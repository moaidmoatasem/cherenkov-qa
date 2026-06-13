"""
CHERENKOV Extended Target API — multi-endpoint CRUD demo range.

Normal mode:   uvicorn target.extended_api:app --port 8002
Regression:    REGRESSION_MODE=true uvicorn target.extended_api:app --port 8002

Bugs injected in regression mode:
  BUG-1  POST /users      → 200 instead of 201, body uses 'user_id' not 'id'
  BUG-2  GET  /users/{id} → leaks 'password_hash' field in response
  BUG-3  GET  /users      → returns empty list regardless of stored users
  BUG-4  POST /orders     → 500 on valid payload (server crash)
  BUG-5  GET  /products   → ignores 'category' query param filter
"""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="CHERENKOV Extended Demo Target",
    description="Multi-endpoint CRUD API for thorough QA demo.",
    version="2.0.0",
)

REGRESSION_MODE = os.getenv("REGRESSION_MODE", "false").lower() == "true"

# ── In-memory store ─────────────────────────────────────────────────────────
_users: dict[int, dict] = {}
_orders: dict[int, dict] = {}
_products = [
    {"id": 1, "name": "Widget A", "category": "tools",      "price": 9.99},
    {"id": 2, "name": "Gadget B", "category": "electronics","price": 49.99},
    {"id": 3, "name": "Doohickey","category": "tools",      "price": 14.99},
    {"id": 4, "name": "Thingamajig","category":"misc",      "price": 4.99},
]
_next_user_id = 1
_next_order_id = 1


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    if REGRESSION_MODE:
        return JSONResponse(status_code=200, content={"message": "ok"})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ── Schemas ──────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: str = Field(..., max_length=100, description="User email")
    password: str = Field(..., min_length=8, description="Password (≥8 chars)")
    name: str = Field(..., min_length=1, description="Display name")

class UserResponse(BaseModel):
    id: int
    email: str
    name: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(..., ge=1, le=100)

class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    total_price: float
    status: str


# ── POST /users ──────────────────────────────────────────────────────────────
@app.post("/users", status_code=201)
async def create_user(user: UserCreate):
    global _next_user_id
    uid = _next_user_id
    _next_user_id += 1
    _users[uid] = {"id": uid, "email": user.email, "name": user.name,
                   "password_hash": f"hashed_{user.password}"}
    if REGRESSION_MODE:
        # BUG-1: wrong status code + wrong field name
        return JSONResponse(status_code=200,
                            content={"user_id": uid, "email": user.email, "name": user.name})
    return {"id": uid, "email": user.email, "name": user.name}


# ── GET /users ───────────────────────────────────────────────────────────────
@app.get("/users", status_code=200)
async def list_users():
    if REGRESSION_MODE:
        # BUG-3: always empty
        return []
    return [{"id": u["id"], "email": u["email"], "name": u["name"]}
            for u in _users.values()]


# ── GET /users/{user_id} ────────────────────────────────────────────────────
@app.get("/users/{user_id}", status_code=200)
async def get_user(user_id: int):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    u = _users[user_id]
    if REGRESSION_MODE:
        # BUG-2: leaks password_hash
        return u
    return {"id": u["id"], "email": u["email"], "name": u["name"]}


# ── PATCH /users/{user_id} ──────────────────────────────────────────────────
@app.patch("/users/{user_id}", status_code=200)
async def update_user(user_id: int, patch: UserUpdate):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    if patch.name:
        _users[user_id]["name"] = patch.name
    if patch.email:
        _users[user_id]["email"] = patch.email
    u = _users[user_id]
    return {"id": u["id"], "email": u["email"], "name": u["name"]}


# ── DELETE /users/{user_id} ─────────────────────────────────────────────────
@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    del _users[user_id]
    return None


# ── POST /orders ─────────────────────────────────────────────────────────────
@app.post("/orders", status_code=201)
async def create_order(order: OrderCreate):
    global _next_order_id
    product = next((p for p in _products if p["id"] == order.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if order.user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    if REGRESSION_MODE:
        # BUG-4: crash on valid request
        raise HTTPException(status_code=500, detail="Internal error")
    oid = _next_order_id
    _next_order_id += 1
    total = product["price"] * order.quantity
    _orders[oid] = {"id": oid, "user_id": order.user_id,
                    "product_id": order.product_id,
                    "quantity": order.quantity,
                    "total_price": total, "status": "pending"}
    return _orders[oid]


# ── GET /orders/{order_id} ──────────────────────────────────────────────────
@app.get("/orders/{order_id}", status_code=200)
async def get_order(order_id: int):
    if order_id not in _orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return _orders[order_id]


# ── GET /products ───────────────────────────────────────────────────────────
@app.get("/products", status_code=200)
async def list_products(category: Optional[str] = Query(None)):
    if REGRESSION_MODE:
        # BUG-5: ignores category filter
        return _products
    if category:
        return [p for p in _products if p["category"] == category]
    return _products


# ── GET /health ──────────────────────────────────────────────────────────────
@app.get("/health", status_code=200)
async def health():
    return {"status": "ok", "regression_mode": REGRESSION_MODE,
            "users": len(_users), "orders": len(_orders)}
