# main.spec
# python -m PyInstaller --clean --noconfirm main.spec  

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("esptool")

datas = collect_data_files("esptool")
datas = collect_data_files("esptool") + [
    ("assets/logo.ico", "assets"),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports + [
        "serial",
        "serial.tools.list_ports",
        "serial.urlhandler",
        "reedsolo",
        "intelhex",
        "cryptography",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RavelEdge Flasher Tools",
    icon="assets/logo.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)