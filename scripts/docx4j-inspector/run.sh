#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

quoted_args=()
for arg in "$@"; do
  escaped="${arg//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  quoted_args+=("\"${escaped}\"")
done

mvn -q -f "${SCRIPT_DIR}/pom.xml" exec:java \
  -Dexec.mainClass=org.docfit.docx4j.Docx4jInspect \
  -Dexec.args="${quoted_args[*]}"
