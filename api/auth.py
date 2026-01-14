"""
Аутентификация через Magic Link.

Эндпоинты:
- POST /auth/register — регистрация фабрики + пользователя
- POST /auth/login — запрос magic link
- POST /auth/verify — проверка токена → JWT
- GET /auth/me — текущий пользователь
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models import Factory, MagicToken, User
from api.settings import settings
from shared.email import send_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])

security = HTTPBearer(auto_error=False)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class RegisterRequest(BaseModel):
    """Запрос на регистрацию фабрики."""
    email: EmailStr
    factory_name: str = Field(..., min_length=2, max_length=255)


class LoginRequest(BaseModel):
    """Запрос на вход (отправка magic link)."""
    email: EmailStr


class VerifyRequest(BaseModel):
    """Проверка magic token."""
    token: str = Field(..., min_length=32, max_length=64)


class TokenResponse(BaseModel):
    """Ответ с JWT токеном."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # секунды
    user: "UserInfo"


class UserInfo(BaseModel):
    """Информация о пользователе."""
    id: UUID
    email: str
    is_owner: bool
    factory: "FactoryInfo"


class FactoryInfo(BaseModel):
    """Информация о фабрике."""
    id: UUID
    name: str


class MessageResponse(BaseModel):
    """Простой ответ с сообщением."""
    message: str
    dev_magic_link: str | None = None  # Только в dev режиме (mock email)


# =============================================================================
# JWT Utilities
# =============================================================================

def create_access_token(user_id: UUID, factory_id: UUID) -> tuple[str, int]:
    """
    Создать JWT токен.

    Returns:
        (token, expires_in_seconds)
    """
    expires_delta = timedelta(days=settings.JWT_EXPIRE_DAYS)
    expire = datetime.now(UTC) + expires_delta

    payload = {
        "sub": str(user_id),
        "factory_id": str(factory_id),
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    """Декодировать и проверить JWT токен."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency для получения текущего пользователя из JWT.

    Использование:
        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            ...
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    result = await db.execute(
        select(User)
        .options(selectinload(User.factory))
        .where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """Опциональная аутентификация — возвращает None если не авторизован."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация новой фабрики и первого пользователя (owner).

    Отправляет magic link на email для подтверждения.
    """
    # Проверяем что email не занят
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Создаём фабрику
    factory = Factory(name=request.factory_name)
    db.add(factory)
    await db.flush()  # Получаем сгенерированный factory.id

    # Создаём пользователя (owner)
    user = User(
        email=request.email,
        factory_id=factory.id,
        is_owner=True
    )
    db.add(user)
    await db.flush()  # Получаем сгенерированный user.id

    # Создаём magic token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES)
    magic_token = MagicToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(magic_token)

    await db.commit()

    # Отправляем email
    email_result = await send_magic_link(request.email, token, is_registration=True)

    # В dev режиме возвращаем ссылку для удобства тестирования
    dev_link = None
    if email_result and email_result.startswith("mock:"):
        dev_link = email_result[5:]  # Убираем префикс "mock:"

    return MessageResponse(
        message=f"Письмо отправлено на {request.email}",
        dev_magic_link=dev_link
    )


@router.post("/login", response_model=MessageResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Запрос magic link для входа.

    Всегда возвращает успех (защита от перебора email).
    """
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        # Создаём magic token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES)
        magic_token = MagicToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        db.add(magic_token)
        await db.commit()

        # Отправляем email
        email_result = await send_magic_link(request.email, token)

        # В dev режиме возвращаем ссылку
        if email_result and email_result.startswith("mock:"):
            return MessageResponse(
                message="Если аккаунт существует, письмо отправлено",
                dev_magic_link=email_result[5:]
            )

    # Всегда возвращаем успех (защита от перебора)
    return MessageResponse(message="Если аккаунт существует, письмо отправлено")


@router.post("/verify", response_model=TokenResponse)
async def verify(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка magic token и выдача JWT.

    Token можно использовать только один раз.
    """
    result = await db.execute(
        select(MagicToken)
        .options(selectinload(MagicToken.user).selectinload(User.factory))
        .where(
            MagicToken.token == request.token,
            MagicToken.used == False,
            MagicToken.expires_at > datetime.now(UTC)
        )
    )
    magic_token = result.scalar_one_or_none()

    if not magic_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    user = magic_token.user

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Помечаем токен как использованный
    magic_token.used = True

    # Обновляем last_login
    user.last_login = datetime.now(UTC)

    await db.commit()

    # Создаём JWT
    access_token, expires_in = create_access_token(user.id, user.factory_id)

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserInfo(
            id=user.id,
            email=user.email,
            is_owner=user.is_owner,
            factory=FactoryInfo(
                id=user.factory.id,
                name=user.factory.name
            )
        )
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе."""
    return UserInfo(
        id=user.id,
        email=user.email,
        is_owner=user.is_owner,
        factory=FactoryInfo(
            id=user.factory.id,
            name=user.factory.name
        )
    )
