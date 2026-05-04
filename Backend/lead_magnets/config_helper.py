import json
import logging
from .models import SystemConfiguration

logger = logging.getLogger(__name__)

def get_config(key: str, default=None):
    """Retrieves a configuration value from SystemConfiguration model."""
    try:
        config = SystemConfiguration.objects.filter(key=key).first()
        if not config:
            return default
            
        if config.config_type == 'json':
            try:
                return json.loads(config.value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON config for key: {key}")
                return default
        return config.value
    except Exception as e:
        logger.error(f"Error retrieving config '{key}': {e}")
        return default

def get_config_all(prefix: str):
    """Retrieves all config values starting with a prefix."""
    try:
        configs = SystemConfiguration.objects.filter(key__startswith=prefix)
        result = {}
        for config in configs:
            key = config.key[len(prefix):] # Strip prefix
            if config.config_type == 'json':
                try:
                    result[key] = json.loads(config.value)
                except json.JSONDecodeError:
                    result[key] = config.value
            else:
                result[key] = config.value
        return result
    except Exception as e:
        logger.error(f"Error retrieving configs for prefix '{prefix}': {e}")
        return {}
