"""Indihome (Telkom Indonesia) bill checker implementation.

This module provides bill checking for Indihome internet/TV accounts
using the Sepulsa Cart API strategy.

API Details:
- Endpoint: https://api.sepulsa.com/api/v1/carts/add/
- Method: POST
- Product URL: http://api.sepulsa.com/api/v1/oscar/products/34/ (Indihome)
- Response contains nested 'inquiry_details' as stringified JSON
"""

import json
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.bill import (
    BillCheckResponse,
    BillDetail,
    BillPeriod,
    BillStatus,
    ProviderEnum,
)
from app.services.bills.base import BaseBillChecker
from app.services.bills.pln import get_stealth_headers

# ============================================================================
# Sepulsa API Configuration for Indihome
# ============================================================================

SEPULSA_API_URL = "https://api.sepulsa.com/api/v1/carts/add/"
SEPULSA_INDIHOME_PRODUCT_URL = (
    "http://api.sepulsa.com/api/v1/oscar/products/34/"  # Indihome
)
SEPULSA_OPTION_URL = "https://api.sepulsa.com/api/v1/oscar/options/1/"


MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MEI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGU": 8,
    "AGT": 8,
    "SEP": 9,
    "OKT": 10,
    "NOV": 11,
    "DES": 12,
    "JANUARI": 1,
    "FEBRUARI": 2,
    "MARET": 3,
    "APRIL": 4,
    "JUNI": 6,
    "JULI": 7,
    "AGUSTUS": 8,
    "SEPTEMBER": 9,
    "OKTOBER": 10,
    "NOVEMBER": 11,
    "DESEMBER": 12,
}


# ============================================================================
# Response Parser
# ============================================================================


