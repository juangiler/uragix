# uRage Control

uRage Control sets one uniform lighting color on the supported uRage mouse.
Run its CLI and desktop interface directly from the repository with the
launcher scripts. The project itself does not need to be installed; PyUSB and
PySide6 are external dependencies.

## Set up the desktop interface

From the repository directory on Linux, create and activate a virtual
environment, then install the project dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Launch the GUI from the repository directory:

```sh
./urage-gui
```

The window opens even if the mouse is disconnected; its status will say
**Not detected**. Choosing presets or changing RGB controls only updates the
on-screen preview. The mouse is changed only when you click **Apply Color**.
If the mouse is connected but access is denied, the window reports a USB
permission error.

Desktop menu metadata and an SVG icon for future Linux package builds are in
`packaging/`. The per-user install script below creates a menu entry that
launches this checkout with its virtual environment.

To add a menu shortcut for this checkout on your own account, run:

```sh
./scripts/install_desktop_entry.sh
```

This uses `.venv/bin/python` and stores the shortcut and icon under your user
data directory. Keep the checkout and its `.venv` in place for the shortcut to
keep working.

## Command line

With the virtual environment activated, run the CLI from the repository
directory:

```sh
./urage-cli red
./urage-cli 255 120 0
```

These commands send USB operations to the mouse.
