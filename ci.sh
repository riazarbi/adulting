#!/usr/bin/env bash
# Continuous-integration entry point. Run with no arguments to do what CI
# does; run a single stage by name while iterating locally.
#
#   ./ci.sh          lint + test          (the gate; fast, no network, no LLM)
#   ./ci.sh lint     syntax + style only
#   ./ci.sh test     pytest only
#   ./ci.sh generate regenerate MANUAL.md and dev/tools/ (needs `claude`)
#   ./ci.sh manual   regenerate MANUAL.md only            (needs `claude`)
#   ./ci.sh tools    regenerate dev/tools/ only           (needs `claude`)
#   ./ci.sh all      lint + test + generate
#
# The corpus is harvested at most ONCE per run and shared by both generators,
# so MANUAL.md and dev/tools/ are built from byte-identical input and cannot
# describe different versions of the tools. Regenerate and commit together.
#
# Generation authenticates with your Claude subscription. On a runner with a
# funded ANTHROPIC_API_KEY, add --use-api-key to the build calls below.
#
# Every stage is independent and prints a PASS/FAIL line. The script exits
# non-zero if any stage failed, after running them all — so one run tells you
# everything that is broken, not just the first thing.

set -uo pipefail
cd "$(dirname "$0")"

FAILED=()

# Executables that make up the operator surface, plus the developer tools.
PY_TOOLS=(tasks search threads people hours payments buffer lint commit)
SH_TOOLS=(notes notes_agenda notes_minutes notes_new notes_pdf notes_strip)
DEV_TOOLS=(dev/manual-harvest dev/manual-build dev/manual-diff
           dev/tools-build dev/tools-check)

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
skip() { printf '  \033[33mSKIP\033[0m %s\n' "$1"; }
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILED+=("$1"); }

stage_lint() {
  step "lint"

  # Python: compile every module and executable. Catches syntax errors in
  # files the test suite happens not to import.
  local py_fail=0
  for f in *.py "${PY_TOOLS[@]}" "${DEV_TOOLS[@]}"; do
    [ -f "$f" ] || continue
    python3 -m py_compile "$f" 2>&1 || { echo "    $f"; py_fail=1; }
  done
  [ $py_fail -eq 0 ] && ok "python syntax" || bad "python syntax"

  # Bash: parse-check every script.
  local sh_fail=0
  for f in "${SH_TOOLS[@]}" ci.sh; do
    [ -f "$f" ] || continue
    bash -n "$f" 2>&1 || { echo "    $f"; sh_fail=1; }
  done
  [ $sh_fail -eq 0 ] && ok "bash syntax" || bad "bash syntax"

  # Errors gate the build; warnings do not. Not installed everywhere, so a
  # missing binary skips rather than fails.
  if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck -S error "${SH_TOOLS[@]}" ci.sh; then
      ok "shellcheck (errors)"
    else
      bad "shellcheck (errors)"
    fi
  else
    skip "shellcheck (not installed)"
  fi

  # Every operator tool must answer --help-json. The harvester, agent-build
  # and the agent tool definitions all depend on it, so a tool that loses it
  # silently breaks the manual.
  local hj_fail=0
  for t in tasks notes search threads people hours payments buffer lint commit; do
    ./"$t" --help-json >/dev/null 2>&1 || { echo "    $t --help-json"; hj_fail=1; }
  done
  [ $hj_fail -eq 0 ] && ok "--help-json contract" || bad "--help-json contract"

  # The committed agent tool definitions must stay loadable and in scope.
  # Deterministic, so it belongs in the gate rather than the generation stage.
  if dev/tools-check >/dev/null; then
    ok "dev/tools definitions"
  else
    dev/tools-check
    bad "dev/tools definitions"
  fi
}

stage_test() {
  step "test"
  if python3 -m pytest tests/ -q; then
    ok "pytest"
  else
    bad "pytest"
  fi
}

# The corpus is a pure function of the tree, so harvesting twice would give
# the same bytes — but harvesting once makes that a fact rather than an
# assumption, and every generator in a run then shares provably equal input.
# Harvesting executes every operator binary and each of their subcommands —
# the one genuinely expensive step here. It happens at most once per run: the
# JSON corpus is harvested, the markdown the generators read is rendered from
# that JSON, and every stage below shares both. Byte-identical input for all
# consumers is then a fact of the run, not an inference from determinism.
CORPUS=""       # markdown, for the two generators
CORPUS_JSON=""  # structured, for the validator

ensure_corpus() {
  [ -n "$CORPUS" ] && return 0
  local js md
  js=$(mktemp -t adulting-corpus-json.XXXXXX) || return 1
  md=$(mktemp -t adulting-corpus-md.XXXXXX) || { rm -f "$js"; return 1; }
  if ! dev/manual-harvest --format json >"$js" 2>/dev/null \
     || ! dev/manual-harvest --from-json "$js" --format md >"$md" 2>/dev/null; then
    rm -f "$js" "$md"
    return 1
  fi
  CORPUS_JSON="$js"
  CORPUS="$md"
  printf '  harvested once: %s bytes of corpus\n' "$(wc -c <"$CORPUS" | tr -d ' ')"
}

cleanup_corpus() { rm -f "$CORPUS" "$CORPUS_JSON"; }
trap cleanup_corpus EXIT

stage_manual() {
  step "manual"
  if ! ensure_corpus; then bad "corpus harvest"; return; fi
  if dev/manual-build --corpus "$CORPUS" --out MANUAL.md; then
    ok "MANUAL.md generated"
  else
    bad "MANUAL.md generation"
  fi
}

stage_tools() {
  step "tools"
  if ! ensure_corpus; then bad "corpus harvest"; return; fi
  if dev/tools-build --corpus "$CORPUS" --out dev/tools \
     && dev/tools-check --corpus-json "$CORPUS_JSON"; then
    ok "dev/tools generated"
  else
    bad "dev/tools generation"
  fi
}

case "${1:-gate}" in
  lint)     stage_lint ;;
  test)     stage_test ;;
  manual)   stage_manual ;;
  tools)    stage_tools ;;
  generate) stage_manual; stage_tools ;;
  gate)     stage_lint; stage_test ;;
  all)      stage_lint; stage_test; stage_manual; stage_tools ;;
  *)        echo "usage: $0 [lint|test|manual|tools|generate|all]" >&2; exit 2 ;;
esac

printf '\n'
if [ ${#FAILED[@]} -eq 0 ]; then
  printf '\033[32mCI passed.\033[0m\n'
  exit 0
fi
printf '\033[31mCI failed:\033[0m %s\n' "${FAILED[*]}"
exit 1
