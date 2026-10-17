from fastapi import FastAPI

from app.modules.orders.router import router as orders_router
from app.modules.catalog.routers import (
    products,
    categories,
    brands,
    variants,
)
from app.modules.inventory.router import router as inventory_router
from app.modules.inventory.router import stock_router
from app.modules.carts.router import router as carts_router
from app.modules.users.router import router as users_router
from app.modules.orders.expire_router import router as admin_orders_router


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
app.include_router(orders_router)
app.include_router(users_router)
app.include_router(admin_orders_router)


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
