#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  validate_no_gemini25_in_draft.sh --draft-file <path>
  validate_no_gemini25_in_draft.sh --app-id <uuid> [--base-url <url>] [--cookie-file <path>]

Examples:
  scripts/factory/validate_no_gemini25_in_draft.sh --draft-file /tmp/draft.json
  scripts/factory/validate_no_gemini25_in_draft.sh --app-id 30c441d5-0232-4329-9f58-5685dd5f304c --cookie-file /tmp/dify_console_cookie.txt
USAGE
}

BASE_URL="http://127.0.0.1:18080/console/api"
COOKIE_FILE="/tmp/dify_console_cookie.txt"
DRAFT_FILE=""
APP_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --draft-file)
      DRAFT_FILE="${2:-}"
      shift 2
      ;;
    --app-id)
      APP_ID="${2:-}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --cookie-file)
      COOKIE_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$DRAFT_FILE" && -z "$APP_ID" ]]; then
  echo "You must provide --draft-file or --app-id" >&2
  usage
  exit 2
fi

TMP_JSON=""
if [[ -n "$APP_ID" ]]; then
  TMP_JSON="$(mktemp)"
  curl -fsS -X GET "${BASE_URL}/apps/${APP_ID}/workflows/draft" -b "$COOKIE_FILE" > "$TMP_JSON"
  DRAFT_FILE="$TMP_JSON"
fi

if [[ ! -f "$DRAFT_FILE" ]]; then
  echo "Draft file not found: $DRAFT_FILE" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 2
fi

BLOCKED="$(jq -r '
  .graph.nodes[]
  | select(.data.type=="llm")
  | {id: .id, title: .data.title, provider: .data.model.provider, model: .data.model.name}
  | select(.model | test("^gemini-2\\.5"))
  | @json
' "$DRAFT_FILE")"

if [[ -n "$BLOCKED" ]]; then
  echo "FAIL: blocked model family detected (gemini-2.5-*)" >&2
  echo "$BLOCKED" >&2
  exit 1
fi

echo "PASS: no gemini-2.5-* model configured in LLM nodes."
jq -r '
  .graph.nodes[]
  | select(.data.type=="llm")
  | [.id, .data.title, .data.model.provider, .data.model.name]
  | @tsv
' "$DRAFT_FILE"

