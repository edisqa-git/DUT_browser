from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "dut-dashboard" / "backend"
ENTRYPOINT = BACKEND_DIR / "run_backend.py"
BUILD_DIR = ROOT_DIR / ".build" / "pyinstaller"
DIST_DIR = BUILD_DIR / "dist"
WORK_DIR = BUILD_DIR / "work"
SPEC_DIR = BUILD_DIR / "spec"
RUNTIME_DIR = ROOT_DIR / "desktop" / "resources" / "runtime"
RUNTIME_BACKEND_DIR = RUNTIME_DIR / "backend"


def main() -> int:
    executable_name = "dut-backend.exe" if sys.platform.startswith("win") else "dut-backend"

    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(RUNTIME_BACKEND_DIR, ignore_errors=True)
    RUNTIME_BACKEND_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "dut-backend",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--paths",
        str(BACKEND_DIR),
        str(ENTRYPOINT),
    ]

    subprocess.run(command, check=True, cwd=ROOT_DIR)

    built_executable = DIST_DIR / executable_name
    if not built_executable.exists():
        raise FileNotFoundError(f"Expected backend executable was not produced: {built_executable}")

    shutil.copy2(built_executable, RUNTIME_BACKEND_DIR / executable_name)
    shutil.copy2(ROOT_DIR / "VERSION", RUNTIME_DIR / "VERSION")
    shutil.copy2(ROOT_DIR / "release.json", RUNTIME_DIR / "release.json")
    shutil.copytree(ROOT_DIR / "dut-dashboard" / "tools", RUNTIME_DIR / "dut-dashboard" / "tools", dirs_exist_ok=True)

    print(f"Backend runtime prepared at {RUNTIME_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
