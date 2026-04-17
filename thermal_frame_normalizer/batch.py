from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from .processing_core import process_frame

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class BatchRunSummary:
    total_files: int
    processed_files: int
    failed_files: int
    output_dir: Path
    errors: tuple[str, ...]


def iter_image_paths(folder: str | Path) -> list[Path]:
    root = Path(folder)
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )


def run_batch_processing(
    input_dir: str | Path,
    output_dir: str | Path,
    background_method_key: str,
    correction_method_key: str,
    background_params: dict[str, Any],
    correction_params: dict[str, Any],
    output_params: dict[str, Any],
    suffix: str = "_corrected",
) -> BatchRunSummary:
    input_root = Path(input_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    image_paths = iter_image_paths(input_root)
    errors: list[str] = []
    processed = 0

    for image_path in image_paths:
        frame = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if frame is None:
            errors.append(f"{image_path.name}: OpenCV could not read the file")
            continue

        try:
            result = process_frame(
                frame=frame,
                background_method_key=background_method_key,
                correction_method_key=correction_method_key,
                background_params=background_params,
                correction_params=correction_params,
                output_params=output_params,
            )
        except Exception as exc:
            errors.append(f"{image_path.name}: processing failed: {exc}")
            continue

        target_path = output_root / f"{image_path.stem}{suffix}.png"
        ok = cv2.imwrite(str(target_path), result.corrected)
        if not ok:
            errors.append(f"{image_path.name}: OpenCV could not write output")
            continue

        processed += 1

    return BatchRunSummary(
        total_files=len(image_paths),
        processed_files=processed,
        failed_files=len(errors),
        output_dir=output_root,
        errors=tuple(errors),
    )
