import os
from functools import lru_cache
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


@lru_cache(maxsize=1)
def load_local_env_files() -> None:
    if os.getenv("SOLO_LOAD_ENV_FILES") != "1":
        return

    api_root = Path(__file__).resolve().parents[2]
    repo_root = api_root.parents[1]
    for env_file in (repo_root / ".env.local", repo_root / ".env", api_root / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)


def get_env(name: str, default: str | None = None) -> str | None:
    load_local_env_files()
    return os.getenv(name, default)
