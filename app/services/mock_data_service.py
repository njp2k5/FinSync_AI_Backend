from pathlib import Path
import json
from typing import Dict, Any

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "customers.json"

def load_customers() -> Dict[str, Dict[str, Any]]:
    if not DATA_PATH.exists():
        return {}

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        arr = json.load(f)

    return {c["customer_id"]: c for c in arr}


def get_customer(customer_id: str) -> Dict[str, Any] | None:
    customers = load_customers()
    return customers.get(customer_id)
