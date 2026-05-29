"""PLN (Perusahaan Listrik Negara) bill checker implementation.

This module provides bill checking for PLN Postpaid electricity accounts
using the Sepulsa Cart API strategy.

API Details:
- Endpoint: https://api.sepulsa.com/api/v1/carts/add/
- Method: POST
- Response contains nested 'inquiry_details' as stringified JSON
"""

import json
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from fake_useragent import UserAgent

from app.core.config import settings
from app.schemas.bill import (
    BillCheckResponse,
    BillDetail,
    BillPeriod,
    BillStatus,
    ProviderEnum,
)
from app.services.bills.base import BaseBillChecker

# ============================================================================
# Sepulsa API Configuration
# ============================================================================

SEPULSA_API_URL = "https://api.sepulsa.com/api/v1/carts/add/"
SEPULSA_PRODUCT_URL = "http://api.sepulsa.com/api/v1/oscar/products/14/"
SEPULSA_OPTION_URL = "https://api.sepulsa.com/api/v1/oscar/options/1/"

# Initialize fake UserAgent for stealth
_ua = UserAgent(browsers=["chrome", "edge"])


def get_stealth_headers() -> dict[str, str]:
    """
    Generate headers with rotating User-Agent for stealth scraping.

    Each call returns headers with a different random User-Agent
    to avoid detection and blocking.
    """
    user_agent = _ua.random

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Origin": "https://www.sepulsa.com",
        "Referer": "https://www.sepulsa.com/",
        "Connection": "keep-alive",
        "x-chital-order-source": "web",
        "x-chital-requester": "https://www.sepulsa.com",
        # Browser fingerprinting headers
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if settings.SEPULSA_API_KEY:
        headers["x-chital-api-key"] = settings.SEPULSA_API_KEY
    return headers


# Month name mapping (Indonesian)
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


