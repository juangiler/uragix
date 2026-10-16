#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
venv_python="$repo_root/.venv/bin/python"
gui_launcher="$repo_root/urage-gui"
icon_source="$repo_root/packaging/icons/hicolor/scalable/apps/urage-control.svg"

if [[ ! -x "$venv_python" ]]; then
    printf 'Virtual environment not found at %s\n' "$venv_python" >&2
    printf 'Create it and install requirements.txt before adding the menu entry.\n' >&2
    exit 1
fi

if [[ ! -x "$gui_launcher" || ! -f "$icon_source" ]]; then
    printf 'GUI launcher or app icon is missing from %s\n' "$repo_root" >&2
    exit 1
fi

python3 - "$repo_root" "$venv_python" "$gui_launcher" "$icon_source" <<'PY'
import os
import shutil
import sys
from pathlib import Path


def desktop_quote(value: str) -> str:
    for char in ("\\", '"', chr(96), chr(36)):
        value = value.replace(char, "\\" + char)
    return f'"{value}"'


repo_root, python_path, launcher_path, icon_source = map(Path, sys.argv[1:])
data_home = Path(
    os.environ.get("XDG_DATA_HOME") or "~/.local/share"
).expanduser()
applications_dir = data_home / "applications"
icon_dir = data_home / "icons/hicolor/scalable/apps"
applications_dir.mkdir(parents=True, exist_ok=True)
icon_dir.mkdir(parents=True, exist_ok=True)

desktop_file = applications_dir / "urage-control.desktop"
icon_file = icon_dir / "urage-control.svg"
exec_command = f"{desktop_quote(str(python_path))} {desktop_quote(str(launcher_path))}"
desktop_file.write_text(
    "\n".join(
        (
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=uRage Control",
            "Comment=Set the lighting color on a supported uRage mouse",
            f"Exec={exec_command}",
            "Icon=urage-control",
            "Terminal=false",
            "Categories=Utility;Settings;",
            "Keywords=mouse;lighting;color;",
            "StartupNotify=true",
            "",
        )
    ),
    encoding="utf-8",
)
shutil.copyfile(icon_source, icon_file)
print(f"Created application menu entry: {desktop_file}")
print(f"Installed app icon: {icon_file}")
print(f"The entry launches the checkout at: {repo_root}")
PY
