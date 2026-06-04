#!/usr/bin/env bash
# Deprecated: use ./build-and-deploy.sh
exec "$(dirname "$0")/build-and-deploy.sh" build "$@"
