from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"),
        nullable=False,
        index=True
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive"
        ),
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        back_populates="items"
    )

    variant: Mapped["ProductVariant"] = relationship(
        back_populates="order_items"
    )
