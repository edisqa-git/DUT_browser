#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_VENV="${ROOT_DIR}/.venv.update.tmp"
TMP_NPM_CACHE="${ROOT_DIR}/.npm-update-cache"
BRANCH="$(git -C "${ROOT_DIR}" rev-parse --abbrev-ref HEAD)"

if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain)" ]]; then
  echo "Update aborted: working tree has local changes. Commit or stash them first."
  exit 1
fi

echo "Fetching latest code for branch ${BRANCH}..."
git -C "${ROOT_DIR}" fetch --tags origin
git -C "${ROOT_DIR}" pull --ff-only origin "${BRANCH}"

echo "Rebuilding Python environment in a temporary virtualenv..."
rm -rf "${TMP_VENV}"
python3 -m venv "${TMP_VENV}"
"${TMP_VENV}/bin/pip" install --upgrade pip wheel
"${TMP_VENV}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

echo "Reinstalling Node dependencies..."
mkdir -p "${TMP_NPM_CACHE}"
npm install --prefix "${ROOT_DIR}" --cache "${TMP_NPM_CACHE}" --no-audit --no-fund
npm install --prefix "${ROOT_DIR}/dut-dashboard/frontend" --cache "${TMP_NPM_CACHE}" --no-audit --no-fund

echo "Promoting refreshed virtualenv..."
rm -rf "${ROOT_DIR}/.venv.previous"
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  mv "${ROOT_DIR}/.venv" "${ROOT_DIR}/.venv.previous"
fi
mv "${TMP_VENV}" "${ROOT_DIR}/.venv"
rm -rf "${ROOT_DIR}/.venv.previous"

echo "Update complete. Current version: $(cat "${ROOT_DIR}/VERSION")"
