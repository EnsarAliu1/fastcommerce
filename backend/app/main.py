from fastapi import FastAPI

from app.routers import products, categories, brands, variants, reservations, carts, orders


app = FastAPI(
    title="FastCommerce API"
)

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(brands.router)
app.include_router(variants.router)
app.include_router(reservations.router)
app.include_router(carts.router)
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
