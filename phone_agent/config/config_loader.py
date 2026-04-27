"""YAML configuration file loader for Phone Agent."""

import os
import sys
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = "config.yaml"
EXAMPLE_CONFIG_PATH = "config.yaml.example"


def _find_config_path() -> str | None:
    """
    Search for config.yaml in standard locations.

    Search order:
    1. Config file specified via PHONE_AGENT_CONFIG env var
    2. config.yaml in current working directory
    3. config.yaml next to the Phone Agent package (project root)

    Returns:
        Path to config file if found, None otherwise.
    """
    candidates = []

    env_path = os.getenv("PHONE_AGENT_CONFIG")
    if env_path and os.path.isfile(env_path):
        return env_path

    candidates.append(os.path.join(os.getcwd(), "config.yaml"))

    try:
        import phone_agent

        pkg_dir = os.path.dirname(os.path.dirname(phone_agent.__file__))
        candidates.append(os.path.join(pkg_dir, "config.yaml"))
    except Exception:
        pass

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def load_config() -> dict[str, Any]:
    """
    Load configuration from config.yaml.

    Searches for config.yaml in standard locations. If not found,
    returns empty dict (caller should apply defaults).

    Returns:
        Dictionary of configuration values. Empty dict if no config file found.
    """
    path = _find_config_path()

    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            return {}

        if not isinstance(config, dict):
            print(
                f"⚠ Warning: config file {path} has unexpected format, ignoring.",
                file=sys.stderr,
            )
            return {}

        return config

    except yaml.YAMLError as e:
        print(
            f"⚠ Warning: failed to parse config file {path}: {e}",
            file=sys.stderr,
        )
        return {}
    except OSError as e:
        print(
            f"⚠ Warning: could not read config file {path}: {e}",
            file=sys.stderr,
        )
        return {}
