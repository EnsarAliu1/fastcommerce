from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    stock_quantity: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    product: Mapped["Product"] = relationship(
        back_populates="variants"
    )

    @property
    def is_in_stock(self) -> bool:
        return self.stock_quantity > 0

    __table_args__ = (
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_product_variants_stock_quantity_non_negative"
        ),
    )

    reservations: Mapped[list["StockReservation"]] = relationship(
        back_populates="variant"
    )

    cart_items: Mapped[list["CartItem"]] = relationship(
        back_populates="variant"
    )
