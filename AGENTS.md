# Repository Guidelines

## Project Structure & Module Organization

The repository currently contains the working USB color utility in `mouse_color.py`. Keep hardware protocol code separate from the CLI and GUI. The planned layout places modules under `src/urage_control/`, hardware-free tests under `tests/`, and an optional udev rule under `packaging/`. Do not add captured USB traffic without approval.

Do not create or install this project as a library. Provide runnable Python modules as the CLI and GUI entry points; install only the external dependencies needed to run them.

## Build, Test, and Development Commands

Install development dependencies in a virtual environment with `python -m pip install -r requirements-dev.txt`. Run lint, formatting, type, and hardware-free test checks with `scripts/run_ci.sh`. Running `python3 mouse_color.py red` or the CLI module with a color contacts the USB device; do not use these as routine checks.

## Coding Style & Naming Conventions

Use Python 3, four spaces per indentation level, `snake_case` for functions and variables, and uppercase `SNAKE_CASE` for protocol constants. Prefer focused modules, type hints for public interfaces, explicit validation, and specific exceptions. Use standard-library logging; avoid bare `except` clauses.

## Testing Guidelines

Name test files `test_*.py` and test functions `test_*`. Unit tests must not require a physical mouse: mock PyUSB discovery and transfers. Cover RGB validation, packet bytes and length, failure cleanup, and restoration of detached interfaces. Mocked tests do not establish hardware compatibility. Any physical-device test requires maintainer approval and a description of the USB operations it will perform.

## USB Protocol Compatibility

Treat the existing identifiers, handshake, transfer parameters and order, profile payload, RGB offsets, delay, and reset behavior in `mouse_color.py` as the compatibility baseline. Do not alter or normalize protocol data without documenting the evidence and obtaining approval. Preserve the original script when extracting its implementation, and review changes to protocol constants and packet construction carefully.

## Commits and Pull Requests

No Git history or contribution convention is available in this checkout. Use concise imperative commit subjects. Pull requests should explain the change, list validation commands and results, identify protocol-impacting edits, and include GUI screenshots for visible interface changes. Do not claim hardware testing unless it was performed and approved.

## Security and Configuration

Do not run as root for normal use. Explain any proposed udev rule and its device scope; obtain approval before changing system configuration, installing system components, or writing to the mouse.

## Critical protocol constraints

Preserve the existing working USB protocol.

Do not change handshake bytes, control-transfer parameters, packet layout, RGB offsets, payload length, timing, or reset behavior without explicit approval.

The current RGB offsets are 57, 58, and 59.

Never silently pad, truncate, reorder, or normalize the known-good packet.

Preserve an untouched copy of the original working script.

Do not access the physical mouse during automated tests.


## Workflow

Before editing, inspect the existing files, verify the packet length and RGB offsets, document assumptions, and propose a refactoring plan.

Wait for explicit approval before implementing changes.

Run relevant tests after approved changes and report their actual results.


## Engineering rules

Inspect the repository before editing.

Work in small, reviewable steps.

Separate USB protocol logic, device management, CLI, GUI, and color presets.

Validate RGB values as integers between 0 and 255.

Use explicit error handling and reliable USB resource cleanup.

Write automated tests with mocked USB operations.

Do not claim hardware verification based on mocked tests.

Use PySide6 for the GUI unless a concrete technical issue justifies another framework.

Keep the application focused on selecting and applying one uniform lighting color.

Do not add DPI controls, macros, polling-rate settings, or additional lighting-zone features.

Do not modify system configuration, install system packages, apply udev rules, or write to the physical mouse without explaining the action and obtaining approval.

Do not commit, push, or publish changes without approval.
