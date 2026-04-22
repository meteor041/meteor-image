#!/usr/bin/env bash

set -euo pipefail

target_dir="${HOME}/.codex/skills"
final_dir="${target_dir}/meteor-image"
tmp_dir="$(mktemp -d)"

cleanup() {
  rm -rf "${tmp_dir}"
}

trap cleanup EXIT

mkdir -p "${target_dir}"

curl -fsSL "https://github.com/meteor041/meteor-image/archive/refs/heads/main.tar.gz" \
  | tar -xz -C "${tmp_dir}"

rm -rf "${final_dir}"
mv "${tmp_dir}/meteor-image-main" "${final_dir}"
