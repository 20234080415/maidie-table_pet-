# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH)
sys.path.insert(0, str(project_root))

from core.version import VERSION_INFO


# Windows 文件版本需要四段数字；前三段来自 SemVer，最后一段使用 build。
windows_version = (*VERSION_INFO.semver_parts, VERSION_INFO.build)
if any(part > 65535 for part in windows_version):
    raise ValueError("version.json 的版本数字必须在 Windows 版本范围 0-65535 内")

file_version = ".".join(str(part) for part in windows_version)
version_info_path = project_root / "build" / "maidie-version-info.txt"
version_info_path.parent.mkdir(parents=True, exist_ok=True)
version_info_path.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={windows_version!r},
    prodvers={windows_version!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', {VERSION_INFO.name!r}),
          StringStruct('FileDescription', 'Maidie Desktop Pet'),
          StringStruct('FileVersion', {file_version!r}),
          StringStruct('InternalName', 'Maidie'),
          StringStruct('OriginalFilename', 'Maidie.exe'),
          StringStruct('ProductName', {VERSION_INFO.name!r}),
          StringStruct('ProductVersion', {VERSION_INFO.full_version!r})
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)""",
    encoding="utf-8",
)

# Whole directories are collected so new sprites, actions, and documentation are
# packaged automatically. Keep secrets out of packaging/config.json.
datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "docs"), "docs"),
    (str(project_root / "README.md"), "."),
    (str(project_root / "version.json"), "."),
    (str(project_root / "packaging" / "config.json"), "config"),
]

hiddenimports = collect_submodules("core.plugins")

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Maidie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory=".",
    icon=str(project_root / "packaging" / "maidie.ico"),
    version=str(version_info_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Maidie",
)
