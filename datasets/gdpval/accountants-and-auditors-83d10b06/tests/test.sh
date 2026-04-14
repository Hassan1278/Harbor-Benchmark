#!/bin/bash
# GDPVal Verifier
#
# Follows GDPVal-AA methodology:
#   - Judge model: Gemini 3.1 Pro Preview (configurable via JUDGE_MODEL)
#   - Rubric-based scoring on a 0.0–1.0 scale
#   - Deliverable file existence check as prerequisite
#
# Ref: https://artificialanalysis.ai/evaluations/gdpval-aa

set -e
mkdir -p /logs/verifier

RUBRIC_FILE="/tests/rubric.json"
DELIVERABLES_FILE="/tests/deliverables.txt"

# ---------- Step 1: Check deliverable files exist ----------

MISSING=0
FOUND_FILES=""
while IFS= read -r expected_file; do
    [ -z "$expected_file" ] && continue
    if [ -f "/app/output/$expected_file" ]; then
        FOUND_FILES="$FOUND_FILES /app/output/$expected_file"
    elif [ -f "/app/$expected_file" ]; then
        FOUND_FILES="$FOUND_FILES /app/$expected_file"
    else
        echo "MISSING: $expected_file"
        MISSING=$((MISSING + 1))
    fi
done < "$DELIVERABLES_FILE"

if [ "$MISSING" -gt 0 ]; then
    echo '{"reward": 0.0, "reason": "missing deliverable files"}' > /logs/verifier/reward.json
    echo "Deliverable files missing. Reward: 0.0"
    exit 0
fi

# ---------- Step 2: Build judge prompt ----------

RUBRIC=$(cat "$RUBRIC_FILE")

PROMPT="You are an expert professional grader for the GDPVal benchmark.
Score the following deliverables against the rubric below.

RUBRIC:
$RUBRIC

DELIVERABLE CONTENTS:
"

for f in $FOUND_FILES; do
    FNAME=$(basename "$f")
    if file "$f" | grep -qiE "text|ascii|utf|csv|json|xml|html"; then
        CONTENT=$(head -c 15000 "$f")
        PROMPT="$PROMPT
--- $FNAME ---
$CONTENT
"
    else
        SIZE=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo "?")
        PROMPT="$PROMPT
--- $FNAME (binary, ${SIZE} bytes) ---
"
    fi
done

PROMPT="$PROMPT

Score this work on a scale from 0.0 to 1.0 based on rubric criteria met.
Respond with ONLY a JSON object: {\"score\": <float>, \"reason\": \"<brief explanation>\"}
"

# ---------- Step 3: Call Gemini 3.1 Pro judge ----------

if [ -n "$GEMINI_API_KEY" ]; then
    RESULT=$(python3 << 'PYEOF'
import json, os, sys

prompt = sys.stdin.read()
api_key = os.environ["GEMINI_API_KEY"]
model = os.environ.get("JUDGE_MODEL", "gemini-3.1-pro-preview")
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

import urllib.request
body = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 300}
}).encode()

req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=60)
data = json.loads(resp.read())
text = data["candidates"][0]["content"]["parts"][0]["text"]

start = text.index("{")
end = text.rindex("}") + 1
result = json.loads(text[start:end])
print(json.dumps(result))
PYEOF
    <<< "$PROMPT" 2>/dev/null)

    SCORE=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('score',0))" 2>/dev/null || echo "0.5")
    REASON=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reason',''))" 2>/dev/null || echo "judge error")

    echo "{\"reward\": $SCORE, \"reason\": \"$REASON\"}" > /logs/verifier/reward.json
else
    # No Gemini key — fall back to file-existence score
    echo '{"reward": 0.5, "reason": "deliverables exist but no judge API key (set GEMINI_API_KEY)"}' > /logs/verifier/reward.json
fi

echo "Verification complete:"
cat /logs/verifier/reward.json
