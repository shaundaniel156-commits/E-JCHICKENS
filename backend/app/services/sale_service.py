"""Sales. A sale is the clearest example of one entry moving through the whole system:
it reduces the flock, raises revenue, updates profit and leaves an audit trail.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DuplicateError, NotFoundError, ValidationError
from app.models.enums import (
    ActivityAction,
    NotificationSeverity,
    NotificationType,
    PaymentStatus,
)
from app.models.finance import Customer, Sale
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.finance import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    SaleCreate,
    SaleOut,
    SaleUpdate,
)
from app.services import activity_service, bird_service, notification_service, settings_service
from app.utils.money import ZERO, money
from app.utils.pagination import paginate

MODULE = "sales"


# --------------------------------------------------------------------------- customers

def get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found.")
    return customer


def get_or_create_customer(db: Session, name: str) -> Customer:
    cleaned = name.strip()
    customer = db.execute(
        select(Customer).where(func.lower(Customer.name) == cleaned.lower())
    ).scalars().first()
    if customer is None:
        customer = Customer(name=cleaned)
        db.add(customer)
        db.flush()
    return customer


def customer_out(db: Session, customer: Customer) -> CustomerOut:
    totals = db.execute(
        select(
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.sum(Sale.quantity), 0),
        ).where(
            Sale.customer_id == customer.id,
            Sale.is_deleted.is_(False),
            Sale.payment_status != PaymentStatus.CANCELLED,
        )
    ).one()
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        address=customer.address,
        notes=customer.notes,
        total_purchases=totals[0],
        birds_bought=int(totals[1]),
    )


def list_customers(db: Session, *, page: int = 1, page_size: int = 20, search: Optional[str] = None):
    stmt = select(Customer)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern)))
    stmt = stmt.order_by(Customer.name)
    rows, meta = paginate(db, stmt, page, page_size)
    return [customer_out(db, row) for row in rows], meta


def create_customer(db: Session, payload: CustomerCreate, actor: Optional[User]) -> CustomerOut:
    name = payload.name.strip()
    if db.execute(select(Customer).where(func.lower(Customer.name) == name.lower())).scalars().first():
        raise DuplicateError(f"A customer called “{name}” already exists.")
    customer = Customer(
        name=name,
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        notes=payload.notes,
    )
    db.add(customer)
    db.flush()
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Added customer {name}",
        entity_id=customer.id,
    )
    db.commit()
    db.refresh(customer)
    return customer_out(db, customer)


def update_customer(
    db: Session, customer_id: int, payload: CustomerUpdate, actor: Optional[User]
) -> CustomerOut:
    customer = get_customer(db, customer_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        clash = db.execute(
            select(Customer).where(
                func.lower(Customer.name) == data["name"].strip().lower(), Customer.id != customer.id
            )
        ).scalars().first()
        if clash:
            raise DuplicateError(f"A customer called “{data['name']}” already exists.")
    for field, value in data.items():
        if value is not None:
            setattr(customer, field, value)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated customer {customer.name}",
        entity_id=customer.id,
    )
    db.commit()
    db.refresh(customer)
    return customer_out(db, customer)


def delete_customer(db: Session, customer_id: int, actor: Optional[User]) -> None:
    customer = get_customer(db, customer_id)
    has_sales = db.execute(
        select(Sale.id).where(Sale.customer_id == customer.id, Sale.is_deleted.is_(False)).limit(1)
    ).scalars().first()
    if has_sales:
        raise ConflictError("This customer has sales recorded and cannot be removed.")
    db.delete(customer)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted customer {customer.name}",
        entity_id=customer_id,
    )
    db.commit()


# --------------------------------------------------------------------------- sales

def get_sale(db: Session, sale_id: int) -> Sale:
    sale = db.get(Sale, sale_id)
    if sale is None or sale.is_deleted:
        raise NotFoundError("Sale not found.")
    return sale


def to_out(sale: Sale) -> SaleOut:
    return SaleOut(
        id=sale.id,
        reference=sale.reference,
        sale_date=sale.sale_date,
        batch_id=sale.batch_id,
        batch_code=sale.batch.batch_code if sale.batch else None,
        customer_id=sale.customer_id,
        customer_name=sale.customer.name if sale.customer else None,
        quantity=sale.quantity,
        unit_price=sale.unit_price,
        total_amount=sale.total_amount,
        amount_paid=sale.amount_paid,
        balance_due=max(sale.balance_due, ZERO),
        payment_status=sale.payment_status,
        payment_method=sale.payment_method,
        notes=sale.notes,
    )


def _next_reference(db: Session) -> str:
    year = date.today().year
    prefix = f"SL-{year}-"
    last = db.execute(
        select(Sale.reference).where(Sale.reference.like(f"{prefix}%")).order_by(Sale.id.desc()).limit(1)
    ).scalars().first()
    sequence = int(last.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{sequence:04d}"


def list_sales(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    batch_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    payment_status: Optional[PaymentStatus] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "sale_date",
    order: str = "desc",
):
    stmt = select(Sale).where(Sale.is_deleted.is_(False))
    if batch_id:
        stmt = stmt.where(Sale.batch_id == batch_id)
    if customer_id:
        stmt = stmt.where(Sale.customer_id == customer_id)
    if payment_status:
        stmt = stmt.where(Sale.payment_status == payment_status)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.outerjoin(Customer).where(
            or_(Sale.reference.ilike(pattern), Customer.name.ilike(pattern), Sale.notes.ilike(pattern))
        )
    if start_date:
        stmt = stmt.where(Sale.sale_date >= start_date)
    if end_date:
        stmt = stmt.where(Sale.sale_date <= end_date)

    sortable = {
        "sale_date": Sale.sale_date,
        "quantity": Sale.quantity,
        "total_amount": Sale.total_amount,
        "reference": Sale.reference,
    }
    column = sortable.get(sort, Sale.sale_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Sale.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    return [to_out(row) for row in rows], meta


def _resolve_payment(total: Decimal, amount_paid: Optional[Decimal], status: PaymentStatus):
    """Keep the payment status and the amount paid consistent with each other."""
    if amount_paid is None:
        amount_paid = total if status == PaymentStatus.PAID else ZERO
    amount_paid = money(amount_paid)
    if amount_paid > total:
        raise ValidationError("The amount paid cannot be greater than the sale total.")

    if status == PaymentStatus.CANCELLED:
        return ZERO, PaymentStatus.CANCELLED
    if amount_paid >= total and total > 0:
        return total, PaymentStatus.PAID
    if amount_paid > 0:
        return amount_paid, PaymentStatus.PARTIAL
    return ZERO, PaymentStatus.UNPAID


def create_sale(db: Session, payload: SaleCreate, actor: Optional[User]) -> SaleOut:
    """Validate stock, record the sale and update every dependent figure in one transaction."""
    batch = bird_service.get_batch(db, payload.batch_id)

    available = agg.batch_available(db, batch)
    if payload.quantity > available:
        raise ConflictError(
            f"Batch {batch.batch_code} has only {available} bird(s) available. "
            f"You cannot sell {payload.quantity}."
        )
    if payload.sale_date < batch.acquisition_date:
        raise ConflictError(
            f"Batch {batch.batch_code} was only acquired on {batch.acquisition_date:%d/%m/%Y}."
        )

    customer = None
    if payload.customer_id:
        customer = get_customer(db, payload.customer_id)
    elif payload.customer_name:
        customer = get_or_create_customer(db, payload.customer_name)

    total = money(Decimal(payload.quantity) * payload.unit_price)
    amount_paid, status = _resolve_payment(total, payload.amount_paid, payload.payment_status)

    sale = Sale(
        reference=_next_reference(db),
        sale_date=payload.sale_date,
        batch_id=batch.id,
        customer_id=customer.id if customer else None,
        quantity=payload.quantity,
        unit_price=money(payload.unit_price),
        total_amount=total,
        amount_paid=amount_paid,
        payment_status=status,
        payment_method=payload.payment_method,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(sale)
    db.flush()

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=(
            f"Sold {sale.quantity} bird(s) from {batch.batch_code} for "
            f"{settings_service.money_text(db, sale.total_amount)}"
            + (f" to {customer.name}" if customer else "")
        ),
        entity_id=sale.id,
    )
    notification_service.push(
        db,
        type_=NotificationType.SALE_COMPLETED,
        severity=NotificationSeverity.SUCCESS,
        title="Sale recorded",
        message=(
            f"{sale.reference}: {sale.quantity} bird(s) from {batch.batch_code} "
            f"sold for {settings_service.money_text(db, sale.total_amount)}."
        ),
        module=MODULE,
        entity_id=sale.id,
    )
    db.commit()
    db.refresh(sale)
    return to_out(sale)


def update_sale(db: Session, sale_id: int, payload: SaleUpdate, actor: Optional[User]) -> SaleOut:
    sale = get_sale(db, sale_id)
    batch = bird_service.get_batch(db, sale.batch_id)
    data = payload.model_dump(exclude_unset=True)

    new_quantity = data.get("quantity", sale.quantity)
    new_status = data.get("payment_status", sale.payment_status)
    if new_status != PaymentStatus.CANCELLED:
        available = agg.batch_available(db, batch, exclude_sale_id=sale.id)
        if new_quantity > available:
            raise ConflictError(
                f"Batch {batch.batch_code} can supply at most {available} bird(s) for this sale."
            )

    if "customer_id" in data and data["customer_id"]:
        get_customer(db, data["customer_id"])
        sale.customer_id = data["customer_id"]

    sale.quantity = new_quantity
    if "unit_price" in data and data["unit_price"] is not None:
        sale.unit_price = money(data["unit_price"])
    sale.total_amount = money(Decimal(sale.quantity) * sale.unit_price)
    sale.amount_paid, sale.payment_status = _resolve_payment(
        sale.total_amount, data.get("amount_paid", sale.amount_paid), new_status
    )

    for field in ("sale_date", "payment_method", "notes"):
        if field in data and data[field] is not None:
            setattr(sale, field, data[field])
    sale.updated_by_id = actor.id if actor else None

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated sale {sale.reference}",
        entity_id=sale.id,
    )
    db.commit()
    db.refresh(sale)
    return to_out(sale)


def delete_sale(db: Session, sale_id: int, actor: Optional[User]) -> None:
    """Soft delete: the birds return to the batch and revenue is reversed."""
    sale = get_sale(db, sale_id)
    batch = bird_service.get_batch(db, sale.batch_id)
    sale.is_deleted = True
    sale.deleted_at = datetime.utcnow()
    sale.deleted_by_id = actor.id if actor else None

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=(
            f"Reversed sale {sale.reference} — {sale.quantity} bird(s) returned to "
            f"{batch.batch_code}"
        ),
        entity_id=sale.id,
    )
    db.commit()


def summary(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> dict:
    return {
        "birds_sold": agg.birds_sold(db, start, end),
        "revenue": agg.total_revenue(db, start, end),
        "collected": agg.cash_collected(db, start, end),
    }
