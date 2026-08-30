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

echo "==> Ensuring pip is available..."
if python -m pip --version >/dev/null 2>&1; then
    echo "==> pip is already available"
else
    echo "==> pip not found, bootstrapping pip..."
    python -m ensurepip --upgrade
fi

# -----------------------------
# INSTALL TOOLS
# -----------------------------
ensure_package() {
    local package="$1"
    if python -m pip show "$package" >/dev/null 2>&1; then
        echo "==> $package is already installed"
    else
        echo "==> Installing $package..."
        python -m pip install --user "$package"
    fi
}

for pkg in pylint flake8 kodistubs kodi-addon-checker; do
    ensure_package "$pkg"
done

# -----------------------------
# RUN KODI ADDON CHECKER
# -----------------------------
echo "==> Removing build and test cache ..."
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +

echo "==> Running kodi-addon-checker on addon root..."
export PYTHON_SCRIPT="$HOME/AppData/Roaming/Python/Python${PYTHON_VERSION//./}/Scripts"
$PYTHON_SCRIPT/kodi-addon-checker --branch=omega ./plugin.video.arteplussept

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
