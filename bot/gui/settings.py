from __future__ import annotations

import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QFormLayout, QTabWidget,
    QSpinBox, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from bot.config import Settings


class SettingsPanel(QWidget):
    """Панель настроек приложения и стратегий."""
    
    # Сигналы для уведомления о изменении настроек
    token_changed = pyqtSignal(str)
    strategy_params_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Загрузка текущих настроек
        self.settings_file = Path(__file__).resolve().parent.parent.parent / "settings.json"
        self.settings = self._load_settings()
        
        # Создаем основной лейаут и вкладки
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget()
        
        # Вкладка с токенами
        token_tab = QWidget()
        token_layout = QFormLayout(token_tab)
        
        # Группа настроек API
        api_group = QGroupBox("Настройки API")
        api_layout = QFormLayout(api_group)
        
        # Поле для ввода токена песочницы
        self.sandbox_token_edit = QLineEdit()
        self.sandbox_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.sandbox_token_edit.setText(self._get_current_sandbox_token())
        api_layout.addRow("Токен песочницы:", self.sandbox_token_edit)
        
        # Поле для ввода боевого токена
        self.production_token_edit = QLineEdit()
        self.production_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.production_token_edit.setText(self._get_current_prod_token())
        api_layout.addRow("Боевой токен:", self.production_token_edit)
        
        # Кнопка выбора конфигурационного файла
        file_select_layout = QHBoxLayout()
        self.conf_path_edit = QLineEdit()
        self.conf_path_edit.setText(str(Path("conf").resolve()))
        self.conf_path_edit.setReadOnly(True)
        file_select_layout.addWidget(self.conf_path_edit, 1)
        
        browse_button = QPushButton("Обзор...")
        browse_button.clicked.connect(self._browse_conf_file)
        file_select_layout.addWidget(browse_button)
        
        api_layout.addRow("Путь к файлу conf:", file_select_layout)
        
        # Кнопка сохранения токенов
        save_token_button = QPushButton("Сохранить токены")
        save_token_button.clicked.connect(self._save_tokens)
        
        token_layout.addWidget(api_group)
        token_layout.addWidget(save_token_button)
        
        # Вкладка с настройками стратегий
        strategy_tab = QWidget()
        strategy_layout = QVBoxLayout(strategy_tab)
        
        # Выбор стратегии
        strategy_select_layout = QHBoxLayout()
        strategy_select_layout.addWidget(QLabel("Стратегия:"))
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["EchoStrategy", "SmaCrossStrategy"])
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_change)
        strategy_select_layout.addWidget(self.strategy_combo)
        
        strategy_layout.addLayout(strategy_select_layout)
        
        # Настройки SMA-Cross стратегии
        self.sma_settings = QGroupBox("Параметры SMA-Cross")
        sma_layout = QFormLayout(self.sma_settings)
        
        self.fast_sma_spin = QSpinBox()
        self.fast_sma_spin.setRange(1, 200)
        self.fast_sma_spin.setValue(self.settings.get("sma_cross", {}).get("fast", 20))
        sma_layout.addRow("Быстрая SMA (период):", self.fast_sma_spin)
        
        self.slow_sma_spin = QSpinBox()
        self.slow_sma_spin.setRange(2, 500)
        self.slow_sma_spin.setValue(self.settings.get("sma_cross", {}).get("slow", 50))
        sma_layout.addRow("Медленная SMA (период):", self.slow_sma_spin)
        
        self.sma_qty_spin = QSpinBox()
        self.sma_qty_spin.setRange(1, 100)
        self.sma_qty_spin.setValue(self.settings.get("sma_cross", {}).get("qty", 1))
        sma_layout.addRow("Количество лотов:", self.sma_qty_spin)
        
        strategy_layout.addWidget(self.sma_settings)
        
        # Кнопка сохранения настроек стратегии
        save_strategy_button = QPushButton("Сохранить настройки стратегии")
        save_strategy_button.clicked.connect(self._save_strategy_settings)
        
        strategy_layout.addWidget(save_strategy_button)
        strategy_layout.addStretch(1)
        
        # Добавляем вкладки
        tab_widget.addTab(token_tab, "API Токены")
        tab_widget.addTab(strategy_tab, "Стратегии")
        
        main_layout.addWidget(tab_widget)
        
        # Показываем настройки для выбранной стратегии
        self._on_strategy_change(self.strategy_combo.currentText())
    
    def _get_current_sandbox_token(self):
        """Получает текущий токен песочницы."""
        try:
            return self.settings.get("sandbox_token", "") or Settings()._conf_path.read_text(encoding="utf-8").splitlines()[0].split()[0]
        except:
            return ""
    
    def _get_current_prod_token(self):
        """Получает текущий боевой токен."""
        try:
            return self.settings.get("production_token", "")
        except:
            return ""
    
    def _browse_conf_file(self):
        """Открывает диалог выбора файла для conf."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл конфигурации", str(Path().resolve()), "All Files (*)"
        )
        if filename:
            self.conf_path_edit.setText(filename)
    
    def _save_tokens(self):
        """Сохраняет токены в конфигурационный файл."""
        # Сохраняем в settings.json
        self.settings["sandbox_token"] = self.sandbox_token_edit.text()
        self.settings["production_token"] = self.production_token_edit.text()
        self._save_settings()
        
        # Обновляем conf файл
        try:
            conf_path = Path(self.conf_path_edit.text())
            with open(conf_path, "w", encoding="utf-8") as f:
                if self.sandbox_token_edit.text():
                    f.write(f"{self.sandbox_token_edit.text()} песочница\n")
                if self.production_token_edit.text():
                    f.write(f"{self.production_token_edit.text()} прод\n")
            
            QMessageBox.information(self, "Успех", "Токены успешно сохранены")
            self.token_changed.emit(self.sandbox_token_edit.text())
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить токены: {e}")
    
    def _on_strategy_change(self, strategy_name: str):
        """Показывает настройки выбранной стратегии."""
        self.sma_settings.setVisible(strategy_name == "SmaCrossStrategy")
    
    def _save_strategy_settings(self):
        """Сохраняет настройки выбранной стратегии."""
        strategy = self.strategy_combo.currentText()
        
        if strategy == "SmaCrossStrategy":
            fast = self.fast_sma_spin.value()
            slow = self.slow_sma_spin.value()
            
            if fast >= slow:
                QMessageBox.warning(
                    self, "Неверные параметры", 
                    "Период быстрой SMA должен быть меньше периода медленной SMA"
                )
                return
            
            self.settings["sma_cross"] = {
                "fast": fast,
                "slow": slow,
                "qty": self.sma_qty_spin.value()
            }
        
        self._save_settings()
        self.strategy_params_changed.emit({
            "strategy": strategy,
            "params": self.settings.get(strategy.lower(), {})
        })
        QMessageBox.information(self, "Успех", "Настройки стратегии успешно сохранены")
    
    def _load_settings(self):
        """Загружает настройки из файла."""
        if not self.settings_file.exists():
            return {
                "sma_cross": {"fast": 20, "slow": 50, "qty": 1}
            }
        
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "sma_cross": {"fast": 20, "slow": 50, "qty": 1}
            }
    
    def _save_settings(self):
        """Сохраняет настройки в файл."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {e}") 