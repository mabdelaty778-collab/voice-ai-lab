"""Generate only local lab configuration. Existing .env files are preserved."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved. Use its LAB_API_KEY in the dashboard.")
else:
    template = (root / ".env.example").read_text()
    template = template.replace("LAB_API_KEY=\n", "LAB_API_KEY=" + secrets.token_urlsafe(32) + "\n")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(template)
    print("Created .env with a random lab key. Open it locally to copy LAB_API_KEY.")
print("Start: python -m uvicorn voice_ai_lab.api:create_app --factory --host 127.0.0.1 --port 8080")
