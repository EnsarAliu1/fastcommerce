from fastapi import HTTPException, status
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.modules.users.schemas.user import UserCreate


password_hash = PasswordHash((Argon2Hasher(),))


def register_user(data: UserCreate, db: Session) -> models.User:
    existing_user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = models.User(
        email=data.email,
        hashed_password=password_hash.hash(data.password),
    )

    try:
        db.add(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        sqlstate = getattr(exc.orig, "sqlstate", None)
        diagnostic = getattr(exc.orig, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)

        if sqlstate == "23505" and constraint_name == "ix_users_email":
            raise HTTPException(
                status_code=409,
                detail="Email already registered",
            ) from exc

        raise

    db.refresh(user)
    return user
