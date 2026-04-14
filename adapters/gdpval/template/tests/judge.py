#!/usr/bin/env python3
"""
GDPVal judge — extracts deliverables to text, then scores against rubric.

Provider priority (first match wins):
  1. Gemini        (GEMINI_API_KEY)           — paper default (gemini-3.1-pro-preview)
  2. Anthropic     (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN)
  3. Ollama Cloud  (http://host.docker.internal:11434) — free, uses a cloud model
  4. Fallback      (no judge reachable) — reward 0.5

Override with JUDGE_PROVIDER=gemini|anthropic|ollama and JUDGE_MODEL=<id>.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

RUBRIC_PATH = Path("/tests/rubric.json")
DELIVERABLES_PATH = Path("/tests/deliverables.txt")
REWARD_PATH = Path("/logs/verifier/reward.json")
MAX_CONTENT_CHARS = 60_000


def extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    parts: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"### Sheet: {sheet_name}")
        for row in ws.iter_rows(values_only=True):
            parts.append("\t".join("" if c is None else str(c) for c in row))
    return "\n".join(parts)


def extract_pdf(path: Path) -> str:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n\n".join((page.extract_text() or "") for page in pdf.pages)


def extract_docx(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


EXTRACTORS = {
    ".xlsx": extract_xlsx, ".xlsm": extract_xlsx, ".xls": extract_xlsx,
    ".pdf": extract_pdf,
    ".docx": extract_docx,
}


def extract(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in EXTRACTORS:
            content = EXTRACTORS[ext](path)
        else:
            content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[extraction failed for {path.name}: {e}]"
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS] + "\n[...truncated...]"
    return content


def find_deliverable(name: str) -> Path | None:
    for root in (Path("/app/output"), Path("/app")):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def http_post_json(url: str, body: dict, headers: dict, timeout: int = 120) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def parse_score(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def judge_gemini(prompt: str) -> dict | None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("JUDGE_MODEL", "gemini-3.1-pro-preview")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    data = http_post_json(url, {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 500},
    }, {})
    return parse_score(data["candidates"][0]["content"]["parts"][0]["text"])


def judge_anthropic(prompt: str) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    oauth = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if key:
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    elif oauth:
        headers = {
            "Authorization": f"Bearer {oauth}",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-04-20",
        }
    else:
        return None
    model = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-5")
    data = http_post_json("https://api.anthropic.com/v1/messages", {
        "model": model, "max_tokens": 500, "temperature": 0.0,
        "messages": [{"role": "user", "content": prompt}],
    }, headers)
    return parse_score(data["content"][0]["text"])


def judge_ollama(prompt: str) -> dict | None:
    host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
    model = os.environ.get("JUDGE_MODEL", "gpt-oss:120b-cloud")
    data = http_post_json(f"{host}/api/generate", {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.0},
    }, {}, timeout=180)
    return parse_score(data.get("response", ""))


JUDGES = {"gemini": judge_gemini, "anthropic": judge_anthropic, "ollama": judge_ollama}


def pick_judge_order() -> list[str]:
    forced = os.environ.get("JUDGE_PROVIDER")
    if forced and forced in JUDGES:
        return [forced]
    return ["gemini", "anthropic", "ollama"]


def write_reward(reward: float, reason: str, judge: str = "none") -> None:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps({"reward": reward}))
    (REWARD_PATH.parent / "judge.json").write_text(json.dumps({
        "reward": reward, "reason": reason, "judge": judge,
    }, indent=2))


def main() -> None:
    deliverables = [
        d.strip() for d in DELIVERABLES_PATH.read_text().splitlines() if d.strip()
    ]

    found: dict[str, Path] = {}
    missing: list[str] = []
    for name in deliverables:
        path = find_deliverable(name)
        if path is None:
            missing.append(name)
        else:
            found[name] = path

    if missing:
        write_reward(0.0, f"missing deliverables: {', '.join(missing)}")
        print(f"Missing: {missing}. Reward: 0.0")
        return

    rubric = RUBRIC_PATH.read_text() if RUBRIC_PATH.exists() else "[]"
    body = "".join(f"\n--- {n} ---\n{extract(p)}" for n, p in found.items())

    prompt = (
        "You are an expert professional grader for the GDPVal benchmark.\n"
        "Score the deliverables below against the rubric.\n\n"
        f"RUBRIC:\n{rubric}\n\n"
        f"DELIVERABLE CONTENTS:\n{body}\n\n"
        "Score on a scale from 0.0 to 1.0 based on the fraction of rubric points earned.\n"
        'Respond with ONLY a JSON object: {"score": <float 0-1>, "reason": "<brief>"}\n'
    )

    for name in pick_judge_order():
        try:
            result = JUDGES[name](prompt)
        except Exception as e:
            print(f"Judge {name} errored: {e}", file=sys.stderr)
            continue
        if result is None:
            continue
        score = max(0.0, min(1.0, float(result.get("score", 0.5))))
        reason = str(result.get("reason", ""))[:500]
        write_reward(score, reason, judge=name)
        print(f"Judge: {name}. Reward: {score}. Reason: {reason}")
        return

    write_reward(0.5, "deliverables exist but no judge reachable", judge="fallback")
    print("No judge reachable. Reward: 0.5")


if __name__ == "__main__":
    main()
