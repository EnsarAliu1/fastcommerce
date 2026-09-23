from app.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from app.database import get_db
from app import models
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from app.services.db import commit_or_conflict
from app.services.categories import get_category_or_404

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.post("", status_code=201, response_model=CategoryResponse)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    new_category = models.Category(**category.model_dump())

    db.add(new_category)

    commit_or_conflict(db, "Category slug already exists")

    db.refresh(new_category)

    return new_category


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db)
):
    return db.query(models.Category).all()


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
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


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    updated_category: CategoryCreate,
    db: Session = Depends(get_db)
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    update_data = updated_category.model_dump()

    for key, value in update_data.items():
        setattr(category, key, value)

    commit_or_conflict(db, "Category slug already exists")

    db.refresh(category)

    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def partial_update_category(
    category_id: int,
    updated_category: CategoryUpdate,
    db: Session = Depends(get_db)
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    update_data = updated_category.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(category, key, value)

    commit_or_conflict(db, "Category slug already exists")

    db.refresh(category)

    return category


@router.delete("/{category_id}", staus_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            delail="Category not found"
        )

    if category.products:
        raise HTTPException(
            status_code=409,
            detail="Category cannot be deleted because it contains products"
        )

    db.delete(category)
    db.commit()
