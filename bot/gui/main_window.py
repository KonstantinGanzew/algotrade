from __future__ import annotations

import asyncio
import importlib
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTabWidget, QMessageBox, QHBoxLayout, QLabel
from qasync import QEventLoop
from PyQt6.QtCore import QTimer
import logging
from tinkoff.invest import CandleInterval

from bot.core.client import InvestClient
from bot.gui.chart import ModernChart
from bot.gui.controls import ControlPanel
from bot.gui.settings import SettingsPanel, Settings
from bot.strategies.base import Strategy

logger = logging.getLogger(__name__)


class ModernWindow(QMainWindow):
    """Основное окно приложения с графиком и настройками."""

    def __init__(self, figi: str):
        super().__init__()
        self.figi = figi
        self._instrument_info = None  # Информация об инструменте
        self._stream_task = None
        self._stream_mgr = None
        self._strategy_instance = None
        self._strategy_running = False
        self._strategy_class_name = "EchoStrategy"  # По умолчанию
        self._strategy_params = {}
        
        self._init_ui()
        self._init_async_loop()
        
        # Загружаем информацию об инструменте
        asyncio.create_task(self._load_instrument_info())
        
    async def _load_instrument_info(self):
        """Загружает информацию об инструменте."""
        try:
            client = InvestClient()
            self._instrument_info = await client.get_instrument_info(self.figi)
            
            # Обновляем заголовок окна
            currency_symbol = Settings().get_currency_symbol(self._instrument_info.get("currency", ""))
            ticker = self._instrument_info.get("ticker", "")
            name = self._instrument_info.get("name", "")
            self.setWindowTitle(f"{name} ({ticker}) - {currency_symbol}")
            
            # Обновляем информацию в GUI
            if hasattr(self, "ticker_label"):
                self.ticker_label.setText(f"{name} ({ticker})")
            if hasattr(self, "currency_label"):
                self.currency_label.setText(f"Валюта: {currency_symbol}")
            
        except Exception as e:
            logger.error("Failed to load instrument info: %s", e)

    def _init_ui(self):
        """Инициализирует пользовательский интерфейс."""
        logger.debug("Initializing ModernWindow for FIGI: %s", self.figi)
        self.setWindowTitle(f"AlgoTrade - {self.figi}")
        self.resize(1200, 800)
        
        # Основной виджет и компоновка
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с информацией об инструменте
        top_panel = QHBoxLayout()
        self.ticker_label = QLabel(f"Инструмент: {self.figi}")
        self.ticker_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.currency_label = QLabel("Валюта: ")
        top_panel.addWidget(self.ticker_label)
        top_panel.addWidget(self.currency_label)
        top_panel.addStretch(1)
        main_layout.addLayout(top_panel)
        
        # Создаем виджет графика
        logger.debug("Creating ModernChart widget...")
        self.chart = ModernChart(figi=self.figi)
        
        # Создаем панель управления
        logger.debug("Creating ControlPanel widget...")
        self.controls = ControlPanel(chart=self.chart)
        
        # Создаем панель настроек
        logger.debug("Creating SettingsPanel widget...")
        self.settings_panel = SettingsPanel()
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        self.tabs.addTab(self.chart, "График")
        self.tabs.addTab(self.settings_panel, "Настройки")
        
        # Добавляем виджеты в основной лейаут
        main_layout.addWidget(self.controls)
        main_layout.addWidget(self.tabs, 1)  # 1 = stretch factor
        
        # Подключаем сигналы
        self.controls.timeframe_changed.connect(self._on_timeframe_change)
        self.controls.instrument_changed.connect(self._on_instrument_change)
        self.controls.start_button.clicked.connect(self._on_start_button_click)
        self.controls.stop_button.clicked.connect(self._on_stop_button_click)
        self.controls.strategy_combo.currentTextChanged.connect(self._on_strategy_change)
        self.settings_panel.token_saved.connect(self._on_token_saved)
        self.settings_panel.strategy_params_saved.connect(self._on_strategy_params_saved)
        
        # Инициализируем состояние кнопок
        self.controls.start_button.setEnabled(True)
        self.controls.stop_button.setEnabled(False)
        
        logger.debug("ModernWindow initialization complete.")

    def _on_timeframe_change(self, interval: CandleInterval):
        """Обрабатывает изменение таймфрейма."""
        self.change_stream(interval)

    def _on_instrument_change(self, figi: str):
        """Обрабатывает изменение выбранного инструмента."""
        logger.info("Changing instrument to %s", figi)
        
        # Останавливаем стратегию, если она запущена
        if self._strategy_running:
            asyncio.create_task(self.stop_strategy())
            
        # Меняем FIGI
        self.figi = figi
        self.chart.set_figi(figi)
        
        # Загружаем информацию о новом инструменте
        asyncio.create_task(self._load_instrument_info())
        
        # Перезапускаем стрим свечей
        current_interval = self.controls.timeframes[self.controls.timeframe_combo.currentText()]
        self.change_stream(current_interval)

    def _on_start_button_click(self):
        """Обрабатывает нажатие кнопки запуска стратегии."""
        asyncio.create_task(self.start_strategy())

    def _on_stop_button_click(self):
        """Обрабатывает нажатие кнопки остановки стратегии."""
        asyncio.create_task(self.stop_strategy())

    def _on_strategy_change(self, strategy_name: str):
        """Обрабатывает изменение выбранной стратегии."""
        self._strategy_class_name = strategy_name
        self._strategy_params = {}
        self.controls.set_strategy_name(strategy_name)

    def _on_token_saved(self, new_token: str):
        """Обрабатывает сохранение нового токена API."""
        logger.info("API token has been updated. Reconnecting...")
        # Перезапускаем текущий стрим, чтобы использовать новый токен
        current_interval = self.controls.timeframes[self.controls.timeframe_combo.currentText()]
        self.change_stream(current_interval)

    def _on_strategy_params_saved(self, params: dict):
        """Обрабатывает сохранение новых параметров стратегии."""
        strategy_name = params["strategy"]
        strategy_params = params["params"]
        
        logger.info("Strategy parameters updated: %s %s", strategy_name, strategy_params)
        
        # Сохраняем параметры для последующего использования
        self._strategy_class_name = strategy_name
        self._strategy_params = strategy_params
        
        # Обновляем имя стратегии в панели управления
        self.controls.set_strategy_name(strategy_name)

    def change_stream(self, interval: CandleInterval):
        """Cancels the old stream task and starts a new one for the given interval."""

        async def _async_change_stream():
            # Cancel and wait for the old task to finish
            if self._stream_task:
                logger.debug("Cancelling previous stream task...")
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    logger.debug("Stream task for %s was cancelled.", interval.name)
                self._stream_task = None

            # Start the new task
            self.chart.clear_data()
            logger.info("Starting new candle stream for interval: %s", interval.name)
            self._stream_task = asyncio.create_task(self._stream_candles(interval))

        asyncio.create_task(_async_change_stream())

    async def _stream_candles(self, interval: CandleInterval) -> None:
        """Subscribes to candles and updates the chart."""
        logger.debug("Stream task started for interval: %s", interval.name)
        try:
            async with InvestClient() as ic:
                logger.debug("InvestClient entered for interval: %s", interval.name)
                self._stream_mgr, self._stream_task = await ic.stream_candles(
                    figi=self.figi, interval=interval
                )
                async for candle in self._stream_task:
                    self.chart.update_data(candle)
                    
                    # Если стратегия запущена, отправляем ей свечи
                    if self._strategy_instance:
                        try:
                            await self._strategy_instance.on_candle(candle)
                        except Exception as e:
                            logger.error("Error in strategy.on_candle: %s", e)
                            self._show_strategy_error(f"Ошибка обработки свечи: {e}")
                            await self.stop_strategy()
                    
        except asyncio.CancelledError:
            # This is expected on timeframe change or close
            logger.debug("Stream task for %s was cancelled.", interval.name)
        except Exception:
            logger.exception("An error occurred in the candle stream:")
        finally:
            if self._stream_mgr:
                logger.debug("Stopping stream manager...")
                self._stream_mgr.stop()
            logger.debug("Stream task for %s finished.", interval.name)

    def _create_strategy_instance(self) -> Strategy:
        """Создаёт экземпляр выбранной стратегии с указанными параметрами."""
        try:
            # Преобразуем CamelCase имя класса в snake_case для модуля
            # Например, SmaCrossStrategy -> sma_cross
            module_name = self._strategy_class_name
            if module_name == "SmaCrossStrategy":
                module_path = "bot.strategies.sma_cross"
            elif module_name == "EchoStrategy":
                module_path = "bot.strategies.echo"
            else:
                # Можно добавить другие стратегии по мере необходимости
                raise ValueError(f"Неизвестный класс стратегии: {module_name}")
            
            # Импортируем модуль стратегии
            module = importlib.import_module(module_path)
            
            # Получаем класс стратегии
            strategy_class = getattr(module, self._strategy_class_name)
            
            # Используем "заглушку" для клиента вместо создания нового InvestClient
            # Реальные запросы будут отправляться через InvestClient, который создается в _stream_candles
            class ClientStub:
                """Заглушка для клиента API, чтобы избежать создания нового соединения."""
                async def place_market_order(self, figi: str, qty: int, direction: str) -> None:
                    """Делегирует запрос на выполнение ордера в основной UI поток."""
                    logger.info("Strategy requested market order: %s %d lots of %s", 
                                direction.upper(), qty, figi)
                    # TODO: В будущем здесь будет код для выполнения ордера
                    # через централизованный InvestClient в GUI
            
            # Создаем стратегию с параметрами
            if self._strategy_class_name == "SmaCrossStrategy":
                params = self._strategy_params.get("sma_cross", {})
                return strategy_class(
                    client=ClientStub(),
                    figi=self.figi,
                    fast=params.get("fast", 20),
                    slow=params.get("slow", 50),
                    qty=params.get("qty", 1),
                    on_signal_callback=self._on_strategy_signal
                )
            else:
                return strategy_class(
                    client=ClientStub(), 
                    figi=self.figi,
                    on_signal_callback=self._on_strategy_signal
                )
                
        except Exception as e:
            logger.exception("Error creating strategy instance")
            raise RuntimeError(f"Не удалось создать экземпляр стратегии: {e}")
    
    async def start_strategy(self):
        """Запускает выбранную стратегию."""
        if self._strategy_instance:
            logger.warning("Strategy is already running")
            return
            
        try:
            # Создаем экземпляр стратегии
            self._strategy_instance = self._create_strategy_instance()
            logger.info("Starting strategy: %s", self._strategy_class_name)
            
            # Вызываем хук on_start
            await self._strategy_instance.on_start()
            
            # Отмечаем в UI
            logger.info("Strategy started successfully")
            
        except Exception as e:
            logger.exception("Failed to start strategy")
            self._show_strategy_error(f"Ошибка запуска стратегии: {e}")
            await self.stop_strategy()
    
    async def stop_strategy(self):
        """Останавливает текущую стратегию."""
        if not self._strategy_instance:
            return
            
        try:
            # Вызываем хук on_stop
            await self._strategy_instance.on_stop()
            logger.info("Strategy stopped successfully")
        except Exception as e:
            logger.exception("Error stopping strategy")
        
        # Очищаем
        self._strategy_instance = None
    
    def _show_strategy_error(self, error_message: str):
        """Отображает ошибку стратегии в UI."""
        self.controls.strategy_error(error_message)
        QMessageBox.critical(
            self, 
            "Ошибка стратегии", 
            error_message
        )
    
    def closeEvent(self, event):
        """Ensure task is cancelled on window close."""
        logger.debug("Close event received, cancelling stream task.")
        if self._stream_task:
            self._stream_task.cancel()
            
        # Останавливаем стратегию при закрытии
        if self._strategy_instance:
            asyncio.create_task(self.stop_strategy())
        
        event.accept()

    def _on_strategy_signal(self, signal: dict):
        """Обрабатывает сигналы от стратегии."""
        logger.debug("Received strategy signal: %s", signal.get('type', 'unknown'))
        # Передаем сигнал в график для отображения
        self.chart.process_strategy_signal(signal)


def run(figi: str = "BBG004730N88") -> None:
    """Entry-point для запуска GUI-приложения."""
    logger.info("Starting GUI application for FIGI: %s", figi)
    app = QApplication([])
    logger.debug("QApplication created.")
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    logger.debug("Asyncio event loop configured with qasync.")

    win = ModernWindow(figi)
    logger.debug("Showing ModernWindow.")
    win.show()

    try:
        with loop:
            logger.info("Starting event loop...")
            loop.run_forever()
    except KeyboardInterrupt:
        logger.info("GUI application stopped by user.")
    finally:
        logger.info("Event loop finished.")


if __name__ == "__main__":
    run() 