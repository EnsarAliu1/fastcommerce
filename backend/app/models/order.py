from decimal import Decimal

from sqlalchemy import Numeric, Enum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from datetime import datetime


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    status: Mapped[str] = mapped_column(
        Enum("pending", "paid", "cancelled", "refunded", name="order_status"),
        nullable=False,
        default="pending"
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
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

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order"
    )

    reservations: Mapped[list["StockReservation"]] = relationship(
        back_populates="order"
    )
