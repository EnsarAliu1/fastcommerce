from sqlalchemy.orm import Session
from app import models
from fastapi import HTTPException


def get_product_or_404(
        product_id: int,
        db: Session
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product
