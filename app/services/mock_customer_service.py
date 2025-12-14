from pathlib import Path
import json
from typing import Dict, Any

# same path logic as routes_mocks.py
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "customers.json"



def add_customer_to_mocks(customer: Dict[str, Any]) -> None:
    """
    Adds a customer to customers.json if not already present.
    """

    customers = []

    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            customers = json.load(f)

    # prevent duplicates
    for c in customers:
        if c["customer_id"] == customer["customer_id"]:
            return

    customers.append(customer)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2)
