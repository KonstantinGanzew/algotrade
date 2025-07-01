from __future__ import annotations

import pandas as pd
import pyqtgraph as pg
import datetime
from typing import Dict, Any, List
from PyQt6.QtWidgets import QGridLayout, QWidget, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from tinkoff.invest.schemas import Candle
from tinkoff.invest.utils import quotation_to_decimal


class TradeInfoWidget(QFrame):
    """Виджет для отображения информации о сделках и прибыли."""
    
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("background-color: rgba(18, 18, 18, 0.7); color: #ccc; border-radius: 5px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title_label = QLabel("Статистика торговли")
        title_label.setStyleSheet("font-weight: bold; color: #fff;")
        layout.addWidget(title_label)
        
        # Информация о сделках
        self.profit_label = QLabel("Прибыль: 0.00")
        self.trades_label = QLabel("Сделок: 0")
        self.win_rate_label = QLabel("Винрейт: 0%")
        self.win_sum_label = QLabel("Сумма выигрышей: 0.00")
        self.last_trade_label = QLabel("Последняя сделка: -")
        
        layout.addWidget(self.profit_label)
        layout.addWidget(self.trades_label)
        layout.addWidget(self.win_rate_label)
        layout.addWidget(self.win_sum_label)
        layout.addWidget(self.last_trade_label)
        
        self.setMaximumWidth(200)
        self.setVisible(False)
    
    def update_stats(self, total_profit: float, trades_count: int, 
                     winning_trades: int, last_trade_profit: float = None,
                     win_sum: float = 0.0):
        """Обновляет статистику торговли."""
        self.profit_label.setText(f"Прибыль: {total_profit:.2f}")
        self.profit_label.setStyleSheet(f"color: {'#26a69a' if total_profit >= 0 else '#ef5350'};")
        
        self.trades_label.setText(f"Сделок: {trades_count}")
        
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
        self.win_rate_label.setText(f"Винрейт: {win_rate:.1f}%")
        
        self.win_sum_label.setText(f"Сумма выигрышей: {win_sum:.2f}")
        self.win_sum_label.setStyleSheet("color: #26a69a;")
        
        if last_trade_profit is not None:
            self.last_trade_label.setText(f"Последняя сделка: {last_trade_profit:.2f}")
            self.last_trade_label.setStyleSheet(
                f"color: {'#26a69a' if last_trade_profit >= 0 else '#ef5350'};"
            )
        
        self.setVisible(True)


class ModernChart(QWidget):
    """Виджет графика на основе pyqtgraph с современным видом."""

    def __init__(self, figi: str, max_bars: int = 200, sma_period: int = 20):
        super().__init__()
        self.figi = figi
        self.max_bars = max_bars
        self.sma_period = sma_period
        self.df = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
        
        # Настройки отображения
        self._volume_visible = True
        self._grid_visible = True
        self._sma_visible = False
        self._signals_visible = True
        
        # --- Данные для отображения сигналов ---
        self._trade_entries: List[Dict[str, Any]] = []
        self._trade_exits: List[Dict[str, Any]] = []
        self._total_profit = 0.0
        self._trades_count = 0
        self._winning_trades = 0
        self._win_sum = 0.0  # Сумма выигрышей
        self._last_trade_profit = None
        
        self._init_ui()
        
    def _init_ui(self):
        # --- Настройка UI ---
        pg.setConfigOptions(antialias=True, background="#121212", foreground="#ccc")
        layout = QGridLayout(self)
        
        # Добавляем виджет с информацией о сделках
        self.trade_info = TradeInfoWidget()
        layout.addWidget(self.trade_info, 0, 1, 2, 1, Qt.AlignmentFlag.AlignTop)
        
        self.win = pg.GraphicsLayoutWidget()
        layout.addWidget(self.win, 0, 0, 2, 1)
        layout.setColumnStretch(0, 1)  # График занимает всё доступное пространство

        # 1. График цены
        self._price_plot = self.win.addPlot(row=0, col=0)
        self._price_plot.showGrid(x=True, y=True, alpha=0.3)
        self._price_plot.getAxis("left").setWidth(60)
        self._price_plot.hideAxis("bottom")

        # 2. График объёма
        self.win.nextRow()
        self._volume_plot = self.win.addPlot(row=1, col=0)
        self.win.nextRow()
        self._volume_plot.setMaximumHeight(150)
        self._volume_plot.getAxis("left").setWidth(60)
        self._volume_plot.setXLink(self._price_plot)  # Синхронизация по оси X

        # Элементы графика
        self._candle_items_list: list[pg.GraphicsObject] = []
        self._volume_item = pg.BarGraphItem(x=[], height=[], width=0.6, brushes=[])
        self._volume_plot.addItem(self._volume_item)
        self._sma_item = pg.PlotDataItem(pen=pg.mkPen("#2962ff", width=2))
        self._price_plot.addItem(self._sma_item)
        
        # Элементы для отображения сигналов
        self._entry_markers = pg.ScatterPlotItem(
            symbol='t', size=15, pen=pg.mkPen(None), brush=pg.mkBrush("#26a69a")
        )
        self._exit_markers = pg.ScatterPlotItem(
            symbol='t1', size=15, pen=pg.mkPen(None), brush=pg.mkBrush("#ef5350")
        )
        self._price_plot.addItem(self._entry_markers)
        self._price_plot.addItem(self._exit_markers)

        self.redraw()

    def redraw(self):
        """Полная перерисовка графика на основе DataFrame."""
        for item in self._candle_items_list:
            self._price_plot.removeItem(item)
        self._candle_items_list = []
        
        if self.df.empty:
            return

        df = self.df
        x_coords = list(range(len(df)))

        # Свечи
        for i, (t, row) in enumerate(df.iterrows()):
            is_bullish = row.close >= row.open
            color_str = "#26a69a" if is_bullish else "#ef5350"
            brush = pg.mkBrush(color_str)
            pen = pg.mkPen(color_str)

            # Wick
            wick = pg.QtWidgets.QGraphicsLineItem(i, row.low, i, row.high)
            wick.setPen(pen)
            self._price_plot.addItem(wick)
            self._candle_items_list.append(wick)

            # Body
            body = pg.QtWidgets.QGraphicsRectItem(i - 0.4, row.open, 0.8, row.close - row.open)
            body.setBrush(brush)
            body.setPen(pen)
            self._price_plot.addItem(body)
            self._candle_items_list.append(body)

        # Объёмы
        if self._volume_visible:
            colors = ["#26a69a" if r.close >= r.open else "#ef5350" for _, r in df.iterrows()]
            self._volume_item.setOpts(x=x_coords, height=df.volume, brushes=colors)
        else:
            self._volume_item.setOpts(x=[], height=[])

        # SMA
        if self._sma_visible and len(df) >= self.sma_period:
            sma = df["close"].rolling(self.sma_period).mean().to_numpy()
            self._sma_item.setData(x=x_coords, y=sma)
        else:
            self._sma_item.clear()
        
        # Сигналы входа и выхода
        if self._signals_visible:
            # Отображаем маркеры входа
            entry_x = []
            entry_y = []
            for entry in self._trade_entries:
                if entry['timestamp'] in df.index:
                    idx = df.index.get_loc(entry['timestamp'])
                    if isinstance(idx, slice):
                        # Если получили slice вместо индекса, берем первый элемент
                        idx = idx.start
                    entry_x.append(idx)
                    entry_y.append(df.iloc[idx].low * 0.999)  # Чуть ниже свечи
            
            self._entry_markers.setData(entry_x, entry_y)
            
            # Отображаем маркеры выхода
            exit_x = []
            exit_y = []
            for exit in self._trade_exits:
                if exit['timestamp'] in df.index:
                    idx = df.index.get_loc(exit['timestamp'])
                    if isinstance(idx, slice):
                        # Если получили slice вместо индекса, берем первый элемент
                        idx = idx.start
                    exit_x.append(idx)
                    exit_y.append(df.iloc[idx].high * 1.001)  # Чуть выше свечи
            
            self._exit_markers.setData(exit_x, exit_y)
        else:
            self._entry_markers.clear()
            self._exit_markers.clear()
        
        self._price_plot.autoRange()
        self._volume_plot.autoRange()

    def update_data(self, candle: Candle) -> None:
        new_row = pd.Series(
            {
                "open": float(quotation_to_decimal(candle.open)),
                "close": float(quotation_to_decimal(candle.close)),
                "high": float(quotation_to_decimal(candle.high)),
                "low": float(quotation_to_decimal(candle.low)),
                "volume": candle.volume,
            },
            name=candle.time,
        )
        self.df = pd.concat([self.df, new_row.to_frame().T]).iloc[-self.max_bars :]
        self.redraw()

    def process_strategy_signal(self, signal: Dict[str, Any]) -> None:
        """Обрабатывает сигналы от стратегии."""
        signal_type = signal.get('type')
        
        if signal_type == 'trade_entry':
            self._trade_entries.append(signal)
            self.redraw()
        
        elif signal_type == 'trade_exit':
            self._trade_exits.append(signal)
            self._total_profit = signal.get('total_profit', 0.0)
            self._trades_count += 1
            self._last_trade_profit = signal.get('profit', 0.0)
            if self._last_trade_profit > 0:
                self._winning_trades += 1
                self._win_sum += self._last_trade_profit  # Добавляем прибыль к сумме выигрышей
            
            # Обновляем информацию о сделках
            self.trade_info.update_stats(
                self._total_profit, 
                self._trades_count,
                self._winning_trades,
                self._last_trade_profit,
                self._win_sum
            )
            self.redraw()
        
        elif signal_type == 'strategy_started':
            # Сбрасываем статистику при запуске стратегии
            self._trade_entries = []
            self._trade_exits = []
            self._total_profit = 0.0
            self._trades_count = 0
            self._winning_trades = 0
            self._win_sum = 0.0
            self._last_trade_profit = None
            self.trade_info.setVisible(False)
            self.redraw()
        
        elif signal_type == 'strategy_stopped':
            # Обновляем итоговую статистику
            self._total_profit = signal.get('total_profit', 0.0)
            self._trades_count = signal.get('trades_count', 0)
            self._winning_trades = signal.get('winning_trades', 0)
            
            # Обновляем информацию о сделках
            if self._trades_count > 0:
                self.trade_info.update_stats(
                    self._total_profit, 
                    self._trades_count,
                    self._winning_trades,
                    win_sum=self._win_sum
                )

    def set_volume_visibility(self, visible: bool):
        self._volume_visible = visible
        self.redraw()

    def set_sma_visibility(self, visible: bool):
        self._sma_visible = visible
        self.redraw()

    def set_grid_visibility(self, visible: bool):
        self._price_plot.showGrid(x=visible, y=visible, alpha=0.3)
        self._volume_plot.showGrid(x=visible, y=visible, alpha=0.3)
    
    def set_signals_visibility(self, visible: bool):
        self._signals_visible = visible
        self.redraw()

    def clear_data(self):
        """Clears the DataFrame and redraws the empty chart."""
        self.df = self.df.iloc[0:0]
        self.redraw()

    def set_figi(self, figi: str):
        """Устанавливает новый FIGI для графика."""
        self.figi = figi
        self.clear_data()
        self._trade_entries = []
        self._trade_exits = []
        self._total_profit = 0.0
        self._trades_count = 0
        self._winning_trades = 0
        self._win_sum = 0.0
        self._last_trade_profit = None
        
        # Обновляем информацию в виджете статистики
        if hasattr(self, "_trade_info_widget"):
            self._trade_info_widget.update_stats(0.0, 0, 0, 0.0) 