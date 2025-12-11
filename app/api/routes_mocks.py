# app/api/routes_mocks.py
from fastapi import APIRouter, HTTPException
import json
from pathlib import Path

router = APIRouter(prefix="/mocks", tags=["mocks"])

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "customers.json"

def load_customers():
    if not DATA_PATH.exists():
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return {c["customer_id"]: c for c in json.load(f)}

CUSTOMERS = load_customers()

@router.get("/offer/{customer_id}")
def get_offer(customer_id: str):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return {"pre_approved_limit": customer.get("pre_approved_limit", 0)}

@router.get("/crm/{customer_id}")
def get_crm(customer_id: str):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    # Return KYC fields
    return {
        "name": customer["name"],
        "phone": customer.get("phone"),
        "address": customer.get("address", ""),
        "income_monthly": customer.get("income_monthly"),
        "existing_emi": customer.get("existing_emi"),
    }

@router.get("/credit/{customer_id}")
def get_credit(customer_id: str):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return {"credit_score": customer.get("credit_score", 600)}
