"""Build the desktop DEB and RPM with Python, Pillow and nFPM."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
APP_ID = "io.github.boxu_pku.MULTI1Dvisual"
APP_DIR = "/usr/share/multi1dvisual"
sys.path.insert(0, str(ROOT))
from utils.config import Config


def package_file(source, destination, mode=0o644):
    return {"src": str(source), "dst": destination, "file_info": {"mode": mode}}


def build(staging):
    files = [package_file(ROOT / "main.py", f"{APP_DIR}/main.py")]
    for directory in ("core", "legacy", "ui", "utils"):
        for source in sorted((ROOT / directory).rglob("*.py")):
            relative = source.relative_to(ROOT).as_posix()
            files.append(package_file(source, f"{APP_DIR}/{relative}"))

    for name in ("README.md", "README_EN.md"):
        files.append(package_file(ROOT / name, f"/usr/share/doc/multi1dvisual/{name}"))
    # Minimal Debian installations can filter /usr/share/doc during unpacking.
    # The Help menu reads the application's own copy on every desktop.
    for name in ("manual_CN/multi1dvisual_manual_zh.pdf", "manual_EN/multi1dvisual_manual_en.pdf",
                 "examples/quickstart.zip"):
        files.append(package_file(ROOT / "docs" / name, f"{APP_DIR}/docs/{name}"))
    files.extend([
        {"type": "symlink", "src": "../../multi1dvisual/docs", "dst": "/usr/share/doc/multi1dvisual/docs",
         "file_info": {"mode": 0o777}},
        package_file(ROOT / "packaging/README.md", "/usr/share/doc/multi1dvisual/packaging/README.md"),
        package_file(HERE / "multi1dvisual", "/usr/bin/multi1dvisual", 0o755),
        package_file(HERE / f"{APP_ID}.desktop", f"/usr/share/applications/{APP_ID}.desktop"),
        package_file(HERE / f"{APP_ID}.metainfo.xml", f"/usr/share/metainfo/{APP_ID}.metainfo.xml"),
    ])

    icon = ROOT / "resources" / "icons" / "multi1dvisual.png"
    with Image.open(icon) as master:
        for size in (16, 24, 32, 48, 64, 128, 256, 512):
            path = staging / f"{size}.png"
            master.resize((size, size), Image.Resampling.LANCZOS).save(path)
            files.append(package_file(path, f"/usr/share/icons/hicolor/{size}x{size}/apps/{APP_ID}.png"))
    # The source launcher and the installed application use the same relative resource path.
    files.append({
        "type": "symlink",
        "src": f"../../../icons/hicolor/512x512/apps/{APP_ID}.png",
        "dst": f"{APP_DIR}/resources/icons/multi1dvisual.png",
        "file_info": {"mode": 0o777},
    })
    files.append({
        "type": "symlink",
        "src": f"../../../../icons/hicolor/512x512/apps/{APP_ID}.png",
        "dst": "/usr/share/doc/multi1dvisual/resources/icons/multi1dvisual.png",
        "file_info": {"mode": 0o777},
    })

    config = {
        "name": "multi1dvisual",
        "version": Config.APP_VERSION,
        "release": "1",
        "arch": "all",
        "platform": "linux",
        "maintainer": f"Bo Xu <{Config.APP_EMAIL}>",
        "homepage": "https://github.com/boxu-pku/MULTI1Dvisual",
        "license": "LicenseRef-proprietary",
        "section": "science",
        "priority": "optional",
        "description": "Desktop viewer for MULTI1D data\nPlot spatial profiles, time series and space-time heatmaps.",
        "contents": files,
        "overrides": {
            "deb": {
                "depends": ["python3", "python3-pyqt5", "python3-numpy", "python3-scipy",
                            "python3-matplotlib", "python3-pandas"],
                "recommends": ["qtwayland5", "fonts-noto-cjk"],
            },
            "rpm": {
                "depends": ["python3", "python3-qt5", "python3-numpy", "python3-scipy",
                            "python3-matplotlib-qt5", "python3-pandas"],
                "recommends": ["qt5-qtwayland"],
            },
        },
    }
    # JSON is a subset of YAML, so nFPM can read this manifest directly.
    manifest = staging / "nfpm.yaml"
    manifest.write_text(json.dumps(config, indent=2), encoding="utf-8")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    for fmt in ("deb", "rpm"):
        subprocess.run(["nfpm", "package", "--config", str(manifest), "--packager", fmt,
                        "--target", str(output) + "/"], check=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="multi1dvisual-") as tmp:
        build(Path(tmp))
