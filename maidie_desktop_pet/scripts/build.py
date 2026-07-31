"""Maidie Windows 统一构建与发布入口。"""

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 10)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = PROJECT_ROOT / "version.json"
SPEC_FILE = PROJECT_ROOT / "maidie.spec"
INSTALLER_FILE = PROJECT_ROOT / "installer" / "MaidieSetup.iss"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "release"


class BuildError(RuntimeError):
    """可直接展示给构建用户的明确错误。"""


def print_step(message):
    print("[STEP] {0}".format(message), flush=True)


def print_error(message):
    print("[ERROR] {0}".format(message), file=sys.stderr, flush=True)


def check_environment():
    """在导入项目模块前检查构建解释器。"""

    print_step("Checking Python environment")
    if sys.version_info < MIN_PYTHON:
        raise BuildError("Python version too low (Python 3.10 or newer is required)")
    if os.name != "nt":
        raise BuildError("Windows build is only supported on Windows")
    if struct.calcsize("P") * 8 != 64:
        raise BuildError("64-bit Python is required for the win64 release")
    print("Python: {0}".format(sys.executable))
    print("Version: {0}".format(sys.version.splitlines()[0]))


def load_version(channel):
    """读取唯一版本源，并复用 core.version 的校验规则。"""

    print_step("Reading and validating version.json")
    if not VERSION_FILE.is_file():
        raise BuildError("version.json not found")
    try:
        payload = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError("Invalid version.json: {0}".format(exc)) from exc

    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from core.version import load_version_info

        version_info = load_version_info(VERSION_FILE)
    except (ImportError, RuntimeError, ValueError) as exc:
        raise BuildError("Invalid version.json: {0}".format(exc)) from exc
    finally:
        if sys.path and sys.path[0] == str(PROJECT_ROOT):
            sys.path.pop(0)

    # 命令行渠道写回唯一版本源，确保 EXE、发布目录和安装器完全一致。
    print_step("Setting release channel to {0}".format(channel))
    if payload.get("channel") != channel:
        payload["channel"] = channel
        temporary = VERSION_FILE.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(VERSION_FILE)

    return {
        "name": version_info.name,
        "version": version_info.version,
        "channel": channel,
        "build": version_info.build,
        "release_date": version_info.release_date,
    }


def check_required_files():
    """在删除旧产物前确认构建配置完整。"""

    required = (
        SPEC_FILE,
        INSTALLER_FILE,
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "requirements-build.txt",
        PROJECT_ROOT / "packaging" / "config.json",
        PROJECT_ROOT / "packaging" / "maidie.ico",
    )
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.is_file()]
    if missing:
        raise BuildError("Required build files missing: {0}".format(", ".join(missing)))


def ensure_dependencies():
    """沿用旧构建入口的依赖安装行为，但统一由当前解释器执行。"""

    print_step("Checking and installing build dependencies")
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(PROJECT_ROOT / "requirements.txt"),
        "-r",
        str(PROJECT_ROOT / "requirements-build.txt"),
    ]
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("Dependency installation failed") from exc


def remove_generated_directory(path):
    """仅允许删除项目根目录下明确命名的构建产物。"""

    resolved = path.resolve()
    if resolved.parent != PROJECT_ROOT or resolved.name not in {"build", "dist"}:
        raise BuildError("Refusing to clean unsafe path: {0}".format(resolved))
    if resolved.exists():
        shutil.rmtree(resolved)


def clean_old_outputs():
    print_step("Cleaning old build and dist directories")
    try:
        remove_generated_directory(BUILD_DIR)
        remove_generated_directory(DIST_DIR)
    except OSError as exc:
        raise BuildError("Unable to clean old build output: {0}".format(exc)) from exc


def run_pyinstaller():
    print_step("Building Maidie with PyInstaller")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("PyInstaller build failed") from exc

    executable = DIST_DIR / "Maidie" / "Maidie.exe"
    if not executable.is_file():
        raise BuildError("PyInstaller build failed: Maidie.exe was not generated")


def release_bundle_path(version):
    name = "Maidie-v{0}-{1}-win64".format(version["version"], version["channel"])
    return RELEASE_DIR / name


def installer_output_path(version):
    name = "Maidie_Setup_v{0}_{1}.exe".format(
        version["version"], version["channel"]
    )
    return RELEASE_DIR / name


def write_release_readme(target, version):
    """生成适合最终用户直接阅读的发布说明。"""

    content = (
        "Maidie v{version} {channel} (Build {build})\n"
        "Release date: {release_date}\n\n"
        "启动方式：运行 Maidie.exe。\n"
        "请保留此目录内全部 DLL、assets、docs 和其他依赖文件。\n"
        "用户配置、日志和数据库保存在 %APPDATA%\\Maidie，升级不会覆盖。\n"
    ).format(**version)
    (target / "README.txt").write_text(content, encoding="utf-8")


def assemble_release(version):
    print_step("Creating standard release directory")
    source = DIST_DIR / "Maidie"
    target = release_bundle_path(version)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    try:
        shutil.copytree(source, target)
        shutil.copy2(VERSION_FILE, target / "version.json")
        write_release_readme(target, version)
    except OSError as exc:
        raise BuildError("Failed to create release directory: {0}".format(exc)) from exc

    required = (
        target / "Maidie.exe",
        target / "assets",
        target / "docs",
        target / "README.txt",
        target / "version.json",
    )
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise BuildError("Release directory is incomplete: {0}".format(", ".join(missing)))
    return target


def find_inno_setup():
    print_step("Locating Inno Setup compiler")
    configured = str(os.environ.get("INNO_SETUP_COMPILER") or "").strip()
    candidates = [
        Path(configured) if configured else None,
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    discovered = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if discovered:
        return Path(discovered)
    raise BuildError("Inno Setup compiler not found")


def build_installer(version, bundle_path):
    print_step("Building Inno Setup installer")
    compiler = find_inno_setup()
    output = installer_output_path(version)
    output.unlink(missing_ok=True)
    output_base = output.stem
    command = [
        str(compiler),
        "/DMyAppVersion={0}".format(version["version"]),
        "/DMyAppChannel={0}".format(version["channel"]),
        "/DMyAppBuild={0}".format(version["build"]),
        "/DMyAppSourceDir={0}".format(bundle_path),
        "/DMyOutputDir={0}".format(RELEASE_DIR),
        "/DMyOutputBaseFilename={0}".format(output_base),
        str(INSTALLER_FILE),
    ]
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("Inno Setup build failed") from exc
    if not output.is_file():
        raise BuildError("Inno Setup build failed: installer was not generated")
    return output


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Build a Maidie Windows release")
    parser.add_argument("channel", choices=("beta", "stable"))
    return parser.parse_args(argv)


def build(channel):
    check_environment()
    version = load_version(channel)
    check_required_files()
    ensure_dependencies()
    clean_old_outputs()
    run_pyinstaller()
    bundle = assemble_release(version)
    installer = build_installer(version, bundle)
    print_step("Build completed")
    print("Release directory: {0}".format(bundle))
    print("Installer: {0}".format(installer))
    return bundle, installer


def main(argv=None):
    try:
        arguments = parse_arguments(argv)
        build(arguments.channel)
    except BuildError as exc:
        print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        print_error("Build cancelled")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
