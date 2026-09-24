from sqlalchemy.orm import Session
from app import models
from fastapi import HTTPException


def get_brand_or_404(
        brand_id: int,
        db: Session
):
    brand = db.query(models.Brand).filter(
        models.Brand.id == brand_id
    ).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    return brand
