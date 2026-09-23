from app.schemas import ProductResponse, ProductCreate, ProductUpdate
from app.database import get_db
from app import models
from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.services.categories import get_category_or_404
from app.services.db import commit_or_conflict


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.post("/", status_code=201, response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    get_category_or_404(product.category_id, db)

    new_product = models.Product(**product.model_dump())

    db.add(new_product)

    commit_or_conflict(db, "SKU already exists")

    db.refresh(new_product)

    return new_product


@router.get("/", response_model=list[ProductResponse])
def get_products(
    db: Session = Depends(get_db)
):
    statement = (
        select(models.Product)
        .options(
            selectinload(models.Product.category)
        )
    )

    products = db.scalars(statement).all()

    return products


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    statement = (
        select(models.Product)
        .options(
            selectinload(models.Product.category)
        )
        .where(
            models.Product.id == product_id
        )
    )

    product = db.scalars(statement).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    updated_product: ProductCreate,
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    get_category_or_404(updated_product.category_id, db)

    update_data = updated_product.model_dump()

    for key, value in update_data.items():
        setattr(product, key, value)

    commit_or_conflict(db, "SKU already exists")

    db.refresh(product)

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def partial_update_product(
    product_id: int,
    updated_product: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    update_data = updated_product.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        get_category_or_404(
            update_data["category_id"],
            db
        )

    for key, value in update_data.items():
        setattr(product, key, value)

    commit_or_conflict(db, "SKU already exists")

    db.refresh(product)

    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()
