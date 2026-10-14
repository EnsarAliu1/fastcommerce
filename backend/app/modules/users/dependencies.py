from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
import jwt
from app.core.config import settings
from app import models

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login"
)


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )

        subject = payload["sub"]

        if not isinstance(subject, str):
            raise credentials_error

        user_id = int(subject)

        if user_id <= 0:
            raise credentials_error

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user = db.get(models.User, user_id)

    if user is None:
        raise credentials_error

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user"
        )

    return user
