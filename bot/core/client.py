from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Dict, Any, Optional, Tuple, AsyncGenerator

from tinkoff.invest import AsyncClient
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.schemas import CandleInterval, HistoricCandle, Candle
from tinkoff.invest.utils import now

from bot.config import Settings

logger = logging.getLogger(__name__)


class InvestClient:
    """Клиент для работы с API Тинькофф Инвестиций."""

    def __init__(self, token: str = None, sandbox: bool = True):
        self.token = token or Settings().get_token(sandbox=sandbox)
        self.sandbox = sandbox
        self._instruments_cache: Dict[str, Dict[str, Any]] = {}

    async def __aenter__(self) -> AsyncServices:
        """Создаёт клиент API при входе в контекстный менеджер."""
        logger.debug("Opening connection to Tinkoff Invest API (%s mode)", 
                    "sandbox" if self.sandbox else "production")
        self.client = await AsyncClient(token=self.token, app_name="AlgoTrade").__aenter__()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает клиент API при выходе из контекстного менеджера."""
        logger.debug("Closing connection to Tinkoff Invest API")
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_instrument_info(self, figi: str) -> Dict[str, Any]:
        """Получает информацию об инструменте по его FIGI."""
        # Проверяем кэш
        if figi in self._instruments_cache:
            return self._instruments_cache[figi]
        
        # Если нет в кэше, запрашиваем
        async with AsyncClient(token=self.token, app_name="AlgoTrade") as client:
            instrument = await client.instruments.get_instrument_by(id_type=1, id=figi)
            
            # Формируем информацию об инструменте
            info = {
                "figi": instrument.instrument.figi,
                "ticker": instrument.instrument.ticker,
                "name": instrument.instrument.name,
                "class_code": instrument.instrument.class_code,
                "currency": instrument.instrument.currency,
                "lot": instrument.instrument.lot,
                "min_price_increment": float(instrument.instrument.min_price_increment.units) + 
                                      float(instrument.instrument.min_price_increment.nano) / 1e9
            }
            
            # Сохраняем в кэш
            self._instruments_cache[figi] = info
            return info

    async def get_candles_history(
        self,
        figi: str,
        from_: datetime.datetime,
        to: datetime.datetime,
        interval: CandleInterval,
    ) -> list[HistoricCandle]:
        """Получает исторические свечи для инструмента."""
        async with AsyncClient(token=self.token, app_name="AlgoTrade") as client:
            candles = []
            for candle in await client.get_all_candles(
                figi=figi,
                from_=from_,
                to=to,
                interval=interval,
            ):
                candles.append(candle)
            return candles

    async def stream_candles(
        self, figi: str, interval: CandleInterval
    ) -> Tuple[Any, AsyncGenerator[Candle, None]]:
        """
        Создаёт поток свечей для указанного инструмента.
        Возвращает менеджер потока и асинхронный генератор свечей.
        """
        client = await AsyncClient(token=self.token, app_name="AlgoTrade").__aenter__()
        
        # Создаем менеджер потока рыночных данных
        stream_mgr = client.create_market_data_stream()
        await stream_mgr.candles.subscribe([{"figi": figi, "interval": interval}])
        
        # Создаем асинхронный генератор свечей
        async def candle_generator():
            async for response in stream_mgr:
                if response.candle:
                    yield response.candle
        
        return stream_mgr, candle_generator()

    async def place_market_order(self, figi: str, qty: int, direction: str) -> None:
        """Выставляет рыночный ордер на покупку/продажу."""
        if direction not in ["buy", "sell"]:
            raise ValueError("Direction must be 'buy' or 'sell'")
        
        # В реальном приложении здесь будет код для выставления ордера через API
        logger.info("Placing %s market order for %d lots of %s", direction.upper(), qty, figi)
        
        # Для песочницы можно использовать специальный метод
        if self.sandbox:
            async with AsyncClient(token=self.token, app_name="AlgoTrade") as client:
                if direction == "buy":
                    await client.sandbox.post_sandbox_order(
                        figi=figi,
                        quantity=qty,
                        direction=1,  # 1 - покупка
                        order_type=2,  # 2 - рыночный
                        account_id=await self._get_sandbox_account_id(client),
                    )
                else:
                    await client.sandbox.post_sandbox_order(
                        figi=figi,
                        quantity=qty,
                        direction=2,  # 2 - продажа
                        order_type=2,  # 2 - рыночный
                        account_id=await self._get_sandbox_account_id(client),
                    )

    async def _get_sandbox_account_id(self, client) -> str:
        """Получает ID аккаунта в песочнице."""
        accounts = await client.sandbox.get_sandbox_accounts()
        if not accounts.accounts:
            # Создаем аккаунт, если его нет
            account = await client.sandbox.open_sandbox_account()
            return account.account_id
        return accounts.accounts[0].id 