class SepulsaResponseParser:
    """Parser for Sepulsa API responses."""

    @staticmethod
    def parse_currency(value: str) -> Decimal:
        """
        Parse Indonesian currency string to Decimal.

        Examples:
            "Rp475.904" -> 475904
            "Rp1.234.567" -> 1234567
            "475904" -> 475904
        """
        if not value:
            return Decimal("0")

        # Remove "Rp", spaces, and dots (thousand separators)
        cleaned = value.replace("Rp", "").replace(" ", "").replace(".", "")

        # Handle comma as decimal separator if present
        if "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")

    @staticmethod
    def parse_period(period_str: str) -> BillPeriod | None:
        """
        Parse period string to BillPeriod.

        Examples:
            "FEB 2026" -> BillPeriod(month=2, year=2026)
            "JANUARI 2025" -> BillPeriod(month=1, year=2025)
        """
        if not period_str:
            return None

        # Split by space and extract month/year
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
        """
        Extract and parse inquiry_details from Sepulsa response.

        The inquiry_details is nested as a stringified JSON inside:
        response['data']['lines'][0]['attributes'][?]['value']
        where item['code'] == 'inquiry_details'
        """
        from app.core.config import settings

        try:
            # Navigate to lines[0]['attributes']
            data = response_data.get("data", {})

            # Debug: Print data structure
            if settings.DEBUG:
                print(f"[PLN DEBUG] data type: {type(data)}")
                if isinstance(data, dict):
                    print(f"[PLN DEBUG] data keys: {data.keys()}")
                elif isinstance(data, list) and data:
                    print(f"[PLN DEBUG] data is list with {len(data)} items")
                    print(
                        f"[PLN DEBUG] first item keys: {data[0].keys() if isinstance(data[0], dict) else 'not dict'}"
                    )

            lines = data.get("lines", []) if isinstance(data, dict) else []

            if settings.DEBUG:
                print(f"[PLN DEBUG] lines count: {len(lines)}")

            if not lines:
                # Maybe lines is directly in data?
                if isinstance(data, list):
                    lines = data
                else:
                    return None

            if settings.DEBUG and lines:
                print(
                    f"[PLN DEBUG] lines[0] keys: {lines[0].keys() if isinstance(lines[0], dict) else 'not dict'}"
                )

            attributes = (
                lines[0].get("attributes", []) if isinstance(lines[0], dict) else []
            )

            if settings.DEBUG:
                print(f"[PLN DEBUG] attributes count: {len(attributes)}")
                if attributes:
                    for i, attr in enumerate(attributes[:6]):  # Print first 6
                        print(f"[PLN DEBUG] attr[{i}] FULL: {attr}")

            # Find inquiry_details attribute
            # Structure: {'option': {'name': '...', 'code': 'inquiry_details'}, 'value': '...'}
            for attr in attributes:
                option = attr.get("option", {})
                attr_code = option.get("code") if isinstance(option, dict) else None

                if attr_code == "inquiry_details":
                    details_str = attr.get("value", "")

                    if settings.DEBUG:
                        print(
                            f"[PLN DEBUG] ✅ Found inquiry_details! Type: {type(details_str)}"
                        )
                        if isinstance(details_str, str):
                            print(
                                f"[PLN DEBUG] inquiry_details content: {details_str[:300]}"
                            )

                    if details_str and isinstance(details_str, str):
                        # Parse the stringified JSON
                        parsed = json.loads(details_str)
                        if settings.DEBUG:
                            print(f"[PLN DEBUG] ✅ Parsed inquiry_details: {parsed}")
                        return parsed
                    elif isinstance(details_str, dict):
                        # Already parsed
                        return details_str

            if settings.DEBUG:
                print("[PLN DEBUG] ❌ inquiry_details NOT FOUND in attributes!")

            return None

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            if settings.DEBUG:
                print(f"[PLN DEBUG] Exception: {e}")
            return None

    @classmethod
    def parse_response(
        cls,
        response_data: dict[str, Any],
        customer_id: str,
    ) -> BillCheckResponse:
        """
        Parse Sepulsa API response to BillCheckResponse.

        Expected inquiry_details structure:
        {
            "Nama Pelanggan": "DJALEKA",
            "ID Pelanggan": "123456789012",
            "Tarif/Daya": "R1/900VA",
            "Periode": "FEB 2026",
            "Jumlah Tagihan": "Rp475.904",
            "Admin Bank": "Rp2.500",
            "Total Bayar": "Rp478.404",
            ...
        }
        """
        # Extract inquiry_details
        details = cls.extract_inquiry_details(response_data)

        if not details:
            # Check for error message in response
            error_msg = response_data.get("message", "")
            # Ensure error_msg is a string (could be dict in some responses)
            if isinstance(error_msg, dict):
                error_msg = str(error_msg)
            error_msg_lower = str(error_msg).lower()

            if "tidak ditemukan" in error_msg_lower or "not found" in error_msg_lower:
                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message="ID Pelanggan tidak ditemukan",
                )

            # Check if it means already paid
            response_str = str(response_data).lower()
            if "lunas" in response_str or "paid" in response_str:
                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.PAID,
                    message="Tagihan sudah lunas",
                )

            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Gagal mengurai response: {error_msg_lower[:100] if error_msg_lower else 'no details'}",
            )

        # Extract fields from inquiry_details
        # Actual keys from Sepulsa: "Nama Pelanggan", "Tarif / Daya", "Jumlah Tagihan", "Biaya Admin"
        customer_name = details.get("Nama Pelanggan", details.get("nama_pelanggan", ""))

        # Try multiple possible key variations for tarif/daya
        tarif_daya = (
            details.get("Tarif / Daya")  # With spaces (actual Sepulsa format)
            or details.get("Tarif/Daya")  # Without spaces
            or details.get("tarif_daya", "")
        )

        # Parse period - handle "FEB 2026 (1 Bulan)" format
        periode_str = details.get("Periode", details.get("periode", ""))
        # Remove "(X Bulan)" suffix if present
        if "(" in periode_str:
            periode_str = periode_str.split("(")[0].strip()

        # Parse amounts - try multiple possible keys
        jumlah_tagihan = cls.parse_currency(
            details.get("Jumlah Tagihan") or details.get("jumlah_tagihan") or "0"
        )

        # Admin fee - Sepulsa uses "Biaya Admin", not "Admin Bank"
        admin_fee = cls.parse_currency(
            details.get("Biaya Admin")
            or details.get("Admin Bank")
            or details.get("admin_bank")
            or "2500"
        )

        # Total - calculate if not provided
        total_bayar = cls.parse_currency(
            details.get("Total Bayar") or details.get("total_bayar") or "0"
        )

        # If total_bayar is 0 but jumlah_tagihan exists, calculate it
        if total_bayar == 0 and jumlah_tagihan > 0:
            total_bayar = jumlah_tagihan + admin_fee

        # Get stand meter if available
        stand_meter = details.get("Stand Meter", "")

        # Parse period
        period = cls.parse_period(periode_str)

        # Build bills list
        bills: list[BillDetail] = []
        if period and jumlah_tagihan > 0:
            bills.append(
                BillDetail(
                    period=period,
                    amount=jumlah_tagihan,
                    admin_fee=admin_fee,
                )
            )

        # Extract tariff and power from "R1M/900 VA" format
        tariff_class = ""
        power_rating = ""
        if tarif_daya:
            if "/" in tarif_daya:
                parts = tarif_daya.split("/")
                tariff_class = parts[0].strip()
                power_rating = parts[1].strip() if len(parts) > 1 else ""
            else:
                tariff_class = tarif_daya

        # Determine status
        if total_bayar == 0:
            status = BillStatus.PAID
        else:
            status = BillStatus.UNPAID

        return BillCheckResponse(
            provider=ProviderEnum.PLN,
            customer_id=customer_id,
            customer_name=customer_name,
            status=status,
            bills=bills,
            total_amount=total_bayar,
            meter_number=stand_meter if stand_meter else None,
            tariff_class=tariff_class,
            power_rating=power_rating,
            checked_at=datetime.now(),
            message=f"Periode: {periode_str}" if periode_str else None,
        )


