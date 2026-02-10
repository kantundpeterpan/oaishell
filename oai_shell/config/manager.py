from typing import Optional
import yaml
from pathlib import Path
from .models import ShellConfig

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config: ShellConfig = self.load()

    def load(self) -> ShellConfig:
        if not self.config_path or not self.config_path.exists():
            return ShellConfig()
        
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            return ShellConfig(**data)
