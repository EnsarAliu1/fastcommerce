from fastapi import FastAPI

from app.routers import products, categories


app = FastAPI(
    title="FastCommerce API"
)

app.include_router(products.router)
app.include_router(categories.router)


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
