import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents

app = FastAPI(title="Athletic Store API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductIn(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    image_url: Optional[str] = Field(None, description="Main product image URL")


@app.get("/")
def read_root():
    return {"message": "Athletic Store Backend Ready"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ------------------ Products Endpoints ------------------ #

def _serialize_product(doc: dict) -> dict:
    if not doc:
        return doc
    doc = dict(doc)
    if doc.get("_id") is not None:
        doc["id"] = str(doc.pop("_id"))
    # Ensure numeric price is float
    if "price" in doc:
        try:
            doc["price"] = float(doc["price"])
        except Exception:
            pass
    return doc


@app.get("/api/products", response_model=List[dict])
def list_products(category: Optional[str] = None, limit: int = 50):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filt = {"category": category} if category else {}
    docs = get_documents("product", filt, limit=limit)
    return [_serialize_product(d) for d in docs]


@app.post("/api/products", status_code=201)
def create_product(product: ProductIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    product_id = create_document("product", product)
    return {"id": product_id}


@app.post("/api/seed", summary="Seed sample products if collection is empty")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    existing = db["product"].count_documents({})
    if existing > 0:
        return {"status": "ok", "seeded": False, "message": "Products already exist"}

    samples = [
        {
            "title": "AirSwift Runner",
            "description": "Lightweight running shoes with responsive foam for daily miles.",
            "price": 129.99,
            "category": "Running",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop"
        },
        {
            "title": "CourtPro 2",
            "description": "Classic court silhouette remastered with premium leather.",
            "price": 99.0,
            "category": "Lifestyle",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1543508282-6319a3e2621f?q=80&w=1200&auto=format&fit=crop"
        },
        {
            "title": "TrailForce GTX",
            "description": "All-terrain traction with waterproof protection for the wild.",
            "price": 149.5,
            "category": "Trail",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1542291026-8c1f1a8a261c?q=80&w=1200&auto=format&fit=crop"
        },
        {
            "title": "Flex Studio",
            "description": "Versatile training shoes built for HIIT, strength and more.",
            "price": 119.0,
            "category": "Training",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1542291026-94d8a1b13972?q=80&w=1200&auto=format&fit=crop"
        }
    ]

    for s in samples:
        create_document("product", s)
    return {"status": "ok", "seeded": True, "count": len(samples)}


@app.on_event("startup")
def _ensure_seed():
    try:
        if db is not None and db["product"].count_documents({}) == 0:
            seed_products()
    except Exception:
        # If seeding fails, continue without blocking startup
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
