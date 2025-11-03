#!/usr/bin/env bash

if [[ "$OSTYPE" == "darwin"* ]]; then
command -v greadlink >/dev/null 2>&1 || { echo >&2 "greadlink not found. Install using 'brew install coreutils'"; exit 1; }
BASE_DIR="$(dirname "$(greadlink -f "$0")")"
else
BASE_DIR="$(dirname "$(readlink -f "$0")")"
fi

PYTHONPATH=$BASE_DIR
KICADMODTREE_DIR="$BASE_DIR/KicadModTree"
ACTION=$1

update_packages() {
    pip3 install --upgrade -e .
}

update_dev_packages() {
    pip3 install --upgrade -e '.[dev]'
}

update_3d_packages() {
    pip3 install --upgrade -e '.[3d]'
}

fp_format_check() {
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
        "src"
        "tests"
        "scripts/tests/test_utils"
        "scripts/tools/drawing_tools.py"
        "scripts/tools/misc_tools.py"
        "scripts/tools/nodes/layouts"
        "scripts/generator.py"
        "scripts/Connector_Dsub"
        "scripts/Connector_PinSocket/pin_sockets.py"
        "scripts/LEDs_SMD"
        "scripts/TerminalBlock_Barrier"
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

3d_format_check() {
    set -e
    echo ''
    echo '[!] Running 3D formatting check'
    cd '3d-model-generators'
    python -m isort --check .
    black --check .
    set +e
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
    fp_format_check
    static_type_check
    # 3d_format_check
}



help() {
    [ -z "$1" ] || printf "Error: $1\n"
    echo ''
    echo "Searx manage.sh help

Commands
========
    help                 - This text
    fp_format_check      - pycodestyle/black/isort validation
    3d_format_check      - black/isort validation for 3D generators
    flake8_check         - flake8 validation
    run_shellcheck       - Run CI checks for footprint generators
    unit_tests           - Run unit tests
    py_test_coverage     - Unit test coverage
    tests                - Run all tests
    update_packages      - Check & update production dependency changes
    update_dev_packages  - Check & update development and production dependency changes
    update_3d_packages   - Check & update 3d model generator dependency changes
    static_type_check    - Run a static type check
"
}

#[ "$(command -V "$ACTION" | grep ' function$')" = "" ] \
#    && help "action not found" \
#    || $ACTION
if [ -n "$(type -t $ACTION)" ] && [ "$(type -t $ACTION)" = function ]; then
     $ACTION
 else
     help "action not found"
fi
