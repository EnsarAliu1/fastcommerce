from sqlalchemy import ForeignKey, String, DateTime, func, CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from datetime import datetime


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"),
        nullable=False,
        index=True
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"),
        nullable=True,
        index=True
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_stock_reservations_quantity_positive"
        ),
    )

    status: Mapped[str] = mapped_column(
        Enum("active", "consumed", "released",
             "expired", name="stock_reservation_status"),
        nullable=False,
        default="active"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    variant: Mapped["ProductVariant"] = relationship(
        back_populates="reservations"
    )

    order: Mapped["Order | None"] = relationship(
        back_populates="reservations"
    )
