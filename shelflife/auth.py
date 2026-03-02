import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.config import LOCAL_USERNAME
from shelflife.database import get_session
from shelflife.models.user import User


def generate_api_key() -> str:
    """Generate a new raw API key. Return to the user once — never store."""
    return f"sk-{secrets.token_hex(32)}"  # 256 bits of entropy


def hash_api_key(raw_key: str) -> str:
    """SHA-256 is safe here: keys are 256-bit random values, not passwords."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def key_prefix(raw_key: str) -> str:
    """First 10 chars of the raw key for display (e.g. 'sk-a3f4b2c1')."""
    return raw_key[:10]


async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    # Local bypass: single-user local mode, no auth header required
    if LOCAL_USERNAME and not authorization:
        result = await session.execute(select(User).where(User.username == LOCAL_USERNAME))
        user = result.scalar_one_or_none()
        if user:
            return user

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    raw_key = authorization.removeprefix("Bearer ")
    key_hash = hash_api_key(raw_key)
    result = await session.execute(
        select(User).where(User.api_key_hash == key_hash)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user
