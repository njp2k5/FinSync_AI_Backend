# app/api/routes_mocks.py
from fastapi import APIRouter, HTTPException
from app.services.mock_data_service import load_customers, get_customer

router = APIRouter(prefix="/mocks", tags=["mocks"])




@router.get("/customers")
def list_customers():
    customers = load_customers()
    return {
        "customers": [
            {
                "customer_id": c["customer_id"],
                "name": c["name"],
                "city": c.get("city"),
                "pre_approved_limit": c.get("pre_approved_limit"),
                "credit_score": c.get("credit_score"),
                "email": c.get("email"),
            }
            for c in customers.values()
        ]
    }


@router.get("/offer/{customer_id}")
def get_offer(customer_id: str):
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")

    return {"pre_approved_limit": customer.get("pre_approved_limit", 0)}


@router.get("/crm/{customer_id}")
def get_crm(customer_id: str):
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")

    return {
        "name": customer["name"],
        "phone": customer.get("phone"),
        "address": customer.get("address", ""),
        "income_monthly": customer.get("income_monthly"),
        "existing_emi": customer.get("existing_emi"),
        "email": customer.get("email"),
    }


@router.get("/credit/{customer_id}")
def get_credit(customer_id: str):
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")

    return {"credit_score": customer.get("credit_score", 600)}
