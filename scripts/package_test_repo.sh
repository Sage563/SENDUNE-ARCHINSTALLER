#!/usr/bin/env bash
# Packages the test_feature_repo into a tar.gz that mimics GitHub's archive
set -euo pipefail
WD=$(pwd)
REPO_DIR="$WD/test_feature_repo"
OUT="/tmp/narchs-features-main.tar.gz"
# create an archive with a top-level directory named `narchs-features-main` to mimic GitHub
TMPDIR=$(mktemp -d)
cp -r "$REPO_DIR" "$TMPDIR/narchs-features-main"
cd "$TMPDIR"
tar -czf "$OUT" narchs-features-main
cd "$WD"
echo "Created archive at $OUT"
