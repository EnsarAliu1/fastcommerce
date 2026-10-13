from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False
    )

    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    category: Mapped["Category"] = relationship(
        back_populates="products"
    )

    brand: Mapped["Brand"] = relationship(
        back_populates="products"
    )

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product"
    )

    @property
    def is_in_stock(self) -> bool:
        return any(
            variant.stock_quantity > 0
            for variant in self.variants
        )
