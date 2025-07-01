import asyncio
import sys
from pathlib import Path

# Ensure project root (one level up from /tests) is on sys.path for import resolution
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from bot.core.client import InvestClient

FIGI = "BBG004730N88"  # Sberbank shares


@pytest.mark.asyncio
async def test_account_retrieval():
    """Ensure we can open sandbox session and read / create account."""
    async with InvestClient() as ic:
        account_id = await ic.account_id()
        assert isinstance(account_id, str) and account_id


@pytest.mark.asyncio
async def test_stream_candles():
    """Subscribe to candle stream and receive at least one update within timeout."""
    async with InvestClient() as ic:
        gen = ic.stream_candles(figi=FIGI)

        try:
            candle = await asyncio.wait_for(gen.__anext__(), timeout=30)
        finally:
            # Properly close generator if still running
            if hasattr(gen, "aclose"):
                await gen.aclose()

        assert candle.figi == FIGI 