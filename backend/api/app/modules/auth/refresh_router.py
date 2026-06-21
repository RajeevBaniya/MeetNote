
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.schemas import TokenOut, UserOut
from app.modules.auth.service import get_user_by_id
from app.modules.auth.refresh_service import (
    clear_refresh_cookie,
    clear_csrf_cookie,
    create_access_token_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
    set_csrf_cookie,
)
from app.core.metrics import incr
import secrets


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenOut:
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("x-csrf-token")
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

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
    # Rotate CSRF token on refresh
    new_csrf_token = secrets.token_urlsafe(32)
    set_csrf_cookie(response, new_csrf_token)
    incr("auth_refresh_success_total")
    return TokenOut(access_token=access_token)


@router.post("/logout", response_model=UserOut | None)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserOut | None:
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("x-csrf-token")
    if csrf_cookie and csrf_header and csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        await revoke_refresh_token(raw_token)
    clear_refresh_cookie(response)
    clear_csrf_cookie(response)
    
    # Broadcast websocket disconnect for this user
    try:
        from app.state.client import get_redis
        import json
        redis = await get_redis()
        # We need the user_id to disconnect them. 
        # But we only have the raw_token here. 
        # Actually, let's get the payload to find user_id.
        from app.modules.auth.refresh_service import _get_refresh_payload
        payload = await _get_refresh_payload(raw_token) if raw_token else None
        if payload and payload.get("user_id"):
            uid = payload["user_id"]
            disconnect_msg = {"event": "force_disconnect", "user_id": uid}
            await redis.publish(f"user_events:{uid}", json.dumps(disconnect_msg))
    except Exception:
        pass

    return None

