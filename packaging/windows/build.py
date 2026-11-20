"""Build the Windows x64 installer in a clean Python environment."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.config import Config


def build():
    compiler = shutil.which("ISCC")
    if compiler is None:
        for directory in (Path(os.environ["LOCALAPPDATA"]) / "Programs",
                          Path(os.environ["ProgramFiles(x86)"])):
            candidate = directory / "Inno Setup 6" / "ISCC.exe"
            if candidate.is_file():
                compiler = str(candidate)
                break
    if compiler is None:
        raise SystemExit("Install Inno Setup 6 or add ISCC.exe to PATH.")
    build_dir = ROOT / "build" / "windows"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--noupx",
        "--onedir", "--windowed", "--name", "MULTI1Dvisual",
        "--specpath", str(build_dir), "--workpath", str(build_dir / "work"),
        "--distpath", str(build_dir / "bundle"),
        "--icon", str(ROOT / "resources/icons/multi1dvisual.ico"),
        "--add-data", f"{ROOT / 'resources/icons/multi1dvisual.png'}:resources/icons",
        # The recorder reads both parser sources when writing a standalone replay.
        "--add-data", f"{ROOT / 'legacy/scanFile.py'}:legacy",
        "--add-data", f"{ROOT / 'core/fort10_parser.py'}:core",
        "--paths", str(ROOT / "legacy"), "--hidden-import", "scanFile",
        str(ROOT / "main.py"),
    ], cwd=ROOT, check=True)
    subprocess.run([compiler, f"/DAppVersion={Config.APP_VERSION}",
                    str(ROOT / "packaging/windows/installer.iss")], check=True)


if __name__ == "__main__":
    build()
