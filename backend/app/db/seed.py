"""DEVELOPMENT / DEMO SEED DATA.

Everything this script writes is fictional sample data for local development and
demonstrations. Do NOT run it against a real farm's database.

    python -m app.db.seed          # add demo data
    python -m app.db.seed --reset  # wipe the tables first, then add demo data
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.init_db import initialise
from app.db.session import SessionLocal
from app.models.bird import BirdBatch, HealthRecord, MortalityRecord
from app.models.enums import HealthStatus, PaymentMethod, PaymentStatus, RoleName
from app.models.feed import FeedConsumption, FeedPurchase, FeedType
from app.models.finance import Budget, Customer, Expense, ExpenseCategory, Sale
from app.models.system import ActivityLog, Notification
from app.models.user import Role, User
from app.schemas.bird import BirdBatchCreate
from app.schemas.feed import FeedConsumptionCreate, FeedPurchaseCreate
from app.services import (
    bird_service,
    budget_service,
    expense_service,
    feed_service,
    health_service,
    mortality_service,
    sale_service,
)
from app.schemas.bird import HealthCreate, MortalityCreate
from app.schemas.finance import BudgetCreate, ExpenseCreate, SaleCreate

TODAY = date.today()

DEMO_USERS = [
    ("Esther Namukasa", "esther", "esther@ejchickens.com", RoleName.ADMIN, "Esther@12345"),
    ("James Okello", "james", "james@ejchickens.com", RoleName.MANAGER, "James@12345"),
    ("Grace Atim", "grace", "grace@ejchickens.com", RoleName.STAFF, "Grace@12345"),
]

MORTALITY_CAUSES = [
    "Respiratory infection",
    "Heat stress",
    "Coccidiosis",
    "Crushing in the brooder",
    "Unknown",
]


def _ago(days: int) -> date:
    return TODAY - timedelta(days=days)


def reset(db: Session) -> None:
    """Remove all transactional data. Keeps nothing — development use only."""
    for model in (
        ActivityLog,
        Notification,
        Sale,
        Customer,
        Expense,
        ExpenseCategory,
        Budget,
        FeedConsumption,
        FeedPurchase,
        FeedType,
        HealthRecord,
        MortalityRecord,
        BirdBatch,
    ):
        db.execute(delete(model))
    db.execute(delete(User))
    db.execute(delete(Role))
    db.commit()


def _demo_users(db: Session) -> User:
    roles = {role.name: role for role in db.execute(select(Role)).scalars().all()}
    created = []
    for full_name, username, email, role, password in DEMO_USERS:
        existing = db.execute(select(User).where(User.username == username)).scalars().first()
        if existing:
            created.append(existing)
            continue
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            password_hash=hash_password(password),
            role_id=roles[role].id,
            is_active=True,
            notes="Demo account created by the development seed script.",
        )
        db.add(user)
        created.append(user)
    db.commit()
    return created[0]


def seed(db: Session) -> None:
    initialise(db)
    actor = _demo_users(db)
    random.seed(20260901)

    if db.execute(select(BirdBatch)).scalars().first():
        print("Demo data already present — nothing to do. Use --reset to start over.")
        return

    # --- budget -------------------------------------------------------------
    budget_service.create_budget(
        db,
        BudgetCreate(
            name="Season 1 — Broilers",
            amount=Decimal("16000000"),
            start_date=_ago(120),
            end_date=TODAY + timedelta(days=60),
            is_active=True,
            notes="Working capital for the first broiler season.",
        ),
        actor,
    )

    # --- bird batches -------------------------------------------------------
    batches = []
    for code, breed, quantity, cost, acquired, source in [
        ("BROILER-001", "Broiler", 500, "2300", 96, "Ugachick Hatchery"),
        ("BROILER-002", "Broiler", 350, "2450", 62, "Biyinzika Hatchery"),
        ("LAYER-001", "Layer (Isa Brown)", 200, "4200", 40, "Kukuchic Uganda"),
    ]:
        batches.append(
            bird_service.create_batch(
                db,
                BirdBatchCreate(
                    batch_code=code,
                    breed=breed,
                    initial_quantity=quantity,
                    acquisition_date=_ago(acquired),
                    source=source,
                    age_days_at_acquisition=1,
                    cost_per_bird=Decimal(cost),
                ),
                actor,
            )
        )

    feed_types = {
        feed_type.name: feed_type
        for feed_type in db.execute(select(FeedType)).scalars().all()
    }

    # --- feed purchases -----------------------------------------------------
    for name, bags, weight, cost, when, supplier in [
        ("Broiler Starter", "12", "50", "125000", 95, "Ugachick Feeds"),
        ("Broiler Grower", "14", "50", "118000", 78, "Ugachick Feeds"),
        ("Broiler Finisher", "12", "50", "115000", 55, "Nuvita Feeds"),
        ("Broiler Starter", "6", "50", "127000", 60, "Ugachick Feeds"),
        ("Layer Mash", "6", "70", "145000", 38, "Nuvita Feeds"),
    ]:
        feed_service.create_purchase(
            db,
            FeedPurchaseCreate(
                feed_type_id=feed_types[name].id,
                purchase_date=_ago(when),
                brand=supplier.split()[0],
                quantity_bags=Decimal(bags),
                bag_weight_kg=Decimal(weight),
                cost_per_bag=Decimal(cost),
                supplier=supplier,
                lot_number=f"LOT-{when:03d}",
            ),
            actor,
        )

    # --- feed consumption (roughly weekly) ----------------------------------
    for name, weeks, bags_per_week in [
        ("Broiler Starter", range(1, 4), "4"),
        ("Broiler Grower", range(1, 4), "3"),
        ("Broiler Finisher", range(1, 4), "3"),
        # Deliberately leaves the layer mash below the low-stock threshold,
        # so the demo shows a live feed alert.
        ("Layer Mash", range(1, 4), "1"),
    ]:
        for week in weeks:
            feed_service.create_consumption(
                db,
                FeedConsumptionCreate(
                    feed_type_id=feed_types[name].id,
                    batch_id=batches[0].id if "Broiler" in name else batches[2].id,
                    consumption_date=_ago(week * 7),
                    quantity_bags=Decimal(bags_per_week),
                ),
                actor,
            )

    # --- mortality ----------------------------------------------------------
    for batch, events in [
        (batches[0], [(90, 6), (75, 4), (60, 3), (44, 2), (30, 2)]),
        (batches[1], [(55, 5), (40, 3), (22, 2)]),
        (batches[2], [(35, 2), (18, 1)]),
    ]:
        for when, quantity in events:
            mortality_service.create_record(
                db,
                MortalityCreate(
                    batch_id=batch.id,
                    record_date=_ago(when),
                    quantity=quantity,
                    cause=random.choice(MORTALITY_CAUSES),
                    notes="Recorded during the morning inspection.",
                ),
                actor,
            )

    # --- health -------------------------------------------------------------
    health_service.create_record(
        db,
        HealthCreate(
            batch_id=batches[0].id,
            record_date=_ago(70),
            sick_count=18,
            symptoms="Coughing, nasal discharge, ruffled feathers",
            diagnosis="Chronic respiratory disease (CRD)",
            treatment="Doxycycline in drinking water for 5 days",
            medicine="Doxycycline 20%",
            dosage="1 g per 2 litres",
            treatment_cost=Decimal("185000"),
            veterinarian="Dr. Okello Ronald",
            status=HealthStatus.RECOVERED,
        ),
        actor,
    )
    health_service.create_record(
        db,
        HealthCreate(
            batch_id=batches[1].id,
            record_date=_ago(12),
            sick_count=14,
            symptoms="Bloody droppings, huddling",
            diagnosis="Coccidiosis",
            treatment="Amprolium for 5 days",
            medicine="Amprolium 20%",
            dosage="1 g per litre",
            treatment_cost=Decimal("96000"),
            veterinarian="Dr. Okello Ronald",
            status=HealthStatus.UNDER_TREATMENT,
        ),
        actor,
    )
    health_service.create_record(
        db,
        HealthCreate(
            batch_id=batches[2].id,
            record_date=_ago(5),
            sick_count=6,
            symptoms="Lethargy, reduced feed intake",
            diagnosis="Suspected Newcastle exposure",
            treatment="Isolation and supportive vitamins",
            medicine="Vitamin supplement",
            treatment_cost=Decimal("42000"),
            veterinarian="Dr. Nabirye Sarah",
            status=HealthStatus.CRITICAL,
        ),
        actor,
    )

    # --- other expenses -----------------------------------------------------
    categories = {
        category.name: category
        for category in db.execute(select(ExpenseCategory)).scalars().all()
    }
    for name, description, amount, when in [
        ("Vaccines", "Newcastle and Gumboro vaccination programme", "320000", 90),
        ("Drinkers", "20 automatic drinkers", "480000", 97),
        ("Feed Troughs", "25 feeder troughs", "375000", 97),
        ("Lighting", "Brooder bulbs and fittings", "165000", 96),
        ("Electricity", "Power bill — brooding period", "240000", 70),
        ("Electricity", "Power bill — grow-out period", "195000", 35),
        ("Labour", "Farm attendant wages (month 1)", "450000", 80),
        ("Labour", "Farm attendant wages (month 2)", "450000", 50),
        ("Labour", "Farm attendant wages (month 3)", "450000", 20),
        ("Transport", "Delivery of birds to Nakawa market", "180000", 30),
        ("Transport", "Feed collection runs", "220000", 60),
        ("Water", "Water bowser deliveries", "130000", 45),
        ("Repairs", "Repaired the brooder house roof", "280000", 58),
        ("Packaging", "Crates for market deliveries", "140000", 28),
        ("Marketing", "Radio spot on a local station", "150000", 25),
    ]:
        expense_service.create_expense(
            db,
            ExpenseCreate(
                expense_date=_ago(when),
                category_id=categories[name].id,
                description=description,
                amount=Decimal(amount),
                vendor="Local supplier",
                payment_method=PaymentMethod.MOBILE_MONEY,
            ),
            actor,
        )

    # --- customers and sales ------------------------------------------------
    customers = {}
    for name, phone, address in [
        ("Nakawa Market Traders", "+256 700 111 222", "Nakawa, Kampala"),
        ("Hotel Sunrise Entebbe", "+256 772 333 444", "Entebbe Road"),
        ("Mrs. Nabukenya Retail", "+256 752 555 666", "Kireka, Wakiso"),
    ]:
        customer = sale_service.get_or_create_customer(db, name)
        customer.phone = phone
        customer.address = address
        customers[name] = customer
    db.commit()

    for batch, when, quantity, price, customer, status in [
        (batches[0], 34, 120, "26000", "Nakawa Market Traders", PaymentStatus.PAID),
        (batches[0], 29, 150, "26500", "Hotel Sunrise Entebbe", PaymentStatus.PAID),
        (batches[0], 24, 100, "25500", "Mrs. Nabukenya Retail", PaymentStatus.PARTIAL),
        (batches[1], 16, 90, "27000", "Nakawa Market Traders", PaymentStatus.PAID),
        (batches[1], 9, 60, "27500", "Hotel Sunrise Entebbe", PaymentStatus.PAID),
        (batches[1], 4, 45, "28000", "Mrs. Nabukenya Retail", PaymentStatus.UNPAID),
    ]:
        total = Decimal(price) * quantity
        paid = None
        if status == PaymentStatus.PARTIAL:
            paid = (total * Decimal("0.6")).quantize(Decimal("0.01"))
        sale_service.create_sale(
            db,
            SaleCreate(
                sale_date=_ago(when),
                batch_id=batch.id,
                customer_id=customers[customer].id,
                quantity=quantity,
                unit_price=Decimal(price),
                amount_paid=paid,
                payment_status=status,
                payment_method=PaymentMethod.MOBILE_MONEY,
            ),
            actor,
        )

    print_summary(db)


def print_summary(db: Session) -> None:
    from app.services import dashboard_service

    birds = dashboard_service.bird_summary(db)
    feed = dashboard_service.feed_summary(db)
    from app.services import finance_service

    finance = finance_service.financial_summary(db)

    print("\nDemo data created (DEVELOPMENT DATA — not real farm records)")
    print("-" * 62)
    print(f"  Bird batches       : {birds.total_batches}")
    print(f"  Birds on the farm  : {birds.total_birds} (of {birds.initial_birds} acquired)")
    print(f"  Deaths / sold      : {birds.dead_birds} / {birds.sold_birds}")
    print(f"  Feed in stock      : {feed.stock_bags} bags ({feed.stock_kg} kg)")
    print(f"  Total expenses     : UGX {finance.total_expenses:,.0f}")
    print(f"  Total revenue      : UGX {finance.total_revenue:,.0f}")
    label = "profit" if finance.is_profit else "loss"
    print(f"  Net {label:<14}: UGX {abs(finance.net_profit_or_loss):,.0f}")
    print(f"  Budget remaining   : UGX {finance.remaining_budget:,.0f}")
    print("-" * 62)
    print("\nDemo sign-in details:")
    print("  admin@ejchickens.com   / Admin@12345    (Administrator — created by init_db)")
    for full_name, _username, email, role, password in DEMO_USERS:
        print(f"  {email:<22} / {password:<14} ({role.value.title()} — {full_name})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed development/demo data.")
    parser.add_argument(
        "--reset", action="store_true", help="Delete existing data before seeding."
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            confirm = "--reset" in sys.argv
            if confirm:
                reset(db)
                print("Existing data removed.")
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
