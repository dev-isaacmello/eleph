#!/usr/bin/env bash
# PostToolUse on Edit|Write|MultiEdit. Exit 2 hands stderr back to Claude as an
# error to fix; exit 0 with JSON adds context without blocking.
set -uo pipefail

input=$(cat)
file=$(jq -r '.tool_input.file_path // empty' <<<"$input")
[[ -z "$file" || ! -f "$file" ]] && exit 0

case "$file" in
  */node_modules/* | */dist/* | */.venv/*) exit 0 ;;
esac

root="${CLAUDE_PROJECT_DIR:-$(git -C "$(dirname "$file")" rev-parse --show-toplevel)}"
cd "$root" || exit 0

# Only the text this edit wrote: older site pages still carry em dashes, and
# flagging them on every edit would bury the one that was just introduced.
written=$(jq -r '[.tool_input.new_string, .tool_input.content,
                  (.tool_input.edits // [] | .[].new_string)]
                 | map(select(. != null)) | join("\n")' <<<"$input")
if grep -q $'\u2014' <<<"$written"; then
  echo "travessao (U+2014) em $file. A convencao do projeto proibe; reescreva a frase." >&2
  grep -n $'\u2014' <<<"$written" | head -5 >&2
  exit 2
fi

case "$file" in
  *.py)
    # The one bug that reached PyPI was syntax that only 3.11 rejected.
    if ! out=$(uv run --quiet --no-project --python 3.11 python - "$file" 2>&1 <<'PY'
import sys
compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")
PY
    ); then
      echo "$file nao compila em Python 3.11, o minimo suportado:" >&2
      echo "$out" | tail -5 >&2
      exit 2
    fi
    ;;
  *.eleph)
    # The venv binary, not `uv run`: uv run writes a uv.lock the project does
    # not version, and a hook should not leave files behind.
    eleph=.venv/bin/eleph
    [[ -x $eleph ]] || { echo "sem .venv: rode uv venv && uv pip install -e '.[dev,mcp]'" >&2; exit 2; }
    out=$("$eleph" check "$file" --no-color 2>&1)
    code=$?
    if [[ $code -eq 2 ]]; then
      echo "$file nao e um programa eleph valido:" >&2
      echo "$out" | tail -5 >&2
      exit 2
    fi
    # REPROVADO can be the intended result (the *_buggy.eleph files exist to
    # fail), so the verdict goes back as context, not as an error.
    verdict=$(echo "$out" | grep -E 'PROVADO|REPROVADO|SEM CONTRAEXEMPLO' | tail -1)
    jq -n --arg ctx "eleph check $file: ${verdict:-sem veredito}" \
      '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
    ;;
esac
exit 0
