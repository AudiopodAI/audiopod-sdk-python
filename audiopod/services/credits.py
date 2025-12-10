"""
Credits Service - User credits and usage (subscription credits)
"""

from typing import List, Dict, Any
from .base import BaseService


class CreditService(BaseService):
    """
    Service for managing subscription credits.

    Note: For API wallet (USD-based billing), use client.wallet instead.
    """

    def get_balance(self) -> Dict[str, Any]:
        """Get subscription credit balance."""
        if self.async_mode:
            return self._async_get_balance()
        return self.client.request("GET", "/api/v1/credits")

    async def _async_get_balance(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/credits")

    def get_usage_history(self) -> List[Dict[str, Any]]:
        """Get credit usage history."""
        if self.async_mode:
            return self._async_get_usage_history()
        return self.client.request("GET", "/api/v1/credits/usage")

    async def _async_get_usage_history(self) -> List[Dict[str, Any]]:
        return await self.client.request("GET", "/api/v1/credits/usage")

    def get_multipliers(self) -> Dict[str, float]:
        """Get credit multipliers for services."""
        if self.async_mode:
            return self._async_get_multipliers()
        return self.client.request("GET", "/api/v1/credits/multipliers")

    async def _async_get_multipliers(self) -> Dict[str, float]:
        return await self.client.request("GET", "/api/v1/credits/multipliers")

