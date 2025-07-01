from __future__ import annotations

import logging
from typing import Dict, Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QLabel, 
    QPushButton, QCheckBox, QFrame, QGroupBox
)
from tinkoff.invest.schemas import CandleInterval

from bot.config import Settings, POPULAR_INSTRUMENTS
from bot.gui.chart import ModernChart

logger = logging.getLogger(__name__)


class ControlPanel(QWidget):
    """Панель управления для графика и стратегий."""

    # Сигналы
    timeframe_changed = pyqtSignal(object)  # CandleInterval
    instrument_changed = pyqtSignal(str)  # FIGI

    def __init__(self, chart: ModernChart):
        super().__init__()
        self.chart = chart
        
        # Словарь таймфреймов
        self.timeframes = {
            "1 мин": CandleInterval.CANDLE_INTERVAL_1_MIN,
            "5 мин": CandleInterval.CANDLE_INTERVAL_5_MIN,
            "15 мин": CandleInterval.CANDLE_INTERVAL_15_MIN,
            "1 час": CandleInterval.CANDLE_INTERVAL_HOUR,
            "1 день": CandleInterval.CANDLE_INTERVAL_DAY,
        }
        
        # Словарь стратегий
        self.strategies = {
            "EchoStrategy": "Эхо (тест)",
            "SmaCrossStrategy": "SMA-Cross",
        }
        
        # Список инструментов
        self.instruments = Settings().get_favorite_instruments()
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        # --- Группа выбора инструмента ---
        instrument_group = QGroupBox("Инструмент")
        instrument_layout = QVBoxLayout(instrument_group)
        
        # Комбобокс для выбора инструмента
        self.instrument_combo = QComboBox()
        for instrument in self.instruments:
            self.instrument_combo.addItem(
                f"{instrument['name']} ({instrument['ticker']})", 
                instrument['figi']
            )
        self.instrument_combo.currentIndexChanged.connect(self._on_instrument_change)
        
        instrument_layout.addWidget(self.instrument_combo)
        main_layout.addWidget(instrument_group)
        
        # --- Группа настроек графика ---
        chart_group = QGroupBox("График")
        chart_layout = QVBoxLayout(chart_group)
        
        # Контролы графика в горизонтальном лейауте
        chart_controls = QHBoxLayout()
        
        # Выбор таймфрейма
        tf_label = QLabel("Таймфрейм:")
        chart_controls.addWidget(tf_label)
        
        self.timeframe_combo = QComboBox()
        for tf_name in self.timeframes:
            self.timeframe_combo.addItem(tf_name)
        self.timeframe_combo.currentTextChanged.connect(self._on_timeframe_change)
        chart_controls.addWidget(self.timeframe_combo)
        
        chart_controls.addSpacing(20)  # Разделитель
        
        # Чекбоксы для отображения элементов графика
        self.volume_chk = QCheckBox("Объем", self)
        self.volume_chk.setChecked(True)  # Включено по-умолчанию
        self.volume_chk.stateChanged.connect(self._toggle_volume)
        chart_controls.addWidget(self.volume_chk)
        
        self.grid_chk = QCheckBox("Сетка", self)
        self.grid_chk.setChecked(True)  # Включено по-умолчанию
        self.grid_chk.stateChanged.connect(self._toggle_grid)
        chart_controls.addWidget(self.grid_chk)
        
        self.ma_chk = QCheckBox("SMA(20)", self)
        self.ma_chk.setChecked(False)  # Отключено по-умолчанию
        self.ma_chk.stateChanged.connect(self._toggle_sma)
        chart_controls.addWidget(self.ma_chk)
        
        self.signals_chk = QCheckBox("Сигналы", self)
        self.signals_chk.setChecked(True)  # Включено по-умолчанию
        self.signals_chk.stateChanged.connect(self._toggle_signals)
        chart_controls.addWidget(self.signals_chk)

        chart_controls.addStretch(1)  # Заполнитель
        
        chart_layout.addLayout(chart_controls)
        main_layout.addWidget(chart_group)
        
        # --- Группа управления стратегией ---
        strategy_group = QGroupBox("Стратегия")
        strategy_layout = QVBoxLayout(strategy_group)
        
        # Верхний ряд: выбор стратегии и статус
        strategy_top = QHBoxLayout()
        
        # Выбор стратегии
        self.strategy_combo = QComboBox()
        for strategy_id, strategy_name in self.strategies.items():
            self.strategy_combo.addItem(strategy_name, strategy_id)
        strategy_top.addWidget(self.strategy_combo)
        
        # Индикатор статуса
        self.status_label = QLabel("Остановлена")
        self.status_label.setStyleSheet("color: #ef5350; font-weight: bold;")
        strategy_top.addWidget(self.status_label)
        
        strategy_top.addStretch(1)  # Заполнитель
        
        # Нижний ряд: кнопки управления
        strategy_bottom = QHBoxLayout()
        
        # Кнопка запуска
        self.start_button = QPushButton("Старт")
        self.start_button.setStyleSheet("background-color: #26a69a; color: white;")
        strategy_bottom.addWidget(self.start_button)
        
        # Кнопка остановки
        self.stop_button = QPushButton("Стоп")
        self.stop_button.setStyleSheet("background-color: #ef5350; color: white;")
        self.stop_button.setEnabled(False)  # Изначально отключена
        strategy_bottom.addWidget(self.stop_button)
        
        # Добавляем ряды в лейаут группы
        strategy_layout.addLayout(strategy_top)
        strategy_layout.addLayout(strategy_bottom)
        
        main_layout.addWidget(strategy_group)
        
        # Устанавливаем соотношение ширины групп
        main_layout.setStretch(0, 1)  # Инструмент
        main_layout.setStretch(1, 2)  # График
        main_layout.setStretch(2, 1)  # Стратегия
    
    def set_strategy_running(self, running: bool):
        """Обновляет состояние UI в зависимости от статуса стратегии."""
        if running:
            self.status_label.setText("Запущена")
            self.status_label.setStyleSheet("color: #26a69a; font-weight: bold;")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.strategy_combo.setEnabled(False)
        else:
            self.status_label.setText("Остановлена")
            self.status_label.setStyleSheet("color: #ef5350; font-weight: bold;")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.strategy_combo.setEnabled(True)
    
    def set_strategy_name(self, strategy_class_name: str):
        """Устанавливает текущую стратегию в комбобоксе."""
        for i in range(self.strategy_combo.count()):
            if self.strategy_combo.itemData(i) == strategy_class_name:
                self.strategy_combo.setCurrentIndex(i)
                break
    
    def get_current_strategy(self) -> str:
        """Возвращает идентификатор текущей выбранной стратегии."""
        return self.strategy_combo.currentData()
    
    def get_current_instrument(self) -> str:
        """Возвращает FIGI текущего выбранного инструмента."""
        return self.instrument_combo.currentData()
    
    def _toggle_volume(self, state: int):
        self.chart.set_volume_visibility(bool(state))
    
    def _toggle_grid(self, state: int):
        self.chart.set_grid_visibility(bool(state))
    
    def _toggle_sma(self, state: int):
        self.chart.set_sma_visibility(bool(state))
        
    def _toggle_signals(self, state: int):
        self.chart.set_signals_visibility(bool(state))

    def _on_timeframe_change(self, text: str):
        interval = self.timeframes[text]
        self.timeframe_changed.emit(interval)
        
    def _on_instrument_change(self, index: int):
        if index >= 0:
            figi = self.instrument_combo.itemData(index)
            self.instrument_changed.emit(figi) 