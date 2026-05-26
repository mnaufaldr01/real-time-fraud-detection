"""Rebuild dbt analytics marts and clear Streamlit caches."""

from __future__ import annotations

import subprocess
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT = ROOT / "dbt_fraud"


def _dbt_command() -> list[str]:
    for rel in (".venv/Scripts/dbt.exe", ".venv/bin/dbt"):
        exe = ROOT / rel
        if exe.exists():
            return [str(exe), "run", "--profiles-dir", "."]
    return ["dbt", "run", "--profiles-dir", "."]


def rebuild_marts() -> tuple[bool, str]:
    """Run `dbt run` in dbt_fraud. Returns (success, combined stdout/stderr)."""
    if not DBT_PROJECT.is_dir():
        return False, f"dbt project not found: {DBT_PROJECT}"

    try:
        proc = subprocess.run(
            _dbt_command(),
            cwd=DBT_PROJECT,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except FileNotFoundError:
        return (
            False,
            "dbt executable not found. Install with: pip install -r requirements-dbt.txt",
        )
    except subprocess.TimeoutExpired:
        return False, "dbt run timed out after 10 minutes."

    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output


def clear_caches() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()


def reload_charts() -> None:
    """Re-read analytics marts from Postgres without running dbt."""
    clear_caches()
