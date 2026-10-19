"""Catalog service - aquarium products, categories, fish attributes, equipment attributes."""

import os
import uuid
from datetime import datetime, timezone

import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.outbox import OutboxRelay
from shared.publisher import StreamPublisher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./catalog.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    product_type = Column(String, nullable=False)  # livestock / equipment / supply
    water_type = Column(String, nullable=True)     # freshwater / saltwater / both
    is_wysiwyg = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    is_livestock = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    species = Column(String, nullable=True)        # common name
    scientific_name = Column(String, nullable=True)
    care_level = Column(String, nullable=True)     # beginner / intermediate / advanced
    max_size_cm = Column(Integer, nullable=True)
    temperament = Column(String, nullable=True)    # peaceful / semi-aggressive / aggressive
    temp_min_c = Column(Integer, nullable=True)
    temp_max_c = Column(Integer, nullable=True)
    ph_min = Column(Numeric(3, 2), nullable=True)
    ph_max = Column(Numeric(3, 2), nullable=True)
    diet = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    compatibility_notes = Column(Text, nullable=True)
    brand = Column(String, nullable=True)          # for equipment
    tank_size_min_litres = Column(Integer, nullable=True)  # for equipment
    power_watts = Column(Integer, nullable=True)   # for equipment
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class StockSnapshot(Base):
    __tablename__ = "stock_snapshot"
    product_id = Column(String, primary_key=True, index=True)
    available_quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True, index=True)
    aggregate_type = Column(String, nullable=False)
    aggregate_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):  # noqa: B008
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Redis + outbox relay
# ---------------------------------------------------------------------------
_redis_client = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    category_id: str | None = None
    product_type: str  # livestock / equipment / supply
    water_type: str | None = None  # freshwater / saltwater / both
    is_wysiwyg: bool = False
    is_livestock: bool = False
    species: str | None = None
    scientific_name: str | None = None
    care_level: str | None = None
    max_size_cm: int | None = None
    temperament: str | None = None
    temp_min_c: int | None = None
    temp_max_c: int | None = None
    ph_min: float | None = None
    ph_max: float | None = None
    diet: str | None = None
    origin: str | None = None
    compatibility_notes: str | None = None
    brand: str | None = None
    tank_size_min_litres: int | None = None
    power_watts: int | None = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: float
    category_id: str | None
    product_type: str
    water_type: str | None
    is_wysiwyg: bool
    is_livestock: bool
    species: str | None
    scientific_name: str | None
    care_level: str | None
    max_size_cm: int | None
    temperament: str | None
    temp_min_c: int | None
    temp_max_c: int | None
    ph_min: float | None
    ph_max: float | None
    diet: str | None
    origin: str | None
    compatibility_notes: str | None
    brand: str | None
    tank_size_min_litres: int | None
    power_watts: int | None
    created_at: datetime


class StockSnapshotResponse(BaseModel):
    product_id: str
    available_quantity: int


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="catalog-service")


@app.post("/catalog/categories", response_model=CategoryResponse, status_code=201)
async def create_category(cat_in: CategoryCreate, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    existing = db.query(Category).filter(Category.name == cat_in.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")
    cat_id = str(uuid.uuid4())
    cat = Category(id=cat_id, name=cat_in.name, description=cat_in.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    try:
        r = await get_redis()
        publisher = StreamPublisher(r)
        relay = OutboxRelay(db, publisher)
        await relay.publish(
            event_type="category.created",
            aggregate_type="category",
            aggregate_id=cat_id,
            idempotency_key=cat_id,
            payload={"category_id": cat_id, "name": cat_in.name},
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return CategoryResponse(id=cat.id, name=cat.name, description=cat.description)


@app.get("/catalog/categories", response_model=list[CategoryResponse])
async def list_categories(db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    cats = db.query(Category).all()
    return [
        CategoryResponse(id=c.id, name=c.name, description=c.description)
        for c in cats
    ]


@app.post("/catalog/products", response_model=ProductResponse, status_code=201)
async def create_product(prod_in: ProductCreate, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    prod_id = str(uuid.uuid4())
    prod = Product(
        id=prod_id,
        name=prod_in.name,
        description=prod_in.description,
        price=prod_in.price,
        category_id=prod_in.category_id,
        product_type=prod_in.product_type,
        water_type=prod_in.water_type,
        is_wysiwyg=1 if prod_in.is_wysiwyg else 0,
        is_livestock=1 if prod_in.is_livestock else 0,
        species=prod_in.species,
        scientific_name=prod_in.scientific_name,
        care_level=prod_in.care_level,
        max_size_cm=prod_in.max_size_cm,
        temperament=prod_in.temperament,
        temp_min_c=prod_in.temp_min_c,
        temp_max_c=prod_in.temp_max_c,
        ph_min=prod_in.ph_min,
        ph_max=prod_in.ph_max,
        diet=prod_in.diet,
        origin=prod_in.origin,
        compatibility_notes=prod_in.compatibility_notes,
        brand=prod_in.brand,
        tank_size_min_litres=prod_in.tank_size_min_litres,
        power_watts=prod_in.power_watts,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    # Initialize stock snapshot at 0
    snapshot = StockSnapshot(product_id=prod_id, available_quantity=0)
    db.add(snapshot)
    db.commit()
    try:
        r = await get_redis()
        publisher = StreamPublisher(r)
        relay = OutboxRelay(db, publisher)
        await relay.publish(
            event_type="product.created",
            aggregate_type="product",
            aggregate_id=prod_id,
            idempotency_key=prod_id,
            payload={"product_id": prod_id, "name": prod_in.name, "price": str(prod_in.price), "product_type": prod_in.product_type},
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return ProductResponse(
        id=prod.id,
        name=prod.name,
        description=prod.description,
        price=float(prod.price),
        category_id=prod.category_id,
        product_type=prod.product_type,
        water_type=prod.water_type,
        is_wysiwyg=bool(prod.is_wysiwyg),
        is_livestock=bool(prod.is_livestock),
        species=prod.species,
        scientific_name=prod.scientific_name,
        care_level=prod.care_level,
        max_size_cm=prod.max_size_cm,
        temperament=prod.temperament,
        temp_min_c=prod.temp_min_c,
        temp_max_c=prod.temp_max_c,
        ph_min=float(prod.ph_min) if prod.ph_min else None,
        ph_max=float(prod.ph_max) if prod.ph_max else None,
        diet=prod.diet,
        origin=prod.origin,
        compatibility_notes=prod.compatibility_notes,
        brand=prod.brand,
        tank_size_min_litres=prod.tank_size_min_litres,
        power_watts=prod.power_watts,
        created_at=prod.created_at,
    )


@app.get("/catalog/products", response_model=list[ProductResponse])
async def list_products(db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    prods = db.query(Product).all()
    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            price=float(p.price),
            category_id=p.category_id,
            product_type=p.product_type,
            water_type=p.water_type,
            is_wysiwyg=bool(p.is_wysiwyg),
            is_livestock=bool(p.is_livestock),
            species=p.species,
            scientific_name=p.scientific_name,
            care_level=p.care_level,
            max_size_cm=p.max_size_cm,
            temperament=p.temperament,
            temp_min_c=p.temp_min_c,
            temp_max_c=p.temp_max_c,
            ph_min=float(p.ph_min) if p.ph_min else None,
            ph_max=float(p.ph_max) if p.ph_max else None,
            diet=p.diet,
            origin=p.origin,
            compatibility_notes=p.compatibility_notes,
            brand=p.brand,
            tank_size_min_litres=p.tank_size_min_litres,
            power_watts=p.power_watts,
            created_at=p.created_at,
        )
        for p in prods
    ]


@app.get("/catalog/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=prod.id,
        name=prod.name,
        description=prod.description,
        price=float(prod.price),
        category_id=prod.category_id,
        product_type=prod.product_type,
        water_type=prod.water_type,
        is_wysiwyg=bool(prod.is_wysiwyg),
        is_livestock=bool(prod.is_livestock),
        species=prod.species,
        scientific_name=prod.scientific_name,
        care_level=prod.care_level,
        max_size_cm=prod.max_size_cm,
        temperament=prod.temperament,
        temp_min_c=prod.temp_min_c,
        temp_max_c=prod.temp_max_c,
        ph_min=float(prod.ph_min) if prod.ph_min else None,
        ph_max=float(prod.ph_max) if prod.ph_max else None,
        diet=prod.diet,
        origin=prod.origin,
        compatibility_notes=prod.compatibility_notes,
        brand=prod.brand,
        tank_size_min_litres=prod.tank_size_min_litres,
        power_watts=prod.power_watts,
        created_at=prod.created_at,
    )


@app.get("/inventory/stock/{product_id}", response_model=StockSnapshotResponse)
async def check_stock(product_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    snapshot = db.query(StockSnapshot).filter(StockSnapshot.product_id == product_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Stock not found")
    return StockSnapshotResponse(product_id=snapshot.product_id, available_quantity=snapshot.available_quantity)