from app.schemas import BrandCreate, BrandResponse, BrandUpdate
from app.database import get_db
from app import models
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from app.services.db import commit_or_conflict
from app.services.brands import get_brand_or_404


router = APIRouter(
    prefix="/brands",
    tags=["Brands"]
)


@router.post("", status_code=201, response_model=BrandResponse)
def create_brand(
    brand: BrandCreate,
    db: Session = Depends(get_db)
):
    new_brand = models.Brand(**brand.model_dump())

    db.add(new_brand)

    commit_or_conflict(db, "Brand slug already exists")

    db.refresh(new_brand)

    return new_brand


@router.get("", response_model=list[BrandResponse])
def get_brands(
    db: Session = Depends(get_db)
):
    return db.query(models.Brand).all()


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(
    brand_id: int,
    db: Session = Depends(get_db)
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


@router.put("/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: int,
    updated_brand: BrandCreate,
    db: Session = Depends(get_db)
):
    brand = db.query(models.Brand).filter(
        models.Brand.id == brand_id
    ).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    update_data = updated_brand.model_dump()

    for key, value in update_data.items():
        setattr(brand, key, value)

    commit_or_conflict(db, "Brand slug already exists")

    db.refresh(brand)

    return brand


@router.patch("/{brand_id}", response_model=BrandResponse)
def partial_update_brand(
    brand_id: int,
    updated_brand: BrandUpdate,
    db: Session = Depends(get_db)
):
    brand = db.query(models.Brand).filter(
        models.Brand.id == brand_id
    ).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    update_data = updated_brand.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(brand, key, value)

    commit_or_conflict(db, "Brand slug already exists")

    db.refresh(brand)

    return brand


@router.delete("/{brand_id}", status_code=204)
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db)
):
    brand = db.query(models.Brand).filter(
        models.Brand.id == brand_id
    ).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    if brand.products:
        raise HTTPException(
            status_code=409,
            detail="Brand cannot be deleted because it contains products"
        )

    db.delete(brand)
    db.commit()
