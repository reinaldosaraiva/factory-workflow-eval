#!/usr/bin/env bash
set -euo pipefail

echo "[security] scanning tracked files for potential plaintext secrets"

tmp_matches="$(mktemp)"
trap 'rm -f "$tmp_matches"' EXIT

git ls-files | while IFS= read -r file; do
  case "$file" in
    *.png|*.jpg|*.jpeg|*.gif|*.svg|*.ico|*.pdf|*.lock|*.db) continue ;;
  esac
  rg -n --no-heading \
    -e 'sk-[A-Za-z0-9_-]{20,}' \
    -e 'AIza[0-9A-Za-z\\-_]{35}' \
    -e 'OPENAI_API_KEY\\s*=\\s*.+$' \
    -e 'GEMINI_API_KEY\\s*=\\s*.+$' \
    "$file" >>"$tmp_matches" || true
done

if [ -s "$tmp_matches" ]; then
  echo "[security] potential secrets detected:"
  cat "$tmp_matches"
  exit 1
fi

echo "[security] no potential plaintext secrets found"
