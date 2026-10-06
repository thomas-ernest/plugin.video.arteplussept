#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="3.11"

usage() {
    cat <<EOF
Usage: $0 [--help] [--prerequisites] [--syntax] [--kodi] [--all]

Prepare the environment and run selected checks for the add-on.

Options:
  -h, --help           Show this help. This is the default when no options are given.
      --prerequisites  Check Python, pip, and install the required check tools.
      --syntax         Run pylint and flake8.
      --kodi           Run kodi-addon-checker.
      --all            Run prerequisites, syntax checks, and the Kodi check.

Prerequisites are checked and tools installed only with --prerequisites or
--all; --syntax and --kodi run without preparing the environment. Use
--prerequisites alone to prepare the environment without running checks. The
three check options can be combined.

Examples:
  $0                      Show this help
  $0 --prerequisites      Prepare the environment only
  $0 --syntax --kodi      Run both checks
  $0 --all                Run all checks
EOF
}

show_help=false
run_prerequisites=false
run_syntax=false
run_kodi=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help)
            show_help=true
            ;;
        --prerequisites)
            run_prerequisites=true
            ;;
        --syntax)
            run_syntax=true
            ;;
        --kodi)
            run_kodi=true
            ;;
        --all)
            run_prerequisites=true
            run_syntax=true
            run_kodi=true
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [ "$show_help" = true ]; then
    if [ "$run_prerequisites" = true ] || [ "$run_syntax" = true ] || [ "$run_kodi" = true ]; then
        echo "Error: --help cannot be combined with check options." >&2
        usage >&2
        exit 2
    fi
    usage
    exit 0
fi

if [ "$run_prerequisites" = false ] && [ "$run_syntax" = false ] && [ "$run_kodi" = false ]; then
    usage
    exit 0
fi

# Ensure ~/.local/bin is in PATH (pip --user installs here)
export PATH="$HOME/.local/bin:$PATH"

# Run commands from extension root directory
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.." || exit 1

if [ "$run_prerequisites" = true ]; then
    echo "==> Checking if Python $PYTHON_VERSION is installed..."
    [ "$(python --version 2>&1 | cut -d' ' -f2 | cut -d. -f1-2)" = "$PYTHON_VERSION" ] || exit 3

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
fi

if [ "$run_kodi" = true ]; then
    # -----------------------------
    # RUN KODI ADDON CHECKER
    # -----------------------------
    echo "==> Removing build and test cache ..."
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type d -name .pytest_cache -exec rm -rf {} +

    echo "==> Running kodi-addon-checker on addon root..."
    export PYTHON_SCRIPT="$HOME/AppData/Roaming/Python/Python${PYTHON_VERSION//./}/Scripts"
    $PYTHON_SCRIPT/kodi-addon-checker --branch=omega ./plugin.video.arteplussept
fi

if [ "$run_syntax" = true ]; then
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
fi

if [ "$run_prerequisites" = true ] && [ "$run_syntax" = false ] && [ "$run_kodi" = false ]; then
    echo "==> Environment prerequisites are ready."
else
    echo "==> Selected checks completed."
fi
