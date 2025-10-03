#! /usr/bin/env bash

set -ex

run_generate() {
    ./ipc_noLead_generator.py "$1" -v
}

for file in ../../../data/no_lead/*.yaml; do
    run_generate "$file"
done

for file in ../../../data/no_lead/qfn/*.yaml; do
    run_generate "$file"
done