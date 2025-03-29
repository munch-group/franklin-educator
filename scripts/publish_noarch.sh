#!/usr/bin/env bash

set -e

if [ -z "$(git status --porcelain)" ];
then
    echo "Working directory clean. Proceeding..."
else
    echo "Uncommitted changes. Please commit or stash before proceeding."
    exit 1
fi

source ~/miniconda3/etc/profile.d/conda.sh

conda activate condabuild

gh release create --latest -p v$(python setup.py --version)

cd conda-build

conda build .

cd ..

conda deactivate
