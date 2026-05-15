#!/usr/bin/env bash
set -euo pipefail

TOKEN="${CANVAS_TOKEN:?set CANVAS_TOKEN}"
COURSE_ID="${COURSE_ID:-225539}"
BASE="https://canvas.stanford.edu/api/v1"
OUT_DIR="${OUT_DIR:-./files}"

mkdir -p "$OUT_DIR"

auth=(-H "Authorization: Bearer $TOKEN")

# Walk paginated endpoints by following the rfc5988 next-link header.
paginate() {
  local url="$1"
  while [[ -n "$url" ]]; do
    local headers body
    headers=$(mktemp)
    body=$(curl -sS -D "$headers" "${auth[@]}" "$url")
    echo "$body"
    url=$(grep -i '^link:' "$headers" | tr ',' '\n' | grep 'rel="next"' | sed -E 's/.*<([^>]+)>.*/\1/' | head -1 || true)
    rm -f "$headers"
  done
}

sanitize() {
  # Strip slashes and control chars; collapse whitespace.
  printf '%s' "$1" | tr '/' '_' | tr -d '\000-\037' | sed 's/  */ /g'
}

# Pull every module, then every item; for File items fetch file metadata + download.
modules_json=$(paginate "$BASE/courses/$COURSE_ID/modules?per_page=100" | jq -s 'add')
echo "$modules_json" | jq -r '.[] | "\(.id)\t\(.name)\t\(.position)"' | \
while IFS=$'\t' read -r mid mname mpos; do
  mdir="$OUT_DIR/$(printf '%02d' "$mpos")_$(sanitize "$mname")"
  mkdir -p "$mdir"
  echo ">> Module: $mname"

  items_json=$(paginate "$BASE/courses/$COURSE_ID/modules/$mid/items?per_page=100" | jq -s 'add')
  echo "$items_json" | jq -c '.[]' | while read -r item; do
    type=$(echo "$item" | jq -r '.type')
    title=$(echo "$item" | jq -r '.title')
    case "$type" in
      File)
        cid=$(echo "$item" | jq -r '.content_id')
        meta=$(curl -sS "${auth[@]}" "$BASE/files/$cid")
        url=$(echo "$meta" | jq -r '.url')
        fname=$(echo "$meta" | jq -r '.display_name // .filename')
        [[ -z "$url" || "$url" == "null" ]] && { echo "  ! no url for $title"; continue; }
        out="$mdir/$(sanitize "$fname")"
        echo "  - $fname"
        curl -sSL -o "$out" "$url"
        ;;
      Page|Assignment|Quiz|Discussion|ExternalUrl|ExternalTool|SubHeader)
        # Save a pointer so the module structure is preserved.
        url=$(echo "$item" | jq -r '.html_url // .external_url // empty')
        if [[ -n "$url" ]]; then
          echo "$url" > "$mdir/$(sanitize "$title").${type}.url"
        fi
        ;;
    esac
  done
done

echo "Done. Files in: $OUT_DIR"
