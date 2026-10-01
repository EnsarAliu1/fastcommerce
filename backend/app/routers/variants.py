from app.schemas import ProductVariantResponse, ProductVariantCreate, ProductVariantUpdate, StockAdjustment
from app.db.session import get_db
from app import models
from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.services.products import get_product_or_404
from app.services.db import commit_or_conflict
from sqlalchemy import update

router = APIRouter(
    prefix="/variants",
    tags=["Variants"]
)


@router.post("/", status_code=201, response_model=ProductVariantResponse)
def create_variant(
    variant: ProductVariantCreate,
    db: Session = Depends(get_db)
):
    get_product_or_404(variant.product_id, db)

    new_variant = models.ProductVariant(**variant.model_dump())

    db.add(new_variant)

    commit_or_conflict(db, "Variant SKU already exists")

    db.refresh(new_variant)

    return new_variant


@router.get("/", response_model=list[ProductVariantResponse])
def get_variants(
    db: Session = Depends(get_db)
):
    statement = select(models.ProductVariant)

    variants = db.scalars(statement).all()

    return variants


@router.get("/{variant_id}", response_model=ProductVariantResponse)
def get_variant(
    variant_id: int,
    db: Session = Depends(get_db)
):
    statement = (
        select(models.ProductVariant)
        .options(
            statement=select(models.ProductVariant)
        )
        .where(
            models.ProductVariant.id == variant_id
        )
    )

    variant = db.scalars(statement).first()

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    return variant


@router.put("/{variant_id}", response_model=ProductVariantResponse)
def update_variant(
    variant_id: int,
    updated_variant: ProductVariantCreate,
    db: Session = Depends(get_db)
):
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id
    ).first()

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    get_product_or_404(updated_variant.product_id, db)

    update_data = updated_variant.model_dump()

    for key, value in update_data.items():
        setattr(variant, key, value)

    commit_or_conflict(db, "Variant SKU already exists")

    db.refresh(variant)

    return variant


@router.patch("/{variant_id}", response_model=ProductVariantResponse)
def partial_update_variant(
    variant_id: int,
    updated_variant: ProductVariantUpdate,
    db: Session = Depends(get_db)
):
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id
    ).first()

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    update_data = updated_variant.model_dump(exclude_unset=True)

    if "product_id" in update_data:
        get_product_or_404(
            update_data["product_id"],
            db
        )

    for key, value in update_data.items():
        setattr(variant, key, value)

    commit_or_conflict(db, "Variant SKU already exists")

    db.refresh(variant)

    return variant


@router.delete("/{variant_id}", status_code=204)
def delete_variant(
    variant_id: int,
    db: Session = Depends(get_db)
):
    variant = db.query(models.ProductVariant).filter(
        models.ProductVariant.id == variant_id
    ).first()

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    db.delete(variant)
    db.commit()


@router.post("/{variant_id}/increase-stock", response_model=ProductVariantResponse)
def increase_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db)
):
    statement = (
        update(models.ProductVariant)
        .where(models.ProductVariant.id == variant_id)
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                + adjustment.quantity
            )
        )
        .returning(models.ProductVariant.id)
    )

    result = db.execute(statement)
    updated_variant__id = result.scalar_one_or_none()

    if updated_variant__id is None:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Product variant not found"
        )

    db.commit()

    variant = db.get(
        models.ProductVariant,
        updated_variant__id
    )

    return variant


@router.post("/{variant_id}/decrease-stock", response_model=ProductVariantResponse)
def decrease_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db)
):
    statement = (
        update(models.ProductVariant)
        .where(
            models.ProductVariant.id == variant_id,
            models.ProductVariant.stock_quantity >= adjustment.quantity
        )
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                - adjustment.quantity
            )
        )
        .returning(models.ProductVariant.id)
    )

    result = db.execute(statement)
    updated_variant_id = result.scalar_one_or_none()

    if updated_variant_id is None:
        variant = db.get(
            models.ProductVariant,
            variant_id
        )

        if variant is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Product variant not found"
            )

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )

    db.commit()

    variant = db.get(
        models.ProductVariant,
        updated_variant_id
    )

    db.refresh(variant)

    return variant
