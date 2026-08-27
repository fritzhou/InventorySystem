from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.schemas.product import ExternalProductRead


class ProductLookupProvider(Protocol):
    name: str

    def lookup(self, barcode: str) -> ExternalProductRead | None: ...


class ProviderUnavailableError(Exception):
    """The provider could not give a trustworthy lookup result."""


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


@dataclass
class OpenFoodFactsProvider:
    base_url: str
    timeout_seconds: float
    name: str = "open_food_facts"

    def lookup(self, barcode: str) -> ExternalProductRead | None:
        try:
            response = httpx.get(
                f"{self.base_url.rstrip('/')}/api/v2/product/{barcode}.json",
                params={"fields": "code,product_name,brands,categories,quantity,image_front_url"},
                headers={"User-Agent": "StockFlow/0.1 product-lookup"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderUnavailableError from exc

        if not isinstance(payload, dict) or "status" not in payload:
            raise ProviderUnavailableError
        if payload.get("status") != 1:
            return None
        product = payload.get("product")
        if not isinstance(product, dict):
            raise ProviderUnavailableError
        return ExternalProductRead(
            barcode=_optional_text(payload.get("code")) or barcode,
            product_name=_optional_text(product.get("product_name")),
            brand=_optional_text(product.get("brands")),
            category_text=_optional_text(product.get("categories")),
            package_size=_optional_text(product.get("quantity")),
            image_url=_optional_text(product.get("image_front_url")),
        )


def get_product_lookup_provider() -> ProductLookupProvider:
    settings = get_settings()
    return OpenFoodFactsProvider(settings.open_food_facts_base_url, settings.product_lookup_timeout_seconds)
