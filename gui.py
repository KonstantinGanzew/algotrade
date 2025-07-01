"""Запуск простого GUI-окна с онлайн-свечами.

Использование:
    python gui.py --figi BBG004730N88
"""
from __future__ import annotations

import argparse
import logging

from bot.gui.main_window import run

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:  # noqa: D401
    parser = argparse.ArgumentParser(description="Tinkoff Invest sandbox GUI")
    parser.add_argument("--figi", "-f", default="BBG004730N88", help="FIGI инструмента")
    args = parser.parse_args()

    run(figi=args.figi)


if __name__ == "__main__":
    main()