class IndihomeResponseParser:
    """Parser for Sepulsa Indihome API responses."""

    @staticmethod
    def parse_currency(value: str) -> Decimal:
        """Parse Indonesian currency string to Decimal."""
        if not value:
            return Decimal("0")

        cleaned = value.replace("Rp", "").replace(" ", "").replace(".", "")
        if "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")

    @staticmethod
    def parse_period(period_str: str) -> BillPeriod | None:
        """Parse period string to BillPeriod."""
        if not period_str:
            return None

        if "(" in period_str:
            period_str = period_str.split("(")[0].strip()

        parts = period_str.strip().upper().split()

        if len(parts) >= 2:
            month_str = parts[0]
            year_str = parts[-1]

            month = MONTH_MAP.get(month_str)
            try:
                year = int(year_str)
            except ValueError:
                year = date.today().year

            if month:
                return BillPeriod(month=month, year=year)

        return None

    @staticmethod
    def extract_inquiry_details(response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract and parse inquiry_details from Sepulsa response."""
        try:
            data = response_data.get("data", {})
            lines = data.get("lines", []) if isinstance(data, dict) else []

            if not lines:
                return None

            attributes = (
                lines[0].get("attributes", []) if isinstance(lines[0], dict) else []
            )

            for attr in attributes:
                option = attr.get("option", {})
                attr_code = option.get("code") if isinstance(option, dict) else None

                if attr_code == "inquiry_details":
                    details_str = attr.get("value", "")

                    if details_str and isinstance(details_str, str):
                        return json.loads(details_str)
                    elif isinstance(details_str, dict):
                        return details_str

            return None

        except (KeyError, IndexError, json.JSONDecodeError):
            return None

    @classmethod
    def parse_error_response(
        cls,
        response_data: dict[str, Any],
        customer_id: str,
    ) -> BillCheckResponse | None:
        """
        Parse error response from Sepulsa.

        Error format:
        {
            "status": "400",
            "errors": [{"code": "50", "detail": "Bill Already Paid/ Not Available"}]
        }
        """
        errors = response_data.get("errors", [])

        if not errors:
            return None

        for error in errors:
            detail = error.get("detail", "")
            code = error.get("code", "")

            # Code 50: Bill already paid or not available
            if (
                code == "50"
                or "paid" in detail.lower()
                or "not available" in detail.lower()
            ):
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.PAID,
                    message=detail or "Tagihan sudah lunas / tidak tersedia",
                )

            # Code 20: Nomor salah / terblokir / expired
            if code == "20":
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message=detail or "Nomor salah / terblokir / expired",
                )

            # Customer not found (text-based)
            if "not found" in detail.lower() or "tidak ditemukan" in detail.lower():
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message=detail or "Nomor Indihome tidak ditemukan",
                )

        # Generic error - use original detail
        error_detail = (
            errors[0].get("detail", "Unknown error") if errors else "Unknown error"
        )
        return BillCheckResponse(
            provider=ProviderEnum.INDIHOME,
            customer_id=customer_id,
            customer_name="",
            status=BillStatus.ERROR,
            message=error_detail,
        )

    @classmethod
    def parse_response(
        cls,
        response_data: dict[str, Any],
        customer_id: str,
    ) -> BillCheckResponse:
        """
        Parse Sepulsa API response to BillCheckResponse for Indihome.

        Expected inquiry_details structure (similar to PLN/PDAM):
        {
            "Nama Pelanggan": "...",
            "Nomor Internet": "...",
            "Periode": "...",
            "Jumlah Tagihan": "Rp...",
            "Biaya Admin": "Rp..."
        }
        """
        # Check for errors first
        if response_data.get("errors"):
            error_response = cls.parse_error_response(response_data, customer_id)
            if error_response:
                return error_response

        details = cls.extract_inquiry_details(response_data)

        if not details:
            error_msg = response_data.get("message", "")
            if isinstance(error_msg, dict):
                error_msg = str(error_msg)
            error_msg_lower = str(error_msg).lower()

            if "tidak ditemukan" in error_msg_lower or "not found" in error_msg_lower:
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message="Nomor Indihome tidak ditemukan",
                )

            response_str = str(response_data).lower()
            if "lunas" in response_str or "paid" in response_str:
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.PAID,
                    message="Tagihan sudah lunas",
                )

            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Gagal mengurai response: {error_msg_lower[:100] if error_msg_lower else 'no details'}",
            )

        # Extract fields from inquiry_details
        customer_name = details.get("Nama Pelanggan") or details.get("Nama") or ""

        # Parse period
        periode_str = details.get("Periode", "")
        if "(" in periode_str:
            periode_str_clean = periode_str.split("(")[0].strip()
        else:
            periode_str_clean = periode_str

        # Parse amounts
        jumlah_tagihan = cls.parse_currency(
            details.get("Jumlah Tagihan") or details.get("Total Tagihan") or "0"
        )
        admin_fee = cls.parse_currency(details.get("Biaya Admin") or "3000")

        total_bayar = jumlah_tagihan + admin_fee if jumlah_tagihan > 0 else Decimal("0")

        period = cls.parse_period(periode_str_clean)

        bills: list[BillDetail] = []
        if period and jumlah_tagihan > 0:
            bills.append(
                BillDetail(
                    period=period,
                    amount=jumlah_tagihan,
                    admin_fee=admin_fee,
                )
            )

        if total_bayar == 0:
            status = BillStatus.PAID
        else:
            status = BillStatus.UNPAID

        return BillCheckResponse(
            provider=ProviderEnum.INDIHOME,
            customer_id=customer_id,
            customer_name=customer_name,
            status=status,
            bills=bills,
            total_amount=total_bayar,
            checked_at=datetime.now(),
            message=f"Periode: {periode_str}" if periode_str else None,
        )


# ============================================================================
# Indihome Bill Checker Implementation
# ============================================================================


class IndihomeBillChecker(BaseBillChecker):
    """
    Indihome bill checker using Sepulsa API.

    Product ID: 34 (Indihome)
    """

    @property
    def provider_name(self) -> str:
        return "INDIHOME"

    def _validate_customer_id(self, customer_id: str) -> bool:
        """Indihome customer ID is 12-14 digits."""
        return customer_id.isdigit() and 12 <= len(customer_id) <= 14

    async def check_bill(self, customer_id: str) -> BillCheckResponse:
        """
        Check Indihome bill for the given customer ID.

        Uses Sepulsa API by default.
        Only uses mock data if INDIHOME_CHECK_URL is explicitly set to "mock".
        """
        if not self._validate_customer_id(customer_id):
            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message="Nomor Indihome harus 12-14 digit angka",
            )

        if settings.INDIHOME_CHECK_URL.lower() == "mock":
            return await self._generate_mock_response(customer_id)

        try:
            result = await self._fetch_from_sepulsa(customer_id)
            return result
        except httpx.TimeoutException:
            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message="Request timeout - server tidak merespons dalam 30 detik",
            )
        except httpx.RequestError as e:
            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Network error: {str(e)}",
            )
        except Exception as e:
            if settings.DEBUG:
                print(f"[INDIHOME] Unexpected error: {type(e).__name__}: {e}")

            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Gagal menghubungi server: {type(e).__name__}",
            )

    async def _fetch_from_sepulsa(self, customer_id: str) -> BillCheckResponse:
        """Fetch bill data from Sepulsa API for Indihome."""
        payload = {
            "url": SEPULSA_INDIHOME_PRODUCT_URL,
            "quantity": 1,
            "options": [
                {
                    "option": SEPULSA_OPTION_URL,
                    "value": customer_id,
                }
            ],
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.HTTP_TIMEOUT),
            follow_redirects=True,
        ) as client:
            # Use rotating headers for stealth
            headers = get_stealth_headers()

            response = await client.post(
                SEPULSA_API_URL,
                json=payload,
                headers=headers,
            )

            if settings.DEBUG:
                print(f"[INDIHOME] Response status: {response.status_code}")

            # Handle 401 Unauthorized
            if response.status_code == 401:
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.ERROR,
                    message="API memerlukan autentikasi (401)",
                )

            # For 400, parse the error response (could be "already paid")
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if settings.DEBUG:
                        print(f"[INDIHOME] 400 response: {error_data}")
                    return IndihomeResponseParser.parse_error_response(
                        error_data, customer_id
                    ) or BillCheckResponse(
                        provider=ProviderEnum.INDIHOME,
                        customer_id=customer_id,
                        customer_name="",
                        status=BillStatus.NOT_FOUND,
                        message="Nomor Indihome tidak valid",
                    )
                except Exception:
                    return BillCheckResponse(
                        provider=ProviderEnum.INDIHOME,
                        customer_id=customer_id,
                        customer_name="",
                        status=BillStatus.NOT_FOUND,
                        message="Nomor Indihome tidak valid",
                    )

            if response.status_code == 404:
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message="Nomor Indihome tidak ditemukan",
                )

            if response.status_code >= 500:
                return BillCheckResponse(
                    provider=ProviderEnum.INDIHOME,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.ERROR,
                    message=f"Server error: {response.status_code}",
                )

            response.raise_for_status()

            response_data = response.json()

            if settings.DEBUG:
                print(
                    f"[INDIHOME] Response data keys: {response_data.keys() if isinstance(response_data, dict) else 'not dict'}"
                )

            return IndihomeResponseParser.parse_response(response_data, customer_id)

    async def _generate_mock_response(self, customer_id: str) -> BillCheckResponse:
        """Generate realistic mock Indihome bill data for testing."""
        random.seed(hash(customer_id) % (2**32))

        if customer_id.startswith("000"):
            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.NOT_FOUND,
                message="Nomor Indihome tidak ditemukan (MOCK)",
            )

        names = [
            "HENDRO WIBOWO",
            "SANTI PERMATA",
            "DIMAS ADITYA",
            "LAURA VALENTINE",
            "KEVIN ANDERSON",
            "MICHELLE TANAKA",
            "RYAN HIDAYAT",
            "DIANA KUSUMA",
        ]
        customer_name = random.choice(names)

        roll = random.random()
        num_months = random.randint(1, 2) if roll > 0.3 else 0

        if num_months == 0:
            return BillCheckResponse(
                provider=ProviderEnum.INDIHOME,
                customer_id=customer_id,
                customer_name=customer_name,
                status=BillStatus.PAID,
                message="Tagihan sudah lunas (MOCK)",
            )

        bills: list[BillDetail] = []
        today = date.today()

        for i in range(num_months):
            bill_date = today.replace(day=1) - timedelta(days=30 * i + 1)

            # Indihome typically Rp300k-600k
            amount = Decimal(random.randint(300000, 600000))

            bills.append(
                BillDetail(
                    period=BillPeriod(month=bill_date.month, year=bill_date.year),
                    amount=amount,
                    admin_fee=Decimal("3000"),
                )
            )

        total_amount = sum(b.total for b in bills)

        return BillCheckResponse(
            provider=ProviderEnum.INDIHOME,
            customer_id=customer_id,
            customer_name=customer_name,
            status=BillStatus.UNPAID,
            bills=bills,
            total_amount=total_amount,
            checked_at=datetime.now(),
            message="MOCK MODE - Data simulasi",
        )
