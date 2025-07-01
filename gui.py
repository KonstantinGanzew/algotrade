#!/usr/bin/env python3
"""
Графический интерфейс для алгоритмической торговли.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
import qasync

from bot.config import Settings, POPULAR_INSTRUMENTS
from bot.gui.main_window import ModernWindow, run


def setup_logging():
    """Настраивает логирование."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_format = "%H:%M:%S"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Отключаем лишние логи от библиотек
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("grpc").setLevel(logging.WARNING)


def parse_args():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(description="AlgoTrade GUI")
    parser.add_argument(
        "-f", "--figi", 
        type=str, 
        default=None,
        help="FIGI инструмента для торговли"
    )
    return parser.parse_args()


def main():
    """Точка входа в приложение."""
    setup_logging()
    args = parse_args()
    
    # Если FIGI не указан, используем первый инструмент из списка
    if args.figi is None:
        favorite_instruments = Settings().get_favorite_instruments()
        if favorite_instruments:
            args.figi = favorite_instruments[0]["figi"]
        else:
            args.figi = POPULAR_INSTRUMENTS[0]["figi"]
    
    # Запускаем GUI
    app = QApplication(sys.argv)
    app.setApplicationName("AlgoTrade")
    app.setApplicationDisplayName("AlgoTrade")
    
    # Создаем и запускаем главное окно
    run(args.figi)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()