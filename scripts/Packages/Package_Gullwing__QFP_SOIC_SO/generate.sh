#! /usr/bin/env bash

set -ex

for file in ../../../data/Gullwing/*.yaml; do
    filename=$(basename "$file")
    if [ "$filename" != "cq_parameters.yaml" ]; then
        ./ipc_gullwing_generator.py "$file" -v
    fi
done

for file in ../../../tests/generators/Gullwing/*.yaml; do
   ./ipc_gullwing_generator.py "$file" -v --output-dir "test_output"
done
