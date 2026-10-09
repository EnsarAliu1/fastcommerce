from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, func, Enum, ForeignKey
from datetime import datetime


class Cart(Base):
    __tablename__ = "cart"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    status: Mapped[str] = mapped_column(
        Enum("active", "checked_out", "abandoned", name="cart_status"),
        nullable=False,
        default="active"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    user: Mapped["User"] = relationship(
        back_populates="carts"
    )
