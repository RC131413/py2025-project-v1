import yaml
import os
from typing import Dict, Any

def load_config(config_path: str) -> dict:
    """Wczytuje konfigurację sieciową z pliku YAML."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            print("[DEBUG] Wczytana konfiguracja:", config)  # Dodaj tę linię
            return config.get("network", {})
    except FileNotFoundError:
        raise RuntimeError(f"Brak pliku konfiguracyjnego: {config_path}")
