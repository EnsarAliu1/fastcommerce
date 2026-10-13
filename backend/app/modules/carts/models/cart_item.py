from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, func, Enum, ForeignKey, CheckConstraint
from datetime import datetime


class CartItem(Base):
    __tablename__ = "cart_item"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    cart_id: Mapped[int] = mapped_column(
        ForeignKey("cart.id"),
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
            name="ck_cart_items_quantity_positive"
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    cart: Mapped["Cart"] = relationship(
        back_populates="items"
    )

    variant: Mapped["ProductVariant"] = relationship(
        back_populates="cart_items"
    )
