#!/usr/bin/env bash


BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" != "main" ]]; then

    echo "You are not on the main branch. Only tag releases on main."
    exit
fi

gh release create --latest "v$(python setup.py --version)" --title "v$(python setup.py --version)" --notes ""