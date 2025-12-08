"""
Script pour créer des données de test dans la base de données.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Ajouter le répertoire backend au path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.pharmacy import Pharmacy
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.sale import Sale, SaleItem, PaymentMethod, SaleStatus
from app.models.cash_register import CashRegister
from app.core.security import get_password_hash
import uuid


def create_categories(db: Session) -> list[ProductCategory]:
    """Créer les catégories de produits."""
    categories_data = [
        {"name": "Antibiotiques", "description": "Médicaments antibactériens"},
        {"name": "Antalgiques", "description": "Médicaments contre la douleur"},
        {"name": "Anti-inflammatoires", "description": "Médicaments anti-inflammatoires"},
        {"name": "Vitamines", "description": "Suppléments vitaminiques"},
        {"name": "Dermatologie", "description": "Produits pour la peau"},
        {"name": "Hygiène", "description": "Produits d'hygiène"},
        {"name": "Pédiatrie", "description": "Médicaments pour enfants"},
        {"name": "Cardiologie", "description": "Médicaments cardiovasculaires"},
    ]
    
    categories = []
    for cat_data in categories_data:
        existing = db.query(ProductCategory).filter(ProductCategory.name == cat_data["name"]).first()
        if not existing:
            category = ProductCategory(**cat_data)
            db.add(category)
            categories.append(category)
        else:
            categories.append(existing)
    
    db.commit()
    print(f"✅ {len(categories)} catégories créées/vérifiées")
    return categories


def create_products(db: Session, pharmacy_id: int, categories: list[ProductCategory]) -> list[Product]:
    """Créer des produits de test."""
    products_data = [
        {"name": "Paracétamol 500mg", "category": "Antalgiques", "purchase_price": 1500, "selling_price": 2000, "quantity": 200, "min_quantity": 50},
        {"name": "Amoxicilline 500mg", "category": "Antibiotiques", "purchase_price": 3000, "selling_price": 4500, "quantity": 100, "min_quantity": 30, "is_prescription_required": True},
        {"name": "Ibuprofène 400mg", "category": "Anti-inflammatoires", "purchase_price": 2000, "selling_price": 3000, "quantity": 150, "min_quantity": 40},
        {"name": "Vitamine C 1000mg", "category": "Vitamines", "purchase_price": 5000, "selling_price": 7500, "quantity": 80, "min_quantity": 20},
        {"name": "Doliprane 1000mg", "category": "Antalgiques", "purchase_price": 2500, "selling_price": 3500, "quantity": 120, "min_quantity": 30},
        {"name": "Augmentin 1g", "category": "Antibiotiques", "purchase_price": 8000, "selling_price": 12000, "quantity": 50, "min_quantity": 15, "is_prescription_required": True},
        {"name": "Voltarène Gel", "category": "Dermatologie", "purchase_price": 4000, "selling_price": 6000, "quantity": 40, "min_quantity": 10},
        {"name": "Savon Antiseptique", "category": "Hygiène", "purchase_price": 1000, "selling_price": 1500, "quantity": 100, "min_quantity": 25},
        {"name": "Sirop Pédiatrique", "category": "Pédiatrie", "purchase_price": 3500, "selling_price": 5000, "quantity": 60, "min_quantity": 15},
        {"name": "Aspirine 100mg", "category": "Cardiologie", "purchase_price": 1200, "selling_price": 1800, "quantity": 90, "min_quantity": 20, "is_prescription_required": True},
        {"name": "Efferalgan 500mg", "category": "Antalgiques", "purchase_price": 2200, "selling_price": 3200, "quantity": 110, "min_quantity": 25},
        {"name": "Ciprofloxacine 500mg", "category": "Antibiotiques", "purchase_price": 6000, "selling_price": 9000, "quantity": 45, "min_quantity": 12, "is_prescription_required": True},
        {"name": "Crème Hydratante", "category": "Dermatologie", "purchase_price": 3000, "selling_price": 4500, "quantity": 55, "min_quantity": 15},
        {"name": "Multivitamines", "category": "Vitamines", "purchase_price": 8000, "selling_price": 12000, "quantity": 70, "min_quantity": 20},
        {"name": "Dentifrice Fluoré", "category": "Hygiène", "purchase_price": 800, "selling_price": 1200, "quantity": 150, "min_quantity": 40},
    ]
    
    category_map = {cat.name: cat.id for cat in categories}
    products = []
    
    for prod_data in products_data:
        existing = db.query(Product).filter(
            Product.name == prod_data["name"],
            Product.pharmacy_id == pharmacy_id
        ).first()
        
        if not existing:
            # Générer une date d'expiration aléatoire (6 mois à 2 ans)
            expiry_days = random.randint(180, 730)
            expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
            
            product = Product(
                pharmacy_id=pharmacy_id,
                name=prod_data["name"],
                category_id=category_map.get(prod_data["category"]),
                purchase_price=prod_data["purchase_price"],
                selling_price=prod_data["selling_price"],
                quantity=prod_data["quantity"],
                min_quantity=prod_data["min_quantity"],
                unit=ProductUnit.BOX,
                expiry_date=expiry_date,
                is_prescription_required=prod_data.get("is_prescription_required", False),
                barcode=f"BRC{random.randint(100000000, 999999999)}",
                sku=f"SKU-{random.randint(1000, 9999)}"
            )
            db.add(product)
            products.append(product)
        else:
            products.append(existing)
    
    db.commit()
    print(f"✅ {len(products)} produits créés/vérifiés")
    return products


def create_customers(db: Session, pharmacy_id: int) -> list[Customer]:
    """Créer des clients de test."""
    customers_data = [
        {"first_name": "Mamadou", "last_name": "Diallo", "phone": "+224620000001", "city": "Conakry"},
        {"first_name": "Fatoumata", "last_name": "Bah", "phone": "+224620000002", "city": "Conakry", "allergies": "Pénicilline"},
        {"first_name": "Ibrahima", "last_name": "Camara", "phone": "+224620000003", "city": "Kindia"},
        {"first_name": "Aissatou", "last_name": "Barry", "phone": "+224620000004", "city": "Conakry"},
        {"first_name": "Oumar", "last_name": "Sylla", "phone": "+224620000005", "city": "Labé"},
        {"first_name": "Mariama", "last_name": "Sow", "phone": "+224620000006", "city": "Conakry", "allergies": "Aspirine"},
        {"first_name": "Abdoulaye", "last_name": "Keita", "phone": "+224620000007", "city": "Kankan"},
        {"first_name": "Kadiatou", "last_name": "Touré", "phone": "+224620000008", "city": "Conakry"},
    ]
    
    customers = []
    for cust_data in customers_data:
        existing = db.query(Customer).filter(
            Customer.phone == cust_data["phone"],
            Customer.pharmacy_id == pharmacy_id
        ).first()
        
        if not existing:
            customer = Customer(
                pharmacy_id=pharmacy_id,
                **cust_data
            )
            db.add(customer)
            customers.append(customer)
        else:
            customers.append(existing)
    
    db.commit()
    print(f"✅ {len(customers)} clients créés/vérifiés")
    return customers


def create_suppliers(db: Session, pharmacy_id: int) -> list[Supplier]:
    """Créer des fournisseurs de test."""
    suppliers_data = [
        {"name": "Pharma Distribution Guinée", "contact_person": "Amadou Balde", "phone": "+224622000001", "city": "Conakry", "payment_terms": "Net 30"},
        {"name": "MedSupply Africa", "contact_person": "Fatou Dieng", "phone": "+224622000002", "city": "Dakar", "country": "Sénégal", "payment_terms": "Net 45"},
        {"name": "HealthCare Import", "contact_person": "Mohamed Cissé", "phone": "+224622000003", "city": "Conakry", "payment_terms": "Cash on delivery"},
    ]
    
    suppliers = []
    for sup_data in suppliers_data:
        existing = db.query(Supplier).filter(
            Supplier.name == sup_data["name"],
            Supplier.pharmacy_id == pharmacy_id
        ).first()
        
        if not existing:
            supplier = Supplier(
                pharmacy_id=pharmacy_id,
                country=sup_data.pop("country", "Guinée"),
                **sup_data
            )
            db.add(supplier)
            suppliers.append(supplier)
        else:
            suppliers.append(existing)
    
    db.commit()
    print(f"✅ {len(suppliers)} fournisseurs créés/vérifiés")
    return suppliers


def create_sample_sales(db: Session, pharmacy_id: int, user_id: int, products: list[Product], customers: list[Customer]) -> None:
    """Créer des ventes de test."""
    # Vérifier si des ventes existent déjà
    existing_sales = db.query(Sale).filter(Sale.pharmacy_id == pharmacy_id).count()
    if existing_sales > 0:
        print(f"⏭️  {existing_sales} ventes déjà existantes, pas de nouvelles ventes créées")
        return
    
    payment_methods = [PaymentMethod.CASH, PaymentMethod.MOBILE_MONEY, PaymentMethod.CARD]
    
    # Créer 10 ventes de test
    for i in range(10):
        # Sélectionner des produits aléatoires (1 à 4 produits par vente)
        selected_products = random.sample(products, random.randint(1, min(4, len(products))))
        
        # Calculer les totaux
        items_data = []
        total = 0
        for prod in selected_products:
            qty = random.randint(1, 3)
            item_total = prod.selling_price * qty
            total += item_total
            items_data.append({
                "product": prod,
                "quantity": qty,
                "unit_price": prod.selling_price,
                "total": item_total
            })
        
        # Créer la vente
        discount = random.choice([0, 0, 0, 500, 1000])  # Parfois une remise
        final_amount = total - discount
        
        sale = Sale(
            pharmacy_id=pharmacy_id,
            customer_id=random.choice([None, random.choice(customers).id]),  # Parfois un client anonyme
            user_id=user_id,
            sale_number=f"SALE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            total_amount=total,
            discount=discount,
            tax=0,
            final_amount=final_amount,
            payment_method=random.choice(payment_methods),
            status=SaleStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        db.add(sale)
        db.flush()
        
        # Créer les items de vente
        for item_data in items_data:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_data["product"].id,
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                discount=0,
                total=item_data["total"]
            )
            db.add(sale_item)
    
    db.commit()
    print("✅ 10 ventes de test créées")


def seed_database():
    """Fonction principale pour peupler la base de données."""
    print("\n🌱 Démarrage du seed de la base de données...\n")
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Vérifier/créer la pharmacie par défaut
        pharmacy = db.query(Pharmacy).first()
        if not pharmacy:
            pharmacy = Pharmacy(
                name="Pharmacie Centrale",
                address="Avenue de la République",
                city="Conakry",
                country="Guinée",
                phone="+224620000000",
                email="contact@pharmacie-centrale.gn",
                license_number="PH-GN-001"
            )
            db.add(pharmacy)
            db.commit()
            db.refresh(pharmacy)
            print("✅ Pharmacie créée")
        else:
            print(f"⏭️  Pharmacie existante: {pharmacy.name}")
        
        # Créer une caisse enregistreuse par défaut
        cash_register = db.query(CashRegister).filter(
            CashRegister.pharmacy_id == pharmacy.id,
            CashRegister.code == "CAISSE-001"
        ).first()
        if not cash_register:
            cash_register = CashRegister(
                pharmacy_id=pharmacy.id,
                name="Caisse Principale",
                code="CAISSE-001",
                location="Comptoir principal",
                is_active=True
            )
            db.add(cash_register)
            db.commit()
            db.refresh(cash_register)
            print("✅ Caisse enregistreuse créée")
        else:
            print(f"⏭️  Caisse existante: {cash_register.name}")
        
        # Vérifier/créer le SUPER ADMIN (sans pharmacie - gestion globale)
        superadmin = db.query(User).filter(User.is_superuser == True).first()
        if not superadmin:
            superadmin = User(
                email="superadmin@pharmacie-manager.com",
                username="superadmin",
                hashed_password=get_password_hash("superadmin123"),
                full_name="Super Administrateur",
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
                pharmacy_id=None  # PAS de pharmacie associée !
            )
            db.add(superadmin)
            db.commit()
            db.refresh(superadmin)
            print("✅ Super Admin créé (superadmin / superadmin123)")
        else:
            print(f"⏭️  Super Admin existant: {superadmin.username}")
        
        # Vérifier/créer l'admin DE LA PHARMACIE
        admin = db.query(User).filter(
            User.username == "admin",
            User.pharmacy_id == pharmacy.id
        ).first()
        if not admin:
            admin = User(
                email="admin@pharmacie-centrale.gn",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin Pharmacie Centrale",
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=False,  # PAS super admin, juste admin de pharmacie
                pharmacy_id=pharmacy.id
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("✅ Admin Pharmacie créé (admin / admin123)")
        else:
            print(f"⏭️  Admin Pharmacie existant: {admin.username}")
        
        # Créer un pharmacien de test
        pharmacist = db.query(User).filter(User.username == "pharmacien").first()
        if not pharmacist:
            pharmacist = User(
                email="pharmacien@pharmacie-manager.com",
                username="pharmacien",
                hashed_password=get_password_hash("pharma123"),
                full_name="Dr. Mamadou Diallo",
                role=UserRole.PHARMACIST,
                is_active=True,
                is_superuser=False,
                pharmacy_id=pharmacy.id
            )
            db.add(pharmacist)
            db.commit()
            db.refresh(pharmacist)
            print("✅ Pharmacien créé (pharmacien / pharma123)")
        else:
            print(f"⏭️  Pharmacien existant: {pharmacist.username}")
        
        # Créer les données
        categories = create_categories(db)
        products = create_products(db, pharmacy.id, categories)
        customers = create_customers(db, pharmacy.id)
        suppliers = create_suppliers(db, pharmacy.id)
        create_sample_sales(db, pharmacy.id, admin.id, products, customers)
        
        print("\n✅ Seed terminé avec succès!\n")
        print("📊 Résumé:")
        print(f"   - Pharmacie: {pharmacy.name}")
        print(f"   - Super Admin (global): superadmin / superadmin123")
        print(f"   - Admin Pharmacie: admin / admin123")
        print(f"   - Pharmacien: pharmacien / pharma123")
        print(f"   - {len(categories)} catégories")
        print(f"   - {len(products)} produits")
        print(f"   - {len(customers)} clients")
        print(f"   - {len(suppliers)} fournisseurs")
        print(f"   - 10 ventes de test")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur lors du seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

