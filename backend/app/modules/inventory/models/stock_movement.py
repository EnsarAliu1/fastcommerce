from app.db.base import Base

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Enum, DateTime, func, CheckConstraint

from datetime import datetime


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"),
        nullable=False,
        index=True
    )

    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=False
    )

    movement_type: Mapped[str] = mapped_column(
        Enum("manual_increase", "manual_decrease",
             name="stock_movement_type"),
        nullable=False,
    )

    quantity_delta: Mapped[int] = mapped_column(
        nullable=False
    )

    stock_before: Mapped[int] = mapped_column(
        nullable=False
    )

    stock_after: Mapped[int] = mapped_column(
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantity_delta != 0",
            name="ck_stock_movements_delta_nonzero",
        ),
        CheckConstraint(
            "stock_before >= 0",
            name="ck_stock_movements_before_nonnegative",
        ),
        CheckConstraint(
            "stock_after >= 0",
            name="ck_stock_movements_after_nonnegative",
        ),
        CheckConstraint(
            "stock_after = stock_before + quantity_delta",
            name="ck_stock_movements_balance",
        ),
    )
