"""Regression tests for lightweight security and request validation."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import app
from app.schemas.bill import BillCheckRequest, ProviderEnum
from app.schemas.utility_account import UtilityAccountCreate


@pytest.fixture
def client() -> TestClient:
    """Create a synchronous test client for middleware checks."""
    return TestClient(app)


def test_protected_routes_fail_closed_when_api_key_is_missing(
    client: TestClient,
) -> None:
    """Protected endpoints must not accept the historical default/null key."""
    original_key = settings.FAMILY_API_KEY
    settings.FAMILY_API_KEY = None
    try:
        response = client.get("/api/v1/utility-accounts/")
    finally:
        settings.FAMILY_API_KEY = original_key

    assert response.status_code == 503
    assert response.json()["error_code"] == "AUTH_NOT_CONFIGURED"


def test_protected_routes_reject_invalid_api_key(client: TestClient) -> None:
    """API key comparison should reject incorrect credentials."""
    original_key = settings.FAMILY_API_KEY
    settings.FAMILY_API_KEY = "expected-secret"
    try:
        response = client.get(
            "/api/v1/utility-accounts/",
            headers={"X-FAMILY-KEY": "wrong-secret"},
        )
    finally:
        settings.FAMILY_API_KEY = original_key

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_INVALID_KEY"


def test_customer_id_is_trimmed_and_digits_only() -> None:
    """External provider identifiers should be canonical numeric strings."""
    request = BillCheckRequest(provider=ProviderEnum.PLN, customer_id=" 123456789012 ")
    account = UtilityAccountCreate(
        provider=ProviderEnum.PLN,
        customer_id=" 123456789012 ",
        alias=" Rumah Utama ",
    )

    assert request.customer_id == "123456789012"
    assert account.customer_id == "123456789012"
    assert account.alias == "Rumah Utama"

    with pytest.raises(ValidationError):
        BillCheckRequest(provider=ProviderEnum.PLN, customer_id="1234<script>")


def test_allowed_origins_accepts_comma_separated_env_value() -> None:
    """Operational config should support common comma-separated env syntax."""
    configured = Settings(ALLOWED_ORIGINS="https://a.example, https://b.example")

    assert configured.ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]
