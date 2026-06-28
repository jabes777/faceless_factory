"""Shared utilities: config/env loading, IO, logging, mode detection."""
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def log(stage, msg):
    print(f"[{time.strftime('%H:%M:%S')}] {stage:<10} | {msg}")


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_env():
    """Minimal .env loader (no python-dotenv dependency)."""
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    return os.environ


def has_key(name):
    v = os.environ.get(name, "").strip()
    return bool(v) and not v.startswith("REPLACE")


def mode():
    """'live' if any generative key is present, else 'dry-run'."""
    load_env()
    if has_key("ANTHROPIC_API_KEY") or has_key("OPENAI_API_KEY"):
        return "live"
    return "dry-run"


def slugify(text, maxlen=60):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text[:maxlen].strip("-") or "video"


def out_dir(slug):
    d = ROOT / "output" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path, text):
    Path(path).write_text(text, encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
