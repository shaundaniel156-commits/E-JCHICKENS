"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import client_ip, get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUser,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _to_current_user(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role_name,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
    )


@router.post("/login", response_model=LoginResponse, summary="Sign in and receive a token pair")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(
        db, payload.identifier, payload.password, ip_address=client_ip(request)
    )
    return LoginResponse(
        tokens=auth_service.issue_tokens(user, payload.remember_me),
        user=_to_current_user(user),
    )


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    _user, tokens = auth_service.refresh_tokens(db, payload.refresh_token)
    return tokens


@router.post("/logout", response_model=Message, summary="Sign out of the current session")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    auth_service.logout(db, user, ip_address=client_ip(request))
    return Message(message="You have been signed out.")


@router.get("/me", response_model=CurrentUser, summary="The signed-in user")
def me(user: User = Depends(get_current_user)):
    return _to_current_user(user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Start the password reset workflow",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    token = auth_service.request_password_reset(db, payload.email)
    # The same answer is returned whether or not the address exists.
    return ForgotPasswordResponse(
        message="If that email address belongs to an account, a reset link has been issued.",
        reset_token=token if (token and settings.DEBUG) else None,
    )


@router.post("/reset-password", response_model=Message, summary="Complete a password reset")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password_with_token(db, payload.token, payload.new_password)
    return Message(message="Your password has been updated. You can now sign in.")


@router.post(
    "/change-password",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Change your own password",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return Message(message="Your password has been changed.")
