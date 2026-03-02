from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import secrets

from shelflife.auth import generate_api_key, get_current_user, hash_api_key, key_prefix
from shelflife.database import get_session
from shelflife.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str


class RegisterResponse(BaseModel):
    user_id: int
    username: str
    api_key: str  # shown once — never stored in plaintext


class MeResponse(BaseModel):
    user_id: int
    username: str
    email: str
    created_at: datetime
    last_sync_at: datetime | None


class RotateKeyResponse(BaseModel):
    api_key: str  # shown once — never stored in plaintext


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    # Check for existing username or email
    existing = (await session.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username or email already registered")

    raw_key = generate_api_key()
    user = User(
        id=int(secrets.token_hex(8), 16),
        username=data.username,
        email=data.email,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=key_prefix(raw_key),
        created_at=datetime.now(UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return RegisterResponse(user_id=user.id, username=user.username, api_key=raw_key)


@router.post("/rotate-key", response_model=RotateKeyResponse)
async def rotate_key(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    raw_key = generate_api_key()
    current_user.api_key_hash = hash_api_key(raw_key)
    current_user.api_key_prefix = key_prefix(raw_key)
    await session.commit()
    return RotateKeyResponse(api_key=raw_key)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        last_sync_at=current_user.last_sync_at,
    )
