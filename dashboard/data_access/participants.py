from __future__ import annotations

from pathlib import Path
from typing import Iterable


def list_participants(data_base_path: str | Path) -> list[str]:
    """Return sorted participant folder names from the base path."""
    base_path = Path(data_base_path)
    if not base_path.exists() or not base_path.is_dir():
        return []
    return sorted([item.name for item in base_path.iterdir() if item.is_dir()])


def participant_path(data_base_path: str | Path, participant_id: str) -> Path:
    """Build participant folder path from base path and participant identifier."""
    return Path(data_base_path) / participant_id


def iter_aggregated_dirs(participant_dir: str | Path) -> Iterable[Path]:
    """Yield directories likely containing aggregated per-minute CSV files."""
    participant_path_obj = Path(participant_dir)
    if not participant_path_obj.exists():
        return

    for candidate in participant_path_obj.rglob("*"):
        if not candidate.is_dir():
            continue
        lower_name = candidate.name.lower()
        if "aggr" in lower_name or "aggregated" in lower_name:
            yield candidate
