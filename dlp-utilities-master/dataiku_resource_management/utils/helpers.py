import json
from core.logger import log, LogLevel, Step

def format_nested_structure(data, **kwargs):
    """Applique format() à toutes les chaînes dans une structure imbriquée"""
    if isinstance(data, dict):
        return {k: format_nested_structure(v, **kwargs) for k, v in data.items()}
    elif isinstance(data, list):
        return [format_nested_structure(item, **kwargs) for item in data]
    elif isinstance(data, str):
        return data.format(**kwargs)
    else:
        return data

def load_config(config_path):
    log(LogLevel.INFO, Step.CONFIG, f"Début du chargement de la configuration: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        log(LogLevel.INFO, Step.CONFIG, f"Fin du chargement de la configuration: {config_path}")
        return config
    except FileNotFoundError:
        log(LogLevel.ERROR, Step.CONFIG, f"Fichier de configuration introuvable: {config_path}")
        return None
    except json.JSONDecodeError:
        log(LogLevel.ERROR, Step.CONFIG, f"Fichier de configuration invalide: {config_path}")
        return None