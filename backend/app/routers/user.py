from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_active_user
from app.config import get_settings
from app.database import get_db
from app.models.schemas import UserOut, UserUpdate
from app.models.user import User

router = APIRouter()


def _get_fernet() -> Fernet:
    settings = get_settings()
    # Derive a 32-byte url-safe base64 key from secret_key
    import base64
    key = base64.urlsafe_b64encode(settings.secret_key.ljust(32)[:32].encode())
    return Fernet(key)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if body.garmin_email is not None:
        current_user.garmin_email = body.garmin_email
    if body.garmin_password is not None:
        fernet = _get_fernet()
        current_user.garmin_password_encrypted = fernet.encrypt(body.garmin_password.encode()).decode()

    await db.commit()
    await db.refresh(current_user)
    return current_user
