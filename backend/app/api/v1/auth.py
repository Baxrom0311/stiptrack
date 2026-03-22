import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import (
    limit_auth_login,
    limit_auth_logout,
    limit_auth_refresh,
    limit_auth_register,
    limiter,
)
from app.core.redis_client import get_redis
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token_by_type,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import (
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)
from app.services.auth_service import authenticate_user, create_student_user, get_user_by_email
from app.services.user_service import update_own_profile


router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_BLACKLIST_KEY_PREFIX = "auth:refresh:blacklist:"


def _build_refresh_blacklist_key(jti: str) -> str:
    return f"{REFRESH_BLACKLIST_KEY_PREFIX}{jti}"


async def _is_refresh_blacklisted(jti: str) -> bool:
    redis_client = get_redis()
    exists = await redis_client.exists(_build_refresh_blacklist_key(jti))
    return bool(exists)


async def _blacklist_refresh_token(jti: str, exp: int | None) -> None:
    if not jti:
        return

    redis_client = get_redis()
    ttl = 1

    if isinstance(exp, int):
        now_ts = int(datetime.now(timezone.utc).timestamp())
        ttl = max(exp - now_ts, 1)

    await redis_client.setex(_build_refresh_blacklist_key(jti), ttl, "1")


def _token_pair_for_user(user_id: uuid.UUID) -> TokenPair:
    access_token, access_expires_in, _ = create_access_token(subject=str(user_id))
    refresh_token, refresh_expires_in, _ = create_refresh_token(subject=str(user_id))

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=access_expires_in,
        refresh_expires_in=refresh_expires_in,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(limit_auth_register)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> UserOut:
    existing_user = await get_user_by_email(db=db, email=payload.email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await create_student_user(db=db, user_in=payload)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit(limit_auth_login)
async def login(
    payload: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> TokenPair:
    user = await authenticate_user(db=db, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return _token_pair_for_user(user_id=user.id)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(limit_auth_refresh)
async def refresh(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request = None,
) -> TokenPair:
    try:
        token_data = decode_token_by_type(payload.refresh_token, expected_type=TokenType.REFRESH)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    jti = str(token_data.get("jti", ""))
    exp = token_data.get("exp")
    sub = token_data.get("sub")

    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if await _is_refresh_blacklisted(jti=jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    try:
        user_id = uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    await _blacklist_refresh_token(jti=jti, exp=exp)

    return _token_pair_for_user(user_id=user.id)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit(limit_auth_logout)
async def logout(payload: LogoutRequest, request: Request = None) -> MessageResponse:
    try:
        token_data = decode_token_by_type(payload.refresh_token, expected_type=TokenType.REFRESH)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    jti = str(token_data.get("jti", ""))
    exp = token_data.get("exp")

    await _blacklist_refresh_token(jti=jti, exp=exp)

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return UserOut.model_validate(current_user)

    if current_user.role == UserRole.STUDENT and "is_supervisor" in updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student akkaunti o‘zini ilmiy rahbar sifatida belgilay olmaydi",
        )

    updated_user = await update_own_profile(db=db, user=current_user, updates=updates)
    return UserOut.model_validate(updated_user)
