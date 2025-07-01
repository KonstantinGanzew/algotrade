from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class Settings:
    """Load tokens from a text file named ``conf`` that resides in the project root
    or from settings.json if it exists.
    
    When loading from conf file, each line must have the following format::

        <token> <label>

    where *label* is either ``песочница`` (sandbox) or ``прод`` (production).
    """

    def __init__(self, conf_path: Path | str | None = None) -> None:
        # Try to load from settings.json first
        self.settings_file = Path(__file__).resolve().parent.parent / "settings.json"
        self.sandbox_token: str | None = None
        self.production_token: str | None = None
        
        # Try to load from settings.json first
        if self.settings_file.exists():
            try:
                settings_data = json.loads(self.settings_file.read_text(encoding="utf-8"))
                self.sandbox_token = settings_data.get("sandbox_token")
                self.production_token = settings_data.get("production_token")
                logger.info("Loaded tokens from settings.json")
            except Exception as e:
                logger.warning("Failed to load tokens from settings.json: %s", e)
        
        # If no token was loaded from settings.json, try the conf file
        if not self.sandbox_token:
            if conf_path is None:
                # The conf file is expected to be located two levels above: project_root/conf
                conf_path = Path(__file__).resolve().parent.parent / "conf"
            self._conf_path = Path(conf_path)
            if not self._conf_path.exists():
                raise FileNotFoundError(
                    f"Configuration file '{self._conf_path}' not found. "
                    "Create it and put your Tinkoff tokens there, or configure tokens in the Settings tab."
                )
            self._parse_file()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _parse_file(self) -> None:
        for line in self._conf_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            token, *label_parts = parts
            label = " ".join(label_parts).lower() if label_parts else ""
            if "песочница" in label or "sandbox" in label:
                self.sandbox_token = token
            elif "прод" in label or "prod" in label:
                self.production_token = token

        if self.sandbox_token is None:
            raise ValueError(
                "Sandbox token not found in conf file or settings.json. "
                "Configure your token in the Settings tab or add a line with your sandbox token followed by the word 'песочница' in the conf file."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def token(self) -> str:
        """Return the sandbox token (for this MVP we always work in sandbox)."""
        return self.sandbox_token  # type: ignore[return-value]


# Initialize global settings instance
settings = Settings() 