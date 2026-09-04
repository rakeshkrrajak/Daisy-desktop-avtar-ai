import json
import urllib.request
from urllib.parse import urlparse


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def is_local_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "http" and parsed.hostname in LOCAL_HOSTS
    except Exception:
        return False


def generate_line(
    prompt: str, model: str, url: str, timeout: float = 8.0
) -> str | None:
    if not is_local_url(url):
        return None
    try:
        endpoint = url.rstrip("/") + "/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 40},
            # Keep the model resident in memory for a while after each call
            # so back-to-back reminders don't pay the ~15s cold-start cost
            # again (Ollama's default idle unload is only 5 minutes). This
            # refreshes on every call, and still frees the RAM if Daisy (or
            # Ollama) goes quiet for a longer stretch.
            "keep_alive": "30m",
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        line = " ".join(str(data["response"]).split()).strip()
        return line[:120] or None
    except Exception:
        return None


def build_prompt(tone: str, minutes_overdue: int) -> str:
    return (
        f"Write ONE short water-reminder line in a {tone} tone, max 12 words, "
        f"no quotes, no emoji. The reminder is {max(0, minutes_overdue)} minutes overdue."
    )
