#!/bin/zsh
set -eu
project_dir="${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
exec python3 "$project_dir/scripts/run_test_session.py"
