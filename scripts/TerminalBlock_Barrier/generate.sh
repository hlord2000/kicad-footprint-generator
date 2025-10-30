#! /usr/bin/env bash

set -ex

run_generate() {
    ./barrier_gen.py "$1" -v
}

for file in ../../data/TerminalBlock_Barrier/*.yaml; do
    run_generate "$file"
done