from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class FirmwareImage:
    logical_name: str
    path: Path
    address: str

@dataclass(frozen=True)
class FirmwareValidationResult:
    images: tuple[FirmwareImage, ...]
    missing_files: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.missing_files

FIRMWARE_LAYOUT: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("bootloader.bin", "0x1000", ("bootloader.bin",)),
    ("partition-table.bin", "0x8000", ("partition-table.bin",)),
    (
        "ota_datainitial.bin",
        "0xF000",
        ("ota_datainitial.bin", "ota_data_initial.bin"),
    ),
    ("firmware.bin", "0x20000", ("firmware.bin",)),
)

def validate_firmware_directory(directory: Path) -> FirmwareValidationResult:
    images: list[FirmwareImage] = []
    missing_files: list[str] = []

    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Firmware directory not found: {directory}")

    for logical_name, address, aliases in FIRMWARE_LAYOUT:
        image_path = _find_file(directory, aliases)
        if image_path is None:
            missing_files.append(logical_name)
            continue

        images.append(
            FirmwareImage(
                logical_name=logical_name,
                path=image_path,
                address=address,
            )
        )

    return FirmwareValidationResult(
        images=tuple(images),
        missing_files=tuple(missing_files),
    )

def _find_file(directory: Path, names: tuple[str, ...]) -> Path | None:
    direct_children = {
        child.name.lower(): child
        for child in directory.iterdir()
        if child.is_file()
    }

    for name in names:
        match = direct_children.get(name.lower())
        if match is not None:
            return match

    for child in directory.rglob("*"):
        if child.is_file() and child.name.lower() in {name.lower() for name in names}:
            return child

    return None
