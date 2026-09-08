#!/usr/bin/env bash
# Continuous-integration entry point. Run with no arguments to do what CI
# does; run a single stage by name while iterating locally.
#
#   ./ci.sh          lint + test          (the gate; fast, no network, no LLM)
#   ./ci.sh lint     syntax + style only
#   ./ci.sh test     pytest only
#   ./ci.sh manual   regenerate MANUAL.md (needs the `claude` CLI; not in the gate)
#   ./ci.sh all      lint + test + manual
#
# The manual stage authenticates with your Claude subscription. On a runner
# with a funded ANTHROPIC_API_KEY, add --use-api-key to the manual-build call
# in stage_manual below.
#
# Every stage is independent and prints a PASS/FAIL line. The script exits
# non-zero if any stage failed, after running them all — so one run tells you
# everything that is broken, not just the first thing.

set -uo pipefail
cd "$(dirname "$0")"

FAILED=()

# Executables that make up the operator surface, plus the developer tools.
PY_TOOLS=(tasks threads people hours payments buffer lint commit agent-build)
SH_TOOLS=(notes notes_agenda notes_minutes notes_new notes_pdf notes_strip)
DEV_TOOLS=(dev/manual-harvest dev/manual-build dev/manual-diff)

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
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
    printf '  \033[33mSKIP\033[0m shellcheck (not installed)\n'
  fi

  # Every operator tool must answer --help-json. The harvester, agent-build
  # and the agent tool definitions all depend on it, so a tool that loses it
  # silently breaks the manual.
  local hj_fail=0
  for t in tasks notes threads people hours payments buffer lint commit; do
    ./"$t" --help-json >/dev/null 2>&1 || { echo "    $t --help-json"; hj_fail=1; }
  done
  [ $hj_fail -eq 0 ] && ok "--help-json contract" || bad "--help-json contract"
}

stage_test() {
  step "test"
  if python3 -m pytest tests/ -q; then
    ok "pytest"
  else
    bad "pytest"
  fi
}

stage_manual() {
  step "manual"
  if dev/manual-build --out MANUAL.md; then
    ok "MANUAL.md generated"
  else
    bad "MANUAL.md generation"
  fi
}

case "${1:-gate}" in
  lint)   stage_lint ;;
  test)   stage_test ;;
  manual) stage_manual ;;
  all)    stage_lint; stage_test; stage_manual ;;
  gate)   stage_lint; stage_test ;;
  *)      echo "usage: $0 [lint|test|manual|all]" >&2; exit 2 ;;
esac

printf '\n'
if [ ${#FAILED[@]} -eq 0 ]; then
  printf '\033[32mCI passed.\033[0m\n'
  exit 0
fi
printf '\033[31mCI failed:\033[0m %s\n' "${FAILED[*]}"
exit 1
