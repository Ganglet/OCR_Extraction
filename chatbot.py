"""Document chatbot backed by OpenRouter (Qwen3-VL by default).

Self-contained and independent of the Gemini extraction stack: upload an image
once to get a session_id, then ask many independent questions about it.
"""
import os
import time
import uuid
import base64
from io import BytesIO

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Pinned vision model; override via env. Not 'openrouter/auto' on purpose —
# we want a known vision-capable model and consistent answers across questions.
CHATBOT_MODEL = os.getenv("CHATBOT_MODEL", "qwen/qwen3-vl-30b-a3b-instruct")
SYSTEM_PROMPT = (
    "You are a document assistant. Answer strictly based on the provided document "
    "image. If the answer is not visible in the document, say you cannot find it. "
    "Do not invent information."
)

# session_id -> {"image": data_url, "created_at": ts}
# In-memory: does not survive restart and breaks under `docker-compose --scale`
# (upload and question may hit different replicas). Use Redis for scaled prod.
CHAT_SESSIONS = {}


def to_data_url(filename, raw):
    """Build a base64 data URL OpenRouter accepts. PDF -> first page PNG."""
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        # Reuse the batch task's 2x fitz render. Local import avoids a circular
        # import at module load (fastapi_app imports this module).
        from fastapi_app import bytes_to_image
        buf = BytesIO()
        bytes_to_image(filename, raw).save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    if ext in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
        mime = "image/jpeg" if ext in ('jpg', 'jpeg') else f"image/{ext}"
        return f"data:{mime};base64," + base64.b64encode(raw).decode()
    raise ValueError("Input file format must be 'jpg','jpeg','png','webp','gif' or 'pdf'.")


def create_session(data_url):
    session_id = uuid.uuid4().hex
    CHAT_SESSIONS[session_id] = {"image": data_url, "created_at": time.time()}
    return session_id


def ask(session_id, question):
    """Answer a question about the session's image. Returns None if session unknown."""
    session = CHAT_SESSIONS.get(session_id)
    if not session:
        return None

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set.")

    resp = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": CHATBOT_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": session["image"]}},
                ]},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
