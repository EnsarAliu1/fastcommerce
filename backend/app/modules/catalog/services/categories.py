from sqlalchemy.orm import Session
from app import models
from fastapi import HTTPException


def get_category_or_404(
        category_id: int,
        db: Session
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return category
