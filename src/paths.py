"""Where the tool keeps its files.

From source, data lives in the project folder (archive/, data/, charts/). The
packaged app uses the user's application-data folder instead, so updates never
touch the archive.

OPTIONSCONE_HOME overrides both.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def home() -> Path:
    env = os.environ.get("OPTIONSCONE_HOME")
    if env:
        p = Path(env)
    elif getattr(sys, "frozen", False):
        from platformdirs import user_data_dir
        p = Path(user_data_dir("OptionsCone", appauthor=False))
    else:
        p = PROJECT
    p.mkdir(parents=True, exist_ok=True)
    return p


def sub(name: str) -> Path:
    d = home() / name
    d.mkdir(parents=True, exist_ok=True)
    return d
