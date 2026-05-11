from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from extractor import FirmwareExtraction, cleanup_extraction, extract_firmware_archive
from flasher import ESPFlasher, FlashError, FlashSettings
from serial_manager import list_serial_ports
from validator import FirmwareImage, validate_firmware_directory

APP_TITLE = "RavelEdge Flasher Tools v1.0.0"
BAUDRATES = ("115200", "230400", "460800", "921600")

class ESPFlasherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("480x240")
        self.root.minsize(480, 240)

        self.root.iconbitmap(self._resource_path("assets/logo.ico"))

        self.archive_path = tk.StringVar()
        self.selected_port = tk.StringVar()
        self.selected_baudrate = tk.StringVar(value="921600")
        self.status_text = tk.StringVar(value="Select a firmware archive to begin.")

        self._extraction: FirmwareExtraction | None = None
        self._images: tuple[FirmwareImage, ...] = ()
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._flasher = ESPFlasher()

        self._build_layout()
        self.refresh_ports()
        self._set_busy(False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)

    def _resource_path(self, relative_path: str) -> str:
        import os
        import sys

        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def run(self) -> None:
        self.root.mainloop()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        top = ttk.Frame(self.root, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Button(top, text="Browse Firmware", command=self._browse_archive).grid(
            row=0,
            column=0,
            padx=(0, 8),
            sticky="w",
        )
        ttk.Entry(top, textvariable=self.archive_path, state="readonly").grid(
            row=0,
            column=1,
            sticky="ew",
        )

        settings = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        settings.grid(row=1, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="COM Port").grid(row=0, column=0, sticky="w")
        self.port_combo = ttk.Combobox(
            settings,
            textvariable=self.selected_port,
            state="readonly",
            width=18,
        )
        self.port_combo.grid(row=0, column=1, padx=8, sticky="w")
        ttk.Button(settings, text="Refresh", command=self.refresh_ports).grid(
            row=0,
            column=2,
            padx=(0, 24),
            sticky="w",
        )

        ttk.Label(settings, text="Baudrate").grid(row=0, column=3, sticky="w")
        ttk.Combobox(
            settings,
            textvariable=self.selected_baudrate,
            values=BAUDRATES,
            state="readonly",
            width=12,
        ).grid(row=0, column=4, padx=8, sticky="w")

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.grid(row=2, column=0, sticky="ew")

        self.erase_button = ttk.Button(actions, text="Erase", command=self._erase)
        self.erase_button.grid(row=0, column=0, padx=(0, 8))

        self.write_button = ttk.Button(actions, text="Write", command=self._write)
        self.write_button.grid(row=0, column=1, padx=(0, 8))

        self.verify_button = ttk.Button(actions, text="Verify", command=self._verify)
        self.verify_button.grid(row=0, column=2, padx=(0, 8))

        self.progress = ttk.Progressbar(actions, mode="indeterminate")
        self.progress.grid(row=0, column=3, padx=(12, 0), sticky="ew")
        actions.columnconfigure(3, weight=1)

        log_frame = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        footer.grid(row=4, column=0, sticky="ew")
        ttk.Label(footer, textvariable=self.status_text).grid(row=0, column=0, sticky="w")

    def refresh_ports(self) -> None:
        try:
            ports = list_serial_ports()
        except RuntimeError as exc:
            self._append_log(str(exc))
            ports = []

        self.port_combo.configure(values=ports)
        if ports and self.selected_port.get() not in ports:
            self.selected_port.set(ports[0])
        elif not ports:
            self.selected_port.set("")

    def _browse_archive(self) -> None:
        path = filedialog.askopenfilename(
            title="Select firmware archive",
            filetypes=(("ZIP archives", "*.zip"),),
        )
        if not path:
            return

        self.archive_path.set(path)
        self._load_archive(Path(path))

    def _load_archive(self, archive_path: Path) -> None:
        cleanup_extraction(self._extraction.extract_dir if self._extraction else None)
        self._extraction = None
        self._images = ()
        self._update_action_state()

        try:
            extraction = extract_firmware_archive(archive_path)
            result = validate_firmware_directory(extraction.extract_dir)
        except Exception as exc:
            self.status_text.set("Firmware archive failed validation.")
            self._append_log(f"Firmware load failed: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self._extraction = extraction
        self._images = result.images if result.is_valid else ()

        if result.is_valid:
            self.status_text.set("Firmware archive ready.")
            self._append_log(f"Loaded firmware archive: {archive_path}")
            ##for image in result.images:
            ##    self._append_log(f"{image.address} -> {image.path.name}")
            self._append_log(f"Firmware Loaded!")
        else:
            missing = ", ".join(result.missing_files)
            self.status_text.set("Firmware archive is missing required files.")
            self._append_log(f"Missing required firmware files: {missing}")
            cleanup_extraction(extraction.extract_dir)
            self._extraction = None
            messagebox.showerror(APP_TITLE, f"Missing required firmware files: {missing}")

        self._update_action_state()

    def _erase(self) -> None:
        self._run_flash_action(
            "Erase",
            lambda settings: self._flasher.erase(settings, self._queue_log),
            requires_firmware=False,
        )

    def _write(self) -> None:
        self._run_flash_action(
            "Write",
            lambda settings: self._flasher.write(settings, self._images, self._queue_log),
            requires_firmware=True,
        )

    def _verify(self) -> None:
        self._run_flash_action(
            "Verify",
            lambda settings: self._flasher.verify(settings, self._images, self._queue_log),
            requires_firmware=True,
        )

    def _run_flash_action(
        self,
        name: str,
        action: Callable[[FlashSettings], None],
        requires_firmware: bool,
    ) -> None:
        if requires_firmware and not self._images:
            messagebox.showerror(APP_TITLE, "Load a valid firmware archive first.")
            return

        if not self.selected_port.get():
            messagebox.showerror(APP_TITLE, "Select a COM port first.")
            return

        settings = FlashSettings(
            port=self.selected_port.get(),
            baudrate=self.selected_baudrate.get(),
        )

        def worker() -> None:
            self._queue_log(f"{name} started.")
            try:
                action(settings)
            except FlashError as exc:
                self._queue_log(f"{name} failed: {exc}")
                self.root.after(0, lambda: self.status_text.set(f"{name} failed."))
            except Exception as exc:
                self._queue_log(f"{name} failed: {exc}")
                self.root.after(0, lambda: self.status_text.set(f"{name} failed."))
            else:
                self._queue_log(f"{name} completed.")
                self.root.after(0, lambda: self.status_text.set(f"{name} completed."))
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        self._set_busy(True)
        self.status_text.set(f"{name} running...")
        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.erase_button.configure(state=state)
        self.write_button.configure(state=state if self._images else "disabled")
        self.verify_button.configure(state=state if self._images else "disabled")

        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()
            self._update_action_state()

    def _update_action_state(self) -> None:
        self.erase_button.configure(state="normal")
        firmware_state = "normal" if self._images else "disabled"
        self.write_button.configure(state=firmware_state)
        self.verify_button.configure(state=firmware_state)

    def _queue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)

        self.root.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_close(self) -> None:
        cleanup_extraction(self._extraction.extract_dir if self._extraction else None)
        self.root.destroy()
