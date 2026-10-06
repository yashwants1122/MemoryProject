from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_FILE = Path(__file__).parent / "app" / "loan_memory.db"


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db() -> None:
    """Create the persistent customer-memory table if it does not exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_memory (
                customer_id TEXT PRIMARY KEY,
                memory_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def load_customer_memory(customer_id: str) -> dict[str, Any]:
    """Load long-term memory for a customer."""
    init_memory_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT memory_json FROM customer_memory WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

    if not row:
        return {}

    try:
        return json.loads(row["memory_json"])
    except json.JSONDecodeError:
        return {}


def save_customer_memory(customer_id: str, memory: dict[str, Any]) -> None:
    """Upsert long-term customer memory."""
    init_memory_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO customer_memory(customer_id, memory_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(customer_id)
            DO UPDATE SET
                memory_json = excluded.memory_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (customer_id, json.dumps(memory)),
        )
        conn.commit()


def update_customer_memory(
    customer: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Store only useful business facts/results, rather than the whole state.
    This is the long-term memory boundary.
    """
    old = load_customer_memory(customer["customer_id"])

    history = old.get("assessment_history", [])
    history.append(
        {
            "requested_amount": customer["requested_amount"],
            "tenure_months": customer["tenure_months"],
            "cibil_score": customer["cibil_score"],
            "decision": result.get("final_decision"),
            "emi": result.get("emi"),
            "emi_ratio": result.get("loan_result", {}).get("emi_ratio"),
        }
    )

    # Keep the POC bounded. In production this could be a proper event store.
    history = history[-10:]

    memory = {
        "customer_id": customer["customer_id"],
        "last_known_profile": {
            "monthly_salary": customer["monthly_salary"],
            "cibil_score": customer["cibil_score"],
            "active_loans": customer["active_loans"],
            "outstanding_amount": customer["outstanding_amount"],
        },
        "last_assessment": history[-1],
        "assessment_history": history,
    }

    save_customer_memory(customer["customer_id"], memory)
    return memory
