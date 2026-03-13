from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.schemas import TokenOut, UserOut
from app.modules.auth.service import get_user_by_id
from app.modules.auth.refresh_service import (
    clear_refresh_cookie,
    create_access_token_for_user,
    issue_session_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
)
from app.core.metrics import incr


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenOut:
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        incr("auth_refresh_failed_total")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    user_id, new_refresh = await rotate_refresh_token(raw_token)
    if not user_id or not new_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user = await get_user_by_id(session, user_id)
    if not user or not user.is_active:
        await revoke_refresh_token(new_refresh)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    access_token = await create_access_token_for_user(user.id, user.email)
    set_refresh_cookie(response, new_refresh)
    incr("auth_refresh_success_total")
    return TokenOut(access_token=access_token)


@router.post("/logout", response_model=UserOut | None)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserOut | None:
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        await revoke_refresh_token(raw_token)
    clear_refresh_cookie(response)
    # Optional: return current user for client-side cleanup
    return None

