#!/usr/bin/env python3
"""
ACFR Krow preset defaults — Lane F preset for checks_bridge resolution.

Env `KROW_CHECKS_SS_MAP` JSON overrides these defaults (env wins).
"""
from __future__ import annotations

import os
import pathlib

_ACFR_PRESET_SS = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def data_root() -> pathlib.Path:
    """Krow data root (client working dirs, external checks toolkit).

    KROW_DATA_DIR overrides; the default is the XDG data home
    (``$XDG_DATA_HOME/krow`` or ``~/.local/share/krow``).
    """
    raw = os.environ.get("KROW_DATA_DIR")
    if raw:
        return pathlib.Path(raw).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = pathlib.Path(xdg).expanduser() if xdg else pathlib.Path.home() / ".local" / "share"
    return base / "krow"


def acfr_preset_ss_id() -> str:
    return _ACFR_PRESET_SS


def acfr_preset_working_dir() -> str:
    """Client working dir for run_checks (projects.json + wk.py)."""
    return str((data_root() / "clients" / "riverton").expanduser().resolve())


def default_ss_map() -> dict[str, str]:
    """Built-in spreadsheetId → workingDir map when env is unset."""
    return {_ACFR_PRESET_SS: acfr_preset_working_dir()}
