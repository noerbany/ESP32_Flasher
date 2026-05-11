from __future__ import annotations

def list_serial_ports() -> list[str]:
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("pyserial is required for COM port detection.") from exc

    return [port.device for port in list_ports.comports()]
