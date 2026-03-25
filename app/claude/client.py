import json
import os
import shutil
import subprocess
import tempfile

# Find claude CLI in PATH; fall back to common install locations
CLAUDE_BIN = (
    shutil.which("claude")
    or "/opt/homebrew/bin/claude"   # macOS Apple Silicon (Homebrew)
    or "/usr/local/bin/claude"      # macOS Intel (Homebrew)
)


def _env():
    """Full environment with vars removed that would confuse the claude CLI."""
    e = os.environ.copy()
    e.pop("CLAUDECODE", None)       # prevents nested-session error
    e.pop("ANTHROPIC_API_KEY", None)  # prevents invalid-key error (use stored OAuth creds)
    # If NODE_EXTRA_CA_CERTS is set in .env (e.g. for corporate SSL inspection),
    # it's already in the environment and will be passed through automatically.
    return e


def call_claude(prompt: str, retries: int = 3) -> str:
    """
    Call Claude via the claude CLI using a temp file to avoid arg-length limits.
    Uses your existing Claude Code auth — no API key needed.
    """
    for attempt in range(retries):
        tmp_path = None
        try:
            # Write prompt to temp file to avoid CLI argument size limits
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(prompt)
                tmp_path = f.name

            result = subprocess.run(
                ["/bin/bash", "-c", f'cat "{tmp_path}" | {CLAUDE_BIN} -p'],
                capture_output=True,
                text=True,
                timeout=300,
                env=_env(),
            )
            if result.returncode != 0:
                msg = (result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}")
                print(f"[claude] FAIL rc={result.returncode} stderr={result.stderr[:300]!r} stdout={result.stdout[:300]!r}")
                raise RuntimeError(msg)
            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            print(f"[claude] timeout on attempt {attempt + 1}")
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"[claude] attempt {attempt + 1} failed: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    raise RuntimeError("claude CLI failed after retries")


def call_claude_json(prompt: str) -> list | dict:
    """Call Claude and parse the JSON response."""
    raw = call_claude(prompt)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)
