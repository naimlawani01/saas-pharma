from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.product import Product, ProductCategory
from app.schemas.product import (
    Product as ProductSchema,
    ProductCreate,
    ProductUpdate,
    ProductCategory as ProductCategorySchema,
    ProductCategoryCreate
)

router = APIRouter()


# Product Categories
@router.get("/categories", response_model=List[ProductCategorySchema])
def read_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste toutes les catégories de produits."""
    categories = db.query(ProductCategory).offset(skip).limit(limit).all()
    return categories


@router.post("/categories", response_model=ProductCategorySchema, status_code=status.HTTP_201_CREATED)
def create_category(
    *,
    db: Session = Depends(get_db),
    category_in: ProductCategoryCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une nouvelle catégorie de produit."""
    category = ProductCategory(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# Products
@router.get("/", response_model=List[ProductSchema])
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    low_stock: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les produits de la pharmacie."""
    query = db.query(Product).filter(Product.pharmacy_id == current_user.pharmacy_id)
    
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.barcode == search) |
            (Product.sku == search)
        )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if low_stock:
        query = query.filter(Product.quantity <= Product.min_quantity)
    
    products = query.offset(skip).limit(limit).all()
    return products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
def create_product(
    *,
    db: Session = Depends(get_db),
    product_in: ProductCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer un nouveau produit."""
    # Vérifier que la pharmacie correspond
    if product_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create product for another pharmacy"
        )
    
    product = Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Vérifier et créer des alertes de stock si nécessaire
    from app.api.v1.stock import check_and_create_stock_alerts
    check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
    db.commit()
    
    return product


@router.get("/{product_id}", response_model=ProductSchema)
def read_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir un produit par ID."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.put("/{product_id}", response_model=ProductSchema)
def update_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour un produit."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    # Vérifier et créer des alertes de stock si nécessaire
    from app.api.v1.stock import check_and_create_stock_alerts
    check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
    db.commit()
    
    return product


@router.delete("/{product_id}")
def delete_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Response:
    """Supprimer un produit."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
