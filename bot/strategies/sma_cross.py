from __future__ import annotations

import pandas as pd
import datetime
from decimal import Decimal
from typing import Callable, Dict, Any

from bot.strategies.base import Strategy
from tinkoff.invest.utils import quotation_to_decimal


class SmaCrossStrategy(Strategy):
    """Simple SMA( fast, slow) crossover strategy."""

    name = "SMA-Cross"

    def __init__(self, client, figi: str, fast: int = 20, slow: int = 50, qty: int = 1,
                 on_signal_callback: Callable[[Dict[str, Any]], None] = None):
        super().__init__(client, figi)
        if fast >= slow:
            raise ValueError("fast MA period must be < slow MA period")
        self.fast = fast
        self.slow = slow
        self.qty = qty  # количество лотов для покупки/продажи
        self.on_signal_callback = on_signal_callback  # колбэк для передачи сигналов в UI
        
        # DataFrame with columns: time, close
        self.df = pd.DataFrame(columns=["time", "close"])
        self.position_open: bool = False
        
        # Для отслеживания прибыли
        self.entry_price: float = 0.0
        self.total_profit: float = 0.0
        self.trades_count: int = 0
        self.winning_trades: int = 0

    # ------------------------------------------------------------------
    async def on_start(self) -> None:
        """Called when strategy is started."""
        self.position_open = False
        self.entry_price = 0.0
        self.total_profit = 0.0
        self.trades_count = 0
        self.winning_trades = 0
        
        # Очищаем историю, чтобы не было ложных сигналов от старых данных
        self.df = pd.DataFrame(columns=["time", "close"])
        
        # Отправляем начальное состояние в UI
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "strategy_started",
                "fast_sma": self.fast,
                "slow_sma": self.slow,
                "qty": self.qty
            })

    async def on_stop(self) -> None:
        """Called on graceful shutdown."""
        # Отправляем итоговую статистику в UI
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "strategy_stopped",
                "total_profit": self.total_profit,
                "trades_count": self.trades_count,
                "winning_trades": self.winning_trades,
                "win_rate": (self.winning_trades / self.trades_count * 100) if self.trades_count > 0 else 0
            })

    async def on_candle(self, candle):
        price: Decimal = quotation_to_decimal(candle.close)
        ts: datetime.datetime = candle.time
        current_price = float(price)
        self.df.loc[len(self.df)] = [ts, current_price]

        # Если недостаточно данных для расчета SMA, просто выходим
        if len(self.df) < self.slow:
            return

        fast_ma = self.df.close.rolling(self.fast).mean().iloc[-1]
        slow_ma = self.df.close.rolling(self.slow).mean().iloc[-1]
        
        # Отправляем информацию об индикаторах в UI
        if self.on_signal_callback:
            self.on_signal_callback({
                "type": "indicators_update",
                "timestamp": ts,
                "price": current_price,
                "fast_ma": fast_ma,
                "slow_ma": slow_ma
            })

        # Crossover detection
        if fast_ma > slow_ma and not self.position_open:
            # Buy specified qty of lots
            await self.client.place_market_order(self.figi, qty=self.qty, direction="buy")
            self.position_open = True
            self.entry_price = current_price
            
            # Отправляем сигнал о входе в позицию
            if self.on_signal_callback:
                self.on_signal_callback({
                    "type": "trade_entry",
                    "timestamp": ts,
                    "price": current_price,
                    "direction": "buy",
                    "qty": self.qty
                })
                
        elif fast_ma < slow_ma and self.position_open:
            # Sell position
            await self.client.place_market_order(self.figi, qty=self.qty, direction="sell")
            
            # Рассчитываем прибыль/убыток
            profit = (current_price - self.entry_price) * self.qty
            self.total_profit += profit
            self.trades_count += 1
            if profit > 0:
                self.winning_trades += 1
                
            self.position_open = False
            
            # Отправляем сигнал о выходе из позиции
            if self.on_signal_callback:
                self.on_signal_callback({
                    "type": "trade_exit",
                    "timestamp": ts,
                    "price": current_price,
                    "direction": "sell",
                    "qty": self.qty,
                    "profit": profit,
                    "total_profit": self.total_profit
                }) 