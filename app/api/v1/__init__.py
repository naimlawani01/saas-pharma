from fastapi import APIRouter
from app.api.v1 import auth, pharmacies, products, sales, customers, suppliers, sync, reports, users, admin, stock, cash_register, prescriptions, credits, setup, license

api_router = APIRouter()

api_router.include_router(setup.router, prefix="/setup", tags=["setup"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(pharmacies.router, prefix="/pharmacies", tags=["pharmacies"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(sync.router, prefix="/sync", tags=["synchronization"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["super-admin"])
api_router.include_router(stock.router, prefix="/stock", tags=["stock-management"])
api_router.include_router(cash_register.router, prefix="/cash", tags=["cash-register"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["prescriptions"])
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(license.router, prefix="/license", tags=["license"])
