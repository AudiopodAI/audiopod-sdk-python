"""
API Wallet Service - Manage API billing and balance
"""

from typing import Dict, Any, Optional, List
from .base import BaseService


class WalletService(BaseService):
    """
    Service for managing API wallet balance and billing.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Get balance
        balance = client.wallet.get_balance()
        print(f"Balance: {balance['balance_usd']}")

        # Estimate cost
        estimate = client.wallet.estimate_cost("stem_extraction", 300)
        print(f"Cost: {estimate['cost_usd']}")

        # Create top-up checkout
        checkout = client.wallet.create_topup_checkout(2500)  # $25.00
        print(f"Pay at: {checkout['url']}")
        ```
    """

    def get_balance(self) -> Dict[str, Any]:
        """
        Get current API wallet balance.

        Returns:
            Dict with balance_cents, balance_usd, total_topup_cents, total_spent_cents
        """
        if self.async_mode:
            return self._async_get_balance()
        return self.client.request("GET", "/api/v1/api-wallet/balance")

    async def _async_get_balance(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/api-wallet/balance")

    def get_pricing(self) -> Dict[str, Any]:
        """
        Get pricing table for all services.

        Returns:
            Dict with services pricing and wallet configuration
        """
        if self.async_mode:
            return self._async_get_pricing()
        return self.client.request("GET", "/api/v1/api-wallet/pricing")

    async def _async_get_pricing(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/api-wallet/pricing")

    def estimate_cost(self, service_type: str, duration_seconds: int) -> Dict[str, Any]:
        """
        Estimate cost for a service operation.

        Args:
            service_type: Type of service (e.g., "stem_extraction", "transcription")
            duration_seconds: Duration of audio in seconds

        Returns:
            Dict with cost_cents, cost_usd, duration_minutes
        """
        if self.async_mode:
            return self._async_estimate_cost(service_type, duration_seconds)
        return self.client.request(
            "POST",
            "/api/v1/api-wallet/estimate",
            json_data={"service_type": service_type, "duration_seconds": duration_seconds},
        )

    async def _async_estimate_cost(self, service_type: str, duration_seconds: int) -> Dict[str, Any]:
        return await self.client.request(
            "POST",
            "/api/v1/api-wallet/estimate",
            json_data={"service_type": service_type, "duration_seconds": duration_seconds},
        )

    def check_balance(self, service_type: str, duration_seconds: int) -> Dict[str, Any]:
        """
        Check if balance is sufficient for an operation.

        Args:
            service_type: Type of service
            duration_seconds: Duration of audio in seconds

        Returns:
            Dict with can_proceed, cost_cents, current_balance_cents

        Raises:
            InsufficientBalanceError: If balance is insufficient (402 response)
        """
        if self.async_mode:
            return self._async_check_balance(service_type, duration_seconds)
        return self.client.request(
            "POST",
            "/api/v1/api-wallet/check-balance",
            json_data={"service_type": service_type, "duration_seconds": duration_seconds},
        )

    async def _async_check_balance(self, service_type: str, duration_seconds: int) -> Dict[str, Any]:
        return await self.client.request(
            "POST",
            "/api/v1/api-wallet/check-balance",
            json_data={"service_type": service_type, "duration_seconds": duration_seconds},
        )

    def create_topup_checkout(self, amount_cents: int) -> Dict[str, Any]:
        """
        Create a Stripe checkout session to top up wallet.

        Args:
            amount_cents: Amount in cents (min 100 = $1.00, max 1000000 = $10,000)

        Returns:
            Dict with session_id, url, amount_cents, amount_usd
        """
        if self.async_mode:
            return self._async_create_topup_checkout(amount_cents)
        return self.client.request(
            "POST",
            "/api/v1/api-wallet/topup/checkout",
            json_data={"amount_cents": amount_cents},
        )

    async def _async_create_topup_checkout(self, amount_cents: int) -> Dict[str, Any]:
        return await self.client.request(
            "POST",
            "/api/v1/api-wallet/topup/checkout",
            json_data={"amount_cents": amount_cents},
        )

    def create_topup_payment_intent(self, amount_cents: int) -> Dict[str, Any]:
        """
        Create a Stripe PaymentIntent for custom payment flows.

        Args:
            amount_cents: Amount in cents

        Returns:
            Dict with client_secret, payment_intent_id, amount_cents
        """
        if self.async_mode:
            return self._async_create_topup_payment_intent(amount_cents)
        return self.client.request(
            "POST",
            "/api/v1/api-wallet/topup/payment-intent",
            json_data={"amount_cents": amount_cents},
        )

    async def _async_create_topup_payment_intent(self, amount_cents: int) -> Dict[str, Any]:
        return await self.client.request(
            "POST",
            "/api/v1/api-wallet/topup/payment-intent",
            json_data={"amount_cents": amount_cents},
        )

    def get_usage_history(
        self, page: int = 1, limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get API usage history.

        Args:
            page: Page number (1-indexed)
            limit: Results per page (max 100)

        Returns:
            Dict with page, limit, logs (list of usage records)
        """
        if self.async_mode:
            return self._async_get_usage_history(page, limit)
        return self.client.request(
            "GET",
            "/api/v1/api-wallet/usage",
            params={"page": page, "limit": limit},
        )

    async def _async_get_usage_history(self, page: int, limit: int) -> Dict[str, Any]:
        return await self.client.request(
            "GET",
            "/api/v1/api-wallet/usage",
            params={"page": page, "limit": limit},
        )

    def get_topup_history(
        self, page: int = 1, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get wallet top-up history.

        Args:
            page: Page number (1-indexed)
            limit: Results per page (max 100)

        Returns:
            Dict with page, limit, topups (list of top-up records)
        """
        if self.async_mode:
            return self._async_get_topup_history(page, limit)
        return self.client.request(
            "GET",
            "/api/v1/api-wallet/topups",
            params={"page": page, "limit": limit},
        )

    async def _async_get_topup_history(self, page: int, limit: int) -> Dict[str, Any]:
        return await self.client.request(
            "GET",
            "/api/v1/api-wallet/topups",
            params={"page": page, "limit": limit},
        )

    def get_service_types(self) -> List[str]:
        """
        Get list of available service types.

        Returns:
            List of service type strings
        """
        if self.async_mode:
            return self._async_get_service_types()
        return self.client.request("GET", "/api/v1/api-wallet/service-types")

    async def _async_get_service_types(self) -> List[str]:
        return await self.client.request("GET", "/api/v1/api-wallet/service-types")

