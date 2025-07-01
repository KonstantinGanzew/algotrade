from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QWidget, QComboBox, QLabel, 
    QPushButton, QFrame, QVBoxLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from tinkoff.invest import CandleInterval

from bot.gui.chart import ModernChart


class ControlPanel(QWidget):
    """Панель управления графиком (чекбоксы, индикаторы, таймфрейм) и стратегией."""

    timeframe_changed = pyqtSignal(CandleInterval)
    strategy_start = pyqtSignal()
    strategy_stop = pyqtSignal()

    def __init__(self, chart: ModernChart):
        super().__init__()
        self.chart = chart
        self.strategy_running = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Основная панель с чекбоксами и таймфреймом
        chart_controls = QHBoxLayout()
        chart_controls.setContentsMargins(0, 0, 0, 0)

        # --- Чекбоксы -----------------------------------------------------
        self.grid_chk = QCheckBox("Grid", self)
        self.grid_chk.setChecked(True)
        self.grid_chk.stateChanged.connect(self._toggle_grid)
        chart_controls.addWidget(self.grid_chk)

        self.volume_chk = QCheckBox("Volume", self)
        self.volume_chk.setChecked(True)
        self.volume_chk.stateChanged.connect(self._toggle_volume)
        chart_controls.addWidget(self.volume_chk)

        self.ma_chk = QCheckBox("SMA(20)", self)
        self.ma_chk.setChecked(False)  # Отключено по-умолчанию
        self.ma_chk.stateChanged.connect(self._toggle_sma)
        chart_controls.addWidget(self.ma_chk)

        self.signals_chk = QCheckBox("Сигналы", self)
        self.signals_chk.setChecked(True)  # Включено по-умолчанию
        self.signals_chk.stateChanged.connect(self._toggle_signals)
        chart_controls.addWidget(self.signals_chk)

        chart_controls.addStretch(1)  # Заполнитель

        # --- Выбор таймфрейма ---
        chart_controls.addWidget(QLabel("Таймфрейм:"))
        self.timeframe_combo = QComboBox(self)
        self.timeframes = {
            "1 минута": CandleInterval.CANDLE_INTERVAL_1_MIN,
            "5 минут": CandleInterval.CANDLE_INTERVAL_5_MIN,
            "15 минут": CandleInterval.CANDLE_INTERVAL_15_MIN,
            "1 час": CandleInterval.CANDLE_INTERVAL_HOUR,
            "1 день": CandleInterval.CANDLE_INTERVAL_DAY,
        }
        self.timeframe_combo.addItems(self.timeframes.keys())
        self.timeframe_combo.currentTextChanged.connect(self._on_timeframe_change)
        chart_controls.addWidget(self.timeframe_combo)

        main_layout.addLayout(chart_controls)

        # Разделительная линия
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Панель управления стратегией
        strategy_controls = QHBoxLayout()
        strategy_controls.setContentsMargins(0, 0, 0, 0)

        self.strategy_label = QLabel("Стратегия:")
        strategy_controls.addWidget(self.strategy_label)

        self.strategy_name_label = QLabel("не выбрана")
        self.strategy_name_label.setStyleSheet("font-weight: bold;")
        strategy_controls.addWidget(self.strategy_name_label)

        strategy_controls.addStretch(1)

        self.status_label = QLabel("Статус: остановлена")
        strategy_controls.addWidget(self.status_label)

        self.start_button = QPushButton("Старт")
        self.start_button.setFixedWidth(80)
        self.start_button.clicked.connect(self._on_start_clicked)
        strategy_controls.addWidget(self.start_button)

        self.stop_button = QPushButton("Стоп")
        self.stop_button.setFixedWidth(80)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        strategy_controls.addWidget(self.stop_button)

        main_layout.addLayout(strategy_controls)

    def _toggle_grid(self, state: int):
        self.chart.set_grid_visibility(bool(state))

    def _toggle_volume(self, state: int):
        self.chart.set_volume_visibility(bool(state))

    def _toggle_sma(self, state: int):
        self.chart.set_sma_visibility(bool(state))

    def _toggle_signals(self, state: int):
        self.chart.set_signals_visibility(bool(state))

    def _on_timeframe_change(self, text: str):
        interval = self.timeframes[text]
        self.timeframe_changed.emit(interval)
    
    def _on_start_clicked(self):
        """Обработчик нажатия на кнопку Старт."""
        self.strategy_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Статус: запущена")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.strategy_start.emit()
    
    def _on_stop_clicked(self):
        """Обработчик нажатия на кнопку Стоп."""
        self.strategy_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Статус: остановлена")
        self.status_label.setStyleSheet("color: red;")
        self.strategy_stop.emit()
    
    def set_strategy_name(self, name: str):
        """Устанавливает имя текущей стратегии."""
        self.strategy_name_label.setText(name)
    
    def strategy_error(self, error_text: str):
        """Отображает ошибку стратегии и сбрасывает состояние."""
        self.strategy_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Статус: ошибка")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # Сброс статуса можно реализовать через диалоговое окно с сообщением об ошибке 