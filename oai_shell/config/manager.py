import yaml
from pathlib import Path
from .models import ShellConfig

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: ShellConfig = self.load()

    def load(self) -> ShellConfig:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            return ShellConfig(**data)
