from __future__ import annotations

import logging
from typing import Callable, Dict, Any
from tinkoff.invest.utils import quotation_to_decimal
from bot.strategies.base import Strategy


logger = logging.getLogger(__name__)


class EchoStrategy(Strategy):
    """Простейшая стратегия, которая лишь выводит полученные свечи."""

    name = "EchoStrategy"

    def __init__(self, client, figi: str, on_signal_callback: Callable[[Dict[str, Any]], None] = None):
        super().__init__(client, figi)
        self.candle_count = 0
        self.on_signal_callback = on_signal_callback
        logger.info("EchoStrategy initialized for FIGI: %s", figi)
    
    async def on_start(self) -> None:
        """Called when strategy is started."""
        logger.info("EchoStrategy started for FIGI: %s", self.figi)
        self.candle_count = 0
        
        # Отправляем сигнал о запуске стратегии
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "strategy_started",
                "strategy_name": self.name
            })

    async def on_stop(self) -> None:
        """Called on graceful shutdown."""
        logger.info("EchoStrategy stopped. Processed %d candles.", self.candle_count)
        
        # Отправляем сигнал об остановке стратегии
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "strategy_stopped",
                "candles_processed": self.candle_count,
                "strategy_name": self.name
            })

    async def on_candle(self, candle):
        # Увеличиваем счетчик свечей
        self.candle_count += 1
        
        # `time` already a timezone-aware datetime in SDK 0.2.0+
        ts = candle.time.astimezone()
        close_price = quotation_to_decimal(candle.close)
        
        # Логируем информацию о свече
        logger.info(
            "[%s] FIGI=%s close=%s vol=%d (processed %d candles)",
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            self.figi,
            close_price,
            candle.volume,
            self.candle_count
        )
        
        # Отправляем сигнал о новой свече
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "candle_received",
                "timestamp": ts,
                "price": float(close_price),
                "volume": candle.volume,
                "candle_count": self.candle_count
            }) 