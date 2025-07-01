from pathlib import Path
import logging
import json
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Список популярных инструментов с их FIGI и человекочитаемыми названиями
POPULAR_INSTRUMENTS = [
    {"figi": "BBG004730N88", "name": "Сбербанк", "ticker": "SBER", "currency": "RUB"},
    {"figi": "BBG000B9XRY4", "name": "Apple", "ticker": "AAPL", "currency": "USD"},
    {"figi": "BBG004S68507", "name": "Яндекс", "ticker": "YNDX", "currency": "RUB"},
    {"figi": "BBG000BPH459", "name": "NVIDIA", "ticker": "NVDA", "currency": "USD"},
    {"figi": "BBG000BVPV84", "name": "Microsoft", "ticker": "MSFT", "currency": "USD"},
    {"figi": "BBG004731354", "name": "Газпром", "ticker": "GAZP", "currency": "RUB"},
    {"figi": "BBG000BDTBL9", "name": "Tesla", "ticker": "TSLA", "currency": "USD"},
    {"figi": "BBG004RVFCY3", "name": "Лукойл", "ticker": "LKOH", "currency": "RUB"},
    {"figi": "BBG000BWXBC2", "name": "Amazon", "ticker": "AMZN", "currency": "USD"},
    {"figi": "BBG000BX7DH0", "name": "Meta", "ticker": "META", "currency": "USD"},
]

# Словарь валют для человекочитаемого отображения
CURRENCY_DISPLAY = {
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CHF": "Fr",
    "JPY": "¥",
    "CNY": "¥",
    "HKD": "HK$",
    "TRY": "₺",
}


class Settings:
    """Настройки приложения."""

    def __init__(self):
        self._settings_file = Path("settings.json")
        self._conf_file = Path("conf")
        self._settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из JSON-файла."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r") as f:
                    settings = json.load(f)
                logger.info("Loaded tokens from settings.json")
                return settings
            except json.JSONDecodeError:
                logger.warning("Failed to parse settings.json, using default settings")
        return {"tokens": {}, "strategies": {}}

    def save_settings(self) -> None:
        """Сохраняет настройки в JSON-файл."""
        with open(self._settings_file, "w") as f:
            json.dump(self._settings, f, indent=2)
        logger.info("Saved settings to settings.json")

    def get_token(self, sandbox: bool = True) -> str:
        """Возвращает токен API для указанного режима."""
        # Сначала проверяем настройки
        token_key = "sandbox_token" if sandbox else "production_token"
        token = self._settings.get("tokens", {}).get(token_key)
        
        # Если токена нет в настройках, проверяем файл conf
        if not token and self._conf_file.exists():
            with open(self._conf_file, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        token = line.strip()
                        break
        
        # Если токена всё ещё нет, проверяем переменные окружения
        if not token:
            env_var = "TINKOFF_SANDBOX_TOKEN" if sandbox else "TINKOFF_PRODUCTION_TOKEN"
            token = os.environ.get(env_var, "")
        
        if not token:
            logger.warning("API token not found, using empty token")
        
        return token

    def set_token(self, token: str, sandbox: bool = True) -> None:
        """Устанавливает токен API для указанного режима."""
        token_key = "sandbox_token" if sandbox else "production_token"
        if "tokens" not in self._settings:
            self._settings["tokens"] = {}
        self._settings["tokens"][token_key] = token
        self.save_settings()
        
        # Также сохраняем в файл conf для обратной совместимости
        if sandbox:
            with open(self._conf_file, "w") as f:
                f.write(token)
            logger.info("Saved sandbox token to conf file")

    def get_strategy_params(self, strategy_name: str) -> Dict[str, Any]:
        """Возвращает параметры стратегии."""
        return self._settings.get("strategies", {}).get(strategy_name, {})

    def set_strategy_params(self, strategy_name: str, params: Dict[str, Any]) -> None:
        """Устанавливает параметры стратегии."""
        if "strategies" not in self._settings:
            self._settings["strategies"] = {}
        self._settings["strategies"][strategy_name] = params
        self.save_settings()

    def get_favorite_instruments(self) -> List[Dict[str, str]]:
        """Возвращает список избранных инструментов."""
        return self._settings.get("favorite_instruments", POPULAR_INSTRUMENTS[:5])

    def set_favorite_instruments(self, instruments: List[Dict[str, str]]) -> None:
        """Устанавливает список избранных инструментов."""
        self._settings["favorite_instruments"] = instruments
        self.save_settings()

    def add_favorite_instrument(self, instrument: Dict[str, str]) -> None:
        """Добавляет инструмент в избранное."""
        if "favorite_instruments" not in self._settings:
            self._settings["favorite_instruments"] = []
        
        # Проверяем, есть ли уже такой инструмент
        for i, item in enumerate(self._settings["favorite_instruments"]):
            if item["figi"] == instrument["figi"]:
                # Обновляем существующий инструмент
                self._settings["favorite_instruments"][i] = instrument
                self.save_settings()
                return
        
        # Добавляем новый инструмент
        self._settings["favorite_instruments"].append(instrument)
        self.save_settings()

    def remove_favorite_instrument(self, figi: str) -> None:
        """Удаляет инструмент из избранного."""
        if "favorite_instruments" in self._settings:
            self._settings["favorite_instruments"] = [
                item for item in self._settings["favorite_instruments"] 
                if item["figi"] != figi
            ]
            self.save_settings()

    def get_currency_symbol(self, currency_code: str) -> str:
        """Возвращает символ валюты для отображения."""
        return CURRENCY_DISPLAY.get(currency_code, currency_code)


# Initialize global settings instance
settings = Settings() 