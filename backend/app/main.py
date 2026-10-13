from fastapi import FastAPI

from app.routers import orders
from app.modules.catalog.routers import (
    products,
    categories,
    brands,
    variants,
)
from app.modules.inventory.router import router as inventory_router
from app.modules.inventory.router import stock_router
from app.modules.carts.router import router as carts_router


app = FastAPI(
    title="FastCommerce API"
)

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(brands.router)
app.include_router(variants.router)
app.include_router(inventory_router)
app.include_router(stock_router)
app.include_router(carts_router)
app.include_router(orders.router)


@app.get("/")
def root():
    return {
        "name": "FastCommerce API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
