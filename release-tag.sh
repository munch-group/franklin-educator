#!/usr/bin/env bash

if [[ `git status --porcelain` ]]; then
  echo "Changes to pyproject.toml must be pushed first."
else
    git tag -a "v$(python setup.py --version)" -m "${1:-Release}"
    git push origin --tags
fi