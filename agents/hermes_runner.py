import json
import os
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = PROJECT_ROOT / "hermes-agent"
HERMES_ENTRYPOINT = HERMES_ROOT / "run_agent.py"
HERMES_HOME = PROJECT_ROOT / ".hermes-runtime"
DEFAULT_HERMES_MODEL = os.getenv("HERMES_MODEL", "openai/gpt-4o-mini")


def _find_first_json_object(text):
    decoder = json.JSONDecoder()

    for index, char in enumerate(text):
        if char != "{":
            continue

        try:
            obj, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(obj, dict):
            return obj

    raise ValueError("Hermes response did not contain a valid JSON object")


def _extract_final_response_block(text):
    patterns = [
        r"FINAL RESPONSE:\s*-+\s*(.*?)(?:\n👋 Agent execution completed!|\Z)",
        r"FINAL RESPONSE:\s*(.*?)(?:\n👋 Agent execution completed!|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
    return text.strip()


def _run_hermes_task(prompt, timeout=240):
    if not HERMES_ENTRYPOINT.exists():
        raise FileNotFoundError(
            "Hermes runner was not found. Expected local checkout at "
            f"{HERMES_ENTRYPOINT}."
        )

    HERMES_HOME.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    project_pythonpath = str(HERMES_ROOT)
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = (
        project_pythonpath
        if not existing_pythonpath
        else os.pathsep.join([project_pythonpath, existing_pythonpath])
    )
    env["HERMES_HOME"] = str(HERMES_HOME)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    command = [
        sys.executable,
        str(HERMES_ENTRYPOINT),
        "--query",
        prompt,
        "--max_turns",
        "1",
        "--model",
        DEFAULT_HERMES_MODEL,
    ]

    result = subprocess.run(
        command,
        cwd=HERMES_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        details = stderr or stdout or "Unknown Hermes error"
        raise RuntimeError(
            "Hermes extraction failed. Make sure Hermes dependencies are installed "
            f"for this environment. Details: {details}"
        )

    return stdout


def run_hermes_text_task(prompt, timeout=240):
    raw_output = _run_hermes_task(prompt, timeout=timeout)
    return _extract_final_response_block(raw_output)


def run_hermes_json_task(prompt, timeout=240):
    raw_output = _run_hermes_task(prompt, timeout=timeout)
    final_response = _extract_final_response_block(raw_output)

    try:
        return _find_first_json_object(final_response)
    except Exception:
        return _find_first_json_object(raw_output)
