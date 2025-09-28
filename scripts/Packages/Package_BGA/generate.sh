#! /usr/bin/env bash

set -ex

for file in ../../../data/BGA/*.yaml; do
    filename=$(basename "$file")
    if [ "$filename" != "cq_parameters.yaml" ]; then
        ./ipc_bga_generator.py "$file" -v
    fi
done
