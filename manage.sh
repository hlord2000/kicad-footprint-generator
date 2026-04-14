#!/usr/bin/env bash

if [[ "$OSTYPE" == "darwin"* ]]; then
command -v greadlink >/dev/null 2>&1 || { echo >&2 "greadlink not found. Install using 'brew install coreutils'"; exit 1; }
BASE_DIR="$(dirname "$(greadlink -f "$0")")"
else
BASE_DIR="$(dirname "$(readlink -f "$0")")"
fi

PYTHONPATH=$BASE_DIR
KICADMODTREE_DIR="$BASE_DIR/KicadModTree"
VENV_DIR="$BASE_DIR/.venv"
UV_PYTHON="$VENV_DIR/bin/python"
VENV_BIN="$VENV_DIR/bin"
ACTION=$1

require_uv() {
    command -v uv >/dev/null 2>&1 || {
        echo >&2 "uv not found. Install from https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

ensure_venv() {
    if [ ! -x "$UV_PYTHON" ]; then
        require_uv
        uv venv "$VENV_DIR"
    fi
}

uv_install() {
    ensure_venv
    uv pip install --python "$UV_PYTHON" --upgrade "$@"
}

activate_venv() {
    ensure_venv
    export VIRTUAL_ENV="$VENV_DIR"
    export PATH="$VENV_BIN:$PATH"
}

update_packages() {
    uv_install -e .
}

update_dev_packages() {
    uv_install -e '.[dev]'
}

update_3d_packages() {
    uv_install -e '.[3d]'
}

update_doc_packages() {
    uv_install -e '.[documentation]'
}

format_check() {
    set -e
    echo ''
    echo '[!] Running footprint formatting check'
    pycodestyle --max-line-length=120 \
        "$KICADMODTREE_DIR/" \
        "src/kilibs/geom"

    # Include "clean" scripts (one day this will be all of them)
    local clean_files=(
        "$KICADMODTREE_DIR/nodes/specialized/RoundRectangle.py"
        "$KICADMODTREE_DIR/nodes/specialized/Stadium.py"
        "$KICADMODTREE_DIR/nodes/specialized/Trapezoid.py"
        "src/kilibs"
        "tests"
        "src/generators/tools/footprint/drawing_tools.py"
        "src/generators/tools/footprint/misc_tools.py"
        "src/generators/tools/footprint/nodes/layouts"
        "src/generators/generate.py"
        "src/generators/connector/D_sub"
        "src/generators/LED/SMD"
        "src/generators/terminal_block/Barrier"
    )

    black --check \
        "${clean_files[@]}"
    isort --check-only \
        "${clean_files[@]}"
    set +e
}


static_type_check() {
    set -e
    echo ''
    echo '[!] Running static typing check'
    mypy
    set +e
}

flake8_check() {
    set -e
    echo ''
    echo '[!] Running flake8 check'
    flake8 "$KICADMODTREE_DIR/" \
        "src/kilibs/geom"
    set +e
}

unit_tests() {
    set -e
    echo ''
    echo '[!] Running footprint unit tests'
    python3 -m pytest
    set +e
}

py_test_coverage() {
    echo '[!] Running python test coverage'
    PYTHONPATH=`pwd` python3 -m nose2 -C --coverage "$KICADMODTREE_DIR" --coverage-report term-missing -s "$KICADMODTREE_DIR/tests"
}


run_shellcheck() {
    set -e
    echo ''
    echo '[!] Running shellcheck'
    shellcheck gitlabci/*.sh
    set +e
}

tests() {
    unit_tests
    format_check
    static_type_check
}



help() {
    [ -z "$1" ] || printf "Error: $1\n"
    echo ''
    echo "Searx manage.sh help

Commands
========
    help                 - This text
    format_check         - pycodestyle/black/isort validation
    flake8_check         - flake8 validation
    run_shellcheck       - Run CI checks for footprint generators
    unit_tests           - Run unit tests
    py_test_coverage     - Unit test coverage
    tests                - Run all tests
    update_packages      - Check & update production dependency changes
    update_dev_packages  - Check & update development and production dependency changes
    update_3d_packages   - Check & update 3d model generator dependency changes
    update_doc_packages - CHeck & update the documentation depencency changes
    static_type_check    - Run a static type check
"
}

#[ "$(command -V "$ACTION" | grep ' function$')" = "" ] \
#    && help "action not found" \
#    || $ACTION
if [ -n "$(type -t $ACTION)" ] && [ "$(type -t $ACTION)" = function ]; then
     [ "$ACTION" = "help" ] || activate_venv
     $ACTION
 else
     help "action not found"
fi
