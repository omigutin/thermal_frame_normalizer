from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_preset_payload(
    background_method: str,
    correction_method: str,
    background_params: dict[str, Any],
    correction_params: dict[str, Any],
    output_params: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": 1,
        "background_method": background_method,
        "correction_method": correction_method,
        "background_params": background_params,
        "correction_params": correction_params,
        "output_params": output_params,
    }


def save_preset(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_preset(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8"))
