#! /usr/bin/env bash

set -ex

run_generate() {
    ./make_Chokes_THT.py -v size_definitions
}

run_generate
