from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.db.models import User
from app.modules.auth.deps import get_current_user_id
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.modules.auth.service import authenticate_user, get_user_by_id, register_user
from app.modules.auth.refresh_service import (
    issue_session_tokens,
    set_refresh_cookie,
    set_csrf_cookie,
)
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
async def register(
    body: RegisterIn,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> User:
    user = await register_user(session, body.email, body.password, body.name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return user


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> TokenOut:
    user, token = await authenticate_user(session, body.email, body.password)
    if not user or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token, refresh_token = await issue_session_tokens(user.id, user.email)
    set_refresh_cookie(response, refresh_token)
    csrf_token = secrets.token_urlsafe(32)
    set_csrf_cookie(response, csrf_token)
    return TokenOut(access_token=access_token)


@router.get("/me", response_model=UserOut)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive",
        )
    return user
