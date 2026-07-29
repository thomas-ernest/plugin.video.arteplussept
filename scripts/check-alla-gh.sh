#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="3.11"

# Ensure ~/.local/bin is in PATH (pip --user installs here)
export PATH="$HOME/.local/bin:$PATH"

# Run commands from extension root directory
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.." || exit 1

echo "==> Checking if Python $PYTHON_VERSION is installed..."
[ "$(python --version 2>&1 | cut -d' ' -f2 | cut -d. -f1-2)" = $PYTHON_VERSION ] || exit 3

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

# -----------------------------
# INSTALL TOOLS
# -----------------------------
echo "==> Installing kodi-addon-checker..."
pip3 install --user kodi-addon-checker

echo "==> Installing pylint, flake8, kodistubs..."
pip3 install --user pylint flake8 kodistubs

# -----------------------------
# RUN KODI ADDON CHECKER
# -----------------------------
echo "==> Removing __pycache__ ..."
find . -type d -name __pycache__ -exec rm -rf {} +

echo "==> Running kodi-addon-checker on addon root..."
export PYTHON_SCRIPT="$HOME/AppData/Roaming/Python/Python${PYTHON_VERSION//./}/Scripts"
$PYTHON_SCRIPT/kodi-addon-checker --branch=matrix ./plugin.video.arteplussept

# -----------------------------
# RUN PYLINT
# -----------------------------
echo "==> Running pylint..."
PY_FILES=$(git ls-files '*.py')

if [ -z "$PY_FILES" ]; then
    echo "No Python files found."
else
    python -m pylint $PY_FILES
fi

# -----------------------------
# RUN FLAKE8
# -----------------------------
echo "==> Running flake8..."
python -m flake8 $PY_FILES --max-line-length=100

echo "==> All checks completed."
