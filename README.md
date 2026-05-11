# ESP32_Flasher

Custom ESP32 Flasher Tools - A GUI application for flashing firmware to ESP32 devices.

## Description

This tool provides a user-friendly graphical interface for flashing ESP32 firmware. It supports extracting firmware from password-protected ZIP archives, validating the firmware files, and performing erase, write, and verify operations using esptool.

The application extracts and validates the following firmware components:
- bootloader.bin (at 0x1000)
- partition-table.bin (at 0x8000)
- ota_data_initial.bin (at 0xF000)
- firmware.bin (at 0x20000)

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - esptool==4.7.0
   - pyserial

2. **Configure Firmware Archive Password**:
   Edit `extractor.py` and set the `FIRMWARE_ZIP_PASSWORD` variable to your firmware archive password.

3. **Run the Application**:
   ```bash
   python main.py
   ```

## How It Works

1. **Select Firmware Archive**: Click "Browse Firmware" to select a ZIP archive containing the ESP32 firmware files.

2. **Extraction and Validation**: The tool extracts the ZIP archive (using the configured password) and validates that all required firmware files are present.

3. **Configure Settings**:
   - Select the COM port where your ESP32 is connected.
   - Choose the baudrate (default: 921600).
   - Refresh ports if needed.

4. **Flash Operations**:
   - **Erase**: Erases the flash memory of the ESP32.
   - **Write**: Writes the firmware images to the ESP32 at their specified addresses.
   - **Verify**: Verifies that the written firmware matches the source files.

The application provides real-time logging of operations and progress updates through the GUI.
