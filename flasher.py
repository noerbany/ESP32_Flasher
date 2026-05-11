from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from typing import Callable, Iterable

from validator import FirmwareImage

LogCallback = Callable[[str], None]

@dataclass(frozen=True)
class FlashSettings:
    port: str
    baudrate: str

class FlashError(RuntimeError):
    pass

class ESPFlasher:
    def erase(self, settings: FlashSettings, log: LogCallback) -> None:
        self._run_esptool(
            ["--chip", "esp32", "--port", settings.port, "erase_flash"],
            log,
        )

    def write(
        self,
        settings: FlashSettings,
        images: Iterable[FirmwareImage],
        log: LogCallback,
    ) -> None:
        args = [
            "--chip",
            "esp32",
            "--port",
            settings.port,
            "--baud",
            settings.baudrate,
            "write_flash",
        ]

        for image in images:
            args.extend([image.address, str(image.path)])

        self._run_esptool(args, log)

    def verify(
        self,
        settings: FlashSettings,
        images: Iterable[FirmwareImage],
        log: LogCallback,
    ) -> None:
        args = [
            "--chip",
            "esp32",
            "--port",
            settings.port,
            "--baud",
            settings.baudrate,
            "verify_flash",
        ]

        for image in images:
            args.extend([image.address, str(image.path)])

        self._run_esptool(args, log)

    def _run_esptool(self, args: list[str], log: LogCallback) -> None:
        try:
            import esptool
        except ImportError as exc:
            raise FlashError("esptool is required for flashing.") from exc

        output = io.StringIO()

        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                esptool.main(args)
        except SystemExit as exc:
            self._flush_output(output.getvalue(), log)
            code = exc.code if isinstance(exc.code, int) else 1
            if code != 0:
                raise FlashError(f"esptool failed with exit code {code}.") from exc
        except Exception as exc:
            self._flush_output(output.getvalue(), log)
            raise FlashError(_friendly_error_message(exc)) from exc

        ##self._flush_output(output.getvalue(), log)

    def _flush_output(self, text: str, log: LogCallback) -> None:
        for line in text.splitlines():
            if line.strip():
                log(line)

def _friendly_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    lower_message = message.lower()

    if "permission" in lower_message or "access is denied" in lower_message:
        return "Permission denied while opening the COM port. Close other serial tools and try again."
    if "timeout" in lower_message:
        return "Flash operation timed out. Check the USB cable, boot mode, and selected COM port."
    if "failed to connect" in lower_message or "no serial data" in lower_message:
        return "Device not detected. Check COM port selection and ESP32 boot mode."

    return message
