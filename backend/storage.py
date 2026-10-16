"""Private file storage. Files are saved under random keys, never served statically."""
import os
import uuid
from pathlib import Path

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))


def save_file(data: bytes, ext: str) -> str:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4().hex}{ext}"
    (STORAGE_DIR / key).write_bytes(data)
    return key


def read_file(key: str) -> bytes:
    path = (STORAGE_DIR / key).resolve()
    if STORAGE_DIR.resolve() not in path.parents:
        raise ValueError("Invalid storage key")
    return path.read_bytes()


def delete_file(key: str) -> None:
    path = (STORAGE_DIR / key).resolve()
    if STORAGE_DIR.resolve() in path.parents and path.exists():
        path.unlink()
