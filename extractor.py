from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

FIRMWARE_ZIP_PASSWORD = "YOUR_ZIP_PASSWORD_HERE"

@dataclass(frozen=True)
class FirmwareExtraction:
    archive_path: Path
    extract_dir: Path

def extract_firmware_archive(archive_path: Path) -> FirmwareExtraction:
    if archive_path.suffix.lower() != ".zip":
        raise ValueError("Only .zip firmware archives are supported.")

    if not archive_path.exists() or not archive_path.is_file():
        raise FileNotFoundError(f"Firmware archive not found: {archive_path}")

    extract_dir = Path(tempfile.mkdtemp(prefix="espflasher_"))
    password = FIRMWARE_ZIP_PASSWORD.encode("utf-8")

    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_dir, pwd=password)
    except Exception:
        cleanup_extraction(extract_dir)
        raise

    return FirmwareExtraction(archive_path=archive_path, extract_dir=extract_dir)

def cleanup_extraction(extract_dir: Path | None) -> None:
    if extract_dir is None:
        return

    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
