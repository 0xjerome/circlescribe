#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Python not found. Create backend/.venv or install Python 3.10+." >&2
  exit 1
fi

echo "== CircleScribe submission check =="
echo "Python: $PYTHON"

echo
echo "1/4 Repository preflight"
"$PYTHON" "$ROOT/backend/scripts/preflight.py"

echo
echo "2/4 Backend safety + integration tests"
(
  cd "$ROOT/backend"
  "$PYTHON" -m unittest discover -s tests -v
)

echo
echo "3/4 Frontend production build"
(
  cd "$ROOT/frontend"
  npm ci
  NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}" npm run build
)

echo
echo "4/4 Required submission artifacts"
required=(
  "$ROOT/README.md"
  "$ROOT/LICENSE"
  "$ROOT/docs/CircleScribe_Architecture_Submission.png"
  "$ROOT/docs/JUDGING.md"
  "$ROOT/docs/TESTING.md"
  "$ROOT/docs/AWS_READINESS.md"
  "$ROOT/docs/DEMO_SCRIPT.md"
  "$ROOT/docs/DEVPOST_SUBMISSION.md"
  "$ROOT/docs/SUBMISSION_CHECKLIST.md"
)

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
done

echo
echo "CircleScribe submission check PASSED"