# ============================================================================
# PLN Bill Checker Implementation
# ============================================================================


class PLNBillChecker(BaseBillChecker):
    """
    PLN Postpaid bill checker using Sepulsa API.

    Uses the Sepulsa Cart API to check PLN Postpaid bills.
    Falls back to mock mode if API is unavailable or disabled.
    """

    TARIFF_CLASSES = {
        "R1": "Rumah Tangga 450VA - 900VA",
        "R1T": "Rumah Tangga 900VA - 2200VA",
        "R2": "Rumah Tangga 3500VA - 5500VA",
        "R3": "Rumah Tangga 6600VA+",
        "B1": "Bisnis Kecil",
        "B2": "Bisnis Menengah",
        "B3": "Bisnis Besar",
    }

    POWER_RATINGS = ["450", "900", "1300", "2200", "3500", "5500", "6600"]

    @property
    def provider_name(self) -> str:
        return "PLN"

    def _validate_customer_id(self, customer_id: str) -> bool:
        """PLN customer ID should be 12 digits."""
        return customer_id.isdigit() and len(customer_id) == 12

    async def check_bill(self, customer_id: str) -> BillCheckResponse:
        """
        Check PLN Postpaid bill for the given customer ID.

        Uses Sepulsa API by default.
        Only uses mock data if PLN_CHECK_URL is explicitly set to "mock".
        """
        # Validate customer ID format
        if not self._validate_customer_id(customer_id):
            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message="ID Pelanggan PLN harus 12 digit angka",
            )

        # ONLY use mock if explicitly configured
        if settings.PLN_CHECK_URL.lower() == "mock":
            return await self._generate_mock_response(customer_id)

        # Always try real Sepulsa API
        try:
            result = await self._fetch_from_sepulsa(customer_id)
            return result
        except httpx.TimeoutException:
            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message="Request timeout - server tidak merespons dalam 30 detik",
            )
        except httpx.RequestError as e:
            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Network error: {str(e)}",
            )
        except Exception as e:
            # Log error for debugging
            if settings.DEBUG:
                print(f"[PLN] Unexpected error: {type(e).__name__}: {e}")

            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.ERROR,
                message=f"Gagal menghubungi server: {type(e).__name__}",
            )

    async def _fetch_from_sepulsa(self, customer_id: str) -> BillCheckResponse:
        """
        Fetch bill data from Sepulsa API.

        Strategy:
        1. First visit Sepulsa homepage to get session cookies
        2. Then make POST request with cookies to cart API

        Endpoint: POST https://api.sepulsa.com/api/v1/carts/add/
        """
        # Build request payload
        payload = {
            "url": SEPULSA_PRODUCT_URL,
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
            # Step 1: Visit homepage to get session cookies
            try:
                home_headers = get_stealth_headers()
                await client.get(
                    "https://www.sepulsa.com/tagihan-listrik-pln",
                    headers={
                        "User-Agent": home_headers["User-Agent"],
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "id-ID,id;q=0.9",
                    },
                )
                # Cookies are automatically stored in client
                if settings.DEBUG:
                    print(
                        f"[PLN] Session cookies obtained: {len(client.cookies)} cookies"
                    )
            except Exception as e:
                if settings.DEBUG:
                    print(f"[PLN] Warning: Could not get session cookies: {e}")

            # Step 2: Make the cart API request with rotating headers
            headers = get_stealth_headers()
            if settings.DEBUG:
                print(f"[PLN] Using User-Agent: {headers['User-Agent'][:50]}...")

            response = await client.post(
                SEPULSA_API_URL,
                json=payload,
                headers=headers,
            )

            if settings.DEBUG:
                print(f"[PLN] Response status: {response.status_code}")

            # Handle 401 Unauthorized
            if response.status_code == 401:
                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.ERROR,
                    message="API memerlukan autentikasi (401). Coba lagi nanti atau gunakan mode mock.",
                )

            # Handle 400 Bad Request - parse Sepulsa error codes
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    errors = error_data.get("errors", [])

                    if errors:
                        error_code = errors[0].get("code", "")
                        error_detail = errors[0].get("detail", "")

                        # Code 50: Bill Already Paid / Not Available
                        if error_code == "50":
                            return BillCheckResponse(
                                provider=ProviderEnum.PLN,
                                customer_id=customer_id,
                                customer_name="",
                                status=BillStatus.PAID,
                                message=error_detail
                                or "Tagihan sudah lunas / tidak tersedia",
                            )

                        # Code 20: Nomor salah / terblokir / expired
                        if error_code == "20":
                            return BillCheckResponse(
                                provider=ProviderEnum.PLN,
                                customer_id=customer_id,
                                customer_name="",
                                status=BillStatus.NOT_FOUND,
                                message=error_detail
                                or "Nomor salah / terblokir / expired",
                            )

                        # Other error codes - return the detail from Sepulsa
                        return BillCheckResponse(
                            provider=ProviderEnum.PLN,
                            customer_id=customer_id,
                            customer_name="",
                            status=BillStatus.ERROR,
                            message=error_detail or f"Error code {error_code}",
                        )

                except Exception:
                    pass

                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message="ID Pelanggan tidak valid",
                )

            # Handle 404 Not Found
            if response.status_code == 404:
                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.NOT_FOUND,
                    message="ID Pelanggan tidak ditemukan",
                )

            # Handle 5xx Server Errors
            if response.status_code >= 500:
                return BillCheckResponse(
                    provider=ProviderEnum.PLN,
                    customer_id=customer_id,
                    customer_name="",
                    status=BillStatus.ERROR,
                    message=f"Server error: {response.status_code}",
                )

            # Raise for other unexpected status codes (including remaining 4xx)
            response.raise_for_status()

            # Parse successful response
            response_data = response.json()

            if settings.DEBUG:
                print(
                    f"[PLN] Response data keys: {response_data.keys() if isinstance(response_data, dict) else 'not dict'}"
                )

            return SepulsaResponseParser.parse_response(response_data, customer_id)

    async def _generate_mock_response(self, customer_id: str) -> BillCheckResponse:
        """Generate realistic mock bill data for testing."""
        random.seed(hash(customer_id) % (2**32))

        if customer_id.startswith("000"):
            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name="",
                status=BillStatus.NOT_FOUND,
                message="ID Pelanggan tidak ditemukan (MOCK)",
            )

        names = [
            "BUDI SANTOSO",
            "SITI RAHAYU",
            "AGUS WIJAYA",
            "DEWI LESTARI",
            "RUDI HARTONO",
            "ANI SUSANTI",
            "DJALEKA",
            "MAYA SARI",
        ]
        customer_name = random.choice(names)

        tariff_code = random.choice(list(self.TARIFF_CLASSES.keys()))
        power_rating = random.choice(self.POWER_RATINGS)

        roll = random.random()
        num_months = random.randint(1, 3) if roll > 0.2 else 0

        if num_months == 0:
            return BillCheckResponse(
                provider=ProviderEnum.PLN,
                customer_id=customer_id,
                customer_name=customer_name,
                status=BillStatus.PAID,
                tariff_class=f"{tariff_code}/{power_rating}VA",
                power_rating=f"{power_rating}VA",
                message="Tidak ada tagihan (MOCK)",
            )

        bills: list[BillDetail] = []
        today = date.today()

        for i in range(num_months):
            bill_date = today.replace(day=1) - timedelta(days=30 * i + 1)

            base_amounts = {
                "450": (50000, 150000),
                "900": (100000, 350000),
                "1300": (150000, 500000),
                "2200": (250000, 750000),
            }
            min_amt, max_amt = base_amounts.get(power_rating, (100000, 500000))
            amount = Decimal(random.randint(min_amt, max_amt))

            bills.append(
                BillDetail(
                    period=BillPeriod(month=bill_date.month, year=bill_date.year),
                    amount=amount,
                    admin_fee=Decimal("2500"),
                )
            )

        total_amount = sum(b.total for b in bills)

        return BillCheckResponse(
            provider=ProviderEnum.PLN,
            customer_id=customer_id,
            customer_name=customer_name,
            status=BillStatus.UNPAID,
            bills=bills,
            total_amount=total_amount,
            tariff_class=f"{tariff_code}/{power_rating}VA",
            power_rating=f"{power_rating}VA",
            checked_at=datetime.now(),
            message="MOCK MODE - Data simulasi",
        )
