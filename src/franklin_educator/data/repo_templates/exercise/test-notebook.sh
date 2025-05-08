#!/bin/sh

PYDEVD_DISABLE_FILE_VALIDATION=1 jupyter nbconvert --Application.log_level=50 --to notebook --execute --inplace exercise.ipynb || exit 1

exec "$@"