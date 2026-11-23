# Build desktop installers

For ready-to-install Debian, Fedora and Windows packages, see the [MULTI1Dvisual 2.3.1 release](https://github.com/boxu-pku/MULTI1Dvisual/releases/tag/v2.3.1).

Run these commands from the repository root. Both builders read the application version from `utils/config.py` and write the installers to `dist/`.

## Linux packages

Use Python 3, Pillow 9.1 or later and nFPM v2 on the build machine. Make the `nfpm` executable available on `PATH`. [nFPM downloads](https://github.com/goreleaser/nfpm/releases)

```sh
python3 packaging/linux/build.py
```

The Debian/Ubuntu and Fedora packages contain the Python sources, the launcher, AppStream metadata, desktop menu entry and hicolor icons. The distribution package manager supplies Python, Qt and the plotting libraries for the installed architecture. The launcher uses the distribution's Python interpreter. The installed command is `multi1dvisual`.

To check an installed package, run `sh packaging/linux/check-installed.sh` as a regular user. The check opens the desktop entry under Xvfb and inspects the window icon and per-user log. It uses `desktop-file-validate`, `appstreamcli`, `gio`, `xvfb-run`, `xauth`, `dbus-run-session`, `xdotool` and `xprop`.

## Windows x64

Install Inno Setup 6 and use a clean 64-bit Python virtual environment. The installer includes the runtime, a Start menu entry, an optional desktop shortcut and an uninstaller.

```powershell
py -3.14 -m venv build/winenv
.\build\winenv\Scripts\python -m pip install -r requirements.txt "pyinstaller>=6.12,<7"
.\build\winenv\Scripts\python packaging/windows/build.py
```
