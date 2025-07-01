from __future__ import annotations

import abc
from typing import Any


class Strategy(abc.ABC):
    """Abstract base class for all user strategies."""

    name: str = "AbstractStrategy"

    def __init__(self, client: Any, figi: str) -> None:  # Any to avoid heavy deps in base
        self.client = client
        self.figi = figi

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    async def on_start(self) -> None:  # noqa: D401
        """Called when strategy is started (before first market event)."""
        pass

    async def on_stop(self) -> None:  # noqa: D401
        """Called on graceful shutdown (Ctrl+C etc.)."""
        pass

    @abc.abstractmethod
    async def on_candle(self, candle) -> None:  # noqa: D401
        """Handle new candle event."""
        raise NotImplementedError 