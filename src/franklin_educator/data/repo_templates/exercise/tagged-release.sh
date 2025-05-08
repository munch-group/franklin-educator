#!/usr/bin/env bash

set -x

git tag -a $1
git push origin --tags


