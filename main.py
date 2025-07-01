import logging
from aiorun import run
import argparse

from bot.core.client import InvestClient
from bot.strategies.echo import EchoStrategy

# Example FIGI for Sberbank (shares). Replace/extend if needed.
DEFAULT_FIGI = "BBG004730N88"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    "echo": EchoStrategy,
}

try:
    from bot.strategies.sma_cross import SmaCrossStrategy

    STRATEGY_MAP["sma"] = SmaCrossStrategy
except ImportError:
    # Ignore if pandas not installed yet
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Tinkoff Invest MVP bot")
    parser.add_argument("--strategy", "-s", choices=STRATEGY_MAP.keys(), default="echo")
    parser.add_argument("--figi", "-f", default=DEFAULT_FIGI, help="Instrument FIGI to trade")
    return parser.parse_args()


async def run_bot() -> None:
    args = parse_args()

    strategy_cls = STRATEGY_MAP[args.strategy]

    logger.info("Starting %s strategy on %s", strategy_cls.name, args.figi)

    async with InvestClient() as ic:
        strategy = strategy_cls(ic, args.figi)
        async for candle in ic.stream_candles(figi=args.figi):
            await strategy.on_candle(candle)


def main():
    run(run_bot())


if __name__ == "__main__":
    main() 