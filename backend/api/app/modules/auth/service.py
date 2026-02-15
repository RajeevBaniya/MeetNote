from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.db.models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    name: str | None = None,
) -> User | None:
    existing = await get_user_by_email(session, email)
    if existing:
        return None
    user = User(
        email=email,
        name=(name.strip() if name and isinstance(name, str) else None) or None,
        hashed_password=hash_password(password),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> tuple[User | None, str | None]:
    user = await get_user_by_email(session, email)
    if not user:
        return None, None
    if not user.is_active:
        return None, None
    if not verify_password(password, user.hashed_password):
        return None, None
    token = create_access_token(user.id, user.email)
    return user, token
