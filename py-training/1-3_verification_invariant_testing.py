import pytest
from pydantic import ValidationError
import importlib.util
from pathlib import Path

# Dynamic import for file starting with number/hyphen
def load_contracts():
    path = Path(__file__).parent / "1-3_contracts.py"
    spec = importlib.util.spec_from_file_location("contracts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

contracts = load_contracts()
TransactionTransferRequest = contracts.TransactionTransferRequest
TransactionTransferResponse = contracts.TransactionTransferResponse

def test_valid_payload_passes():

    payload = {
        "source_account": "acc_prod98765432",
        "destination_account": "acc_dest12345678",
        "amount_cents": 150000,
        "currency": "USD",
        "audit_reason": "Quarterly vendor settlement"
    }
    req = TransactionTransferRequest(**payload)
    assert req.amount_cents == 150000

def test_injection_or_malformed_account_fails():
    payload = {
        "source_account": "acc_prod98765432'; DROP TABLE users;--",
        "destination_account": "acc_dest12345678",
        "amount_cents": 500,
        "currency": "USD",
        "audit_reason": "Attempting SQL injection via account field"
    }
    with pytest.raises(ValidationError):
        TransactionTransferRequest(**payload)

def test_transfer_limit_exceeded_fails():
    payload = {
        "source_account": "acc_prod98765432",
        "destination_account": "acc_dest12345678",
        "amount_cents": 10_000_000, # Exceeds 5,000,000 limit
        "currency": "USD",
        "audit_reason": "Over-limit wire transfer"
    }
    with pytest.raises(ValidationError):
        TransactionTransferRequest(**payload)

def test_self_transfer_constraint_fails():
    payload = {
        "source_account": "acc_prod98765432",
        "destination_account": "acc_prod98765432",
        "amount_cents": 5000,
        "currency": "USD",
        "audit_reason": "Transferring funds to identical account"
    }
    with pytest.raises(ValidationError):
        TransactionTransferRequest(**payload)

# pytest -v 1-3_verification_invariant_testing.py