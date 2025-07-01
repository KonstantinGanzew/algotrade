from __future__ import annotations

import logging
from typing import AsyncIterator, AsyncContextManager

from tinkoff.invest import (
    AsyncClient,
    CandleInterval,
    CandleInstrument,
    MarketDataRequest,
    OrderDirection,
    OrderType,
    SubscriptionAction,
    SubscribeCandlesRequest,
)
from tinkoff.invest.constants import INVEST_GRPC_API_SANDBOX

from bot.config import settings

logger = logging.getLogger(__name__)


class InvestClient:
    """Lightweight asynchronous wrapper around tinkoff-invest-python AsyncClient."""

    def __init__(self) -> None:
        self._token: str = settings.token
        self._client: AsyncClient | None = None

    # ------------------------------------------------------------------
    # Async context manager helpers
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "InvestClient":
        logger.debug("Opening connection to Tinkoff Invest API (sandbox mode)")
        self._client = AsyncClient(token=self._token, target=INVEST_GRPC_API_SANDBOX)
        self._services = await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        logger.debug("Closing connection to Tinkoff Invest API")
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    async def account_id(self) -> str:
        assert self._client is not None
        resp = await self._services.sandbox.get_sandbox_accounts()
        if not resp.accounts:
            opened = await self._services.sandbox.open_sandbox_account()
            return opened.account_id
        return resp.accounts[0].id

    async def place_market_order(self, figi: str, qty: int, direction: str) -> None:
        """Send a simple market order in the given *direction* (buy/sell)."""
        assert self._client is not None, "Client not initialized. Use 'async with InvestClient()'."
        direction_enum = OrderDirection.BUY if direction.lower() == "buy" else OrderDirection.SELL
        account_id = await self.account_id()
        await self._services.sandbox.post_sandbox_order(
            figi=figi,
            quantity=qty,
            direction=direction_enum,
            order_type=OrderType.MARKET,
            account_id=account_id,
        )
        logger.info("%s %s @MKT", direction.upper(), figi)

    async def stream_candles(
        self,
        figi: str,
        interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_1_MIN,
    ) -> tuple[AsyncContextManager, AsyncIterator]:
        """
        Creates and returns a stream manager and an async iterator for candles.
        This allows for graceful stream termination.
        """
        assert self._client is not None, "Client not initialized. Use 'async with InvestClient()'."

        stream_mgr = self._services.create_market_data_stream()
        stream_mgr.candles.subscribe(
            [CandleInstrument(figi=figi, interval=interval)]
        )

        async def candle_iterator() -> AsyncIterator:
            async for marketdata in stream_mgr:
                if marketdata.candle and marketdata.candle.figi == figi:
                    yield marketdata.candle

        return stream_mgr, candle_iterator() 