"""Where the database and the original files are: from the environment, otherwise from .env.

Never hard-coded, as for the model's address (extraction.client.load_settings).
"""

from __future__ import annotations

import os
from pathlib import Path

from extraction.client import DEFAULT_ENV_FILE, read_env_file

DATABASE_URL_SETTING = "DATABASE_URL"
TEST_DATABASE_URL_SETTING = "TEST_DATABASE_URL"
ORIGINALS_DIR_SETTING = "ORIGINALS_DIR"


class StorageConfigError(Exception):
    """A storage setting is missing."""


def _setting(name: str, env_file: Path | str) -> str | None:
    return os.environ.get(name) or read_env_file(Path(env_file)).get(name) or None


def _required(name: str, env_file: Path | str) -> str:
    value = _setting(name, env_file)
    if not value:
        raise StorageConfigError(f"{name} isn't set. Add it to .env (see .env.example).")
    return value


def load_database_url(env_file: Path | str = DEFAULT_ENV_FILE) -> str:
    return _required(DATABASE_URL_SETTING, env_file)


def load_test_database_url(env_file: Path | str = DEFAULT_ENV_FILE) -> str | None:
    """The database the tests may wipe. None skips the database tests."""
    return _setting(TEST_DATABASE_URL_SETTING, env_file)


def load_originals_dir(env_file: Path | str = DEFAULT_ENV_FILE) -> Path:
    return Path(_required(ORIGINALS_DIR_SETTING, env_file)).expanduser()
