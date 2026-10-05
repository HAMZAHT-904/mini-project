"""Talks to the local LLM through Ollama's REST API (http://localhost:11434)."""
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"   # change here if you use another model
TIMEOUT_SECONDS = 300        # small models on CPU can be slow


class LLMError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def build_prompt(repo_url: str, tree: str, files: list) -> str:
    code_block = ""
    for path, content in files:
        code_block += f"\n--- FILE: {path} ---\n{content}\n"

    return f"""You are a helpful teacher. Explain this GitHub repository to a college student
in simple language. Use ONLY the information given below. Do not invent features.

Repository: {repo_url}

File list:
{tree}

Source code (some files may be shortened):
{code_block}

Write your answer in Markdown using EXACTLY these five sections:

## Project Overview
## Main Technologies
## Main Features
## How It Works
## Important Files

Rules: keep it simple, use short bullet points, and in "Important Files"
explain the purpose of each important file in one line."""


def explain_with_llm(repo_url: str, tree: str, files: list) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": build_prompt(repo_url, tree, files),
        "stream": False,
        "options": {"num_ctx": 8192, "temperature": 0.3},
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError:
        raise LLMError("Ollama is not running. Open the Ollama app or run 'ollama serve'.", 503)
    except requests.exceptions.Timeout:
        raise LLMError("The model took too long to respond. Try a smaller model or repository.", 504)
    except requests.exceptions.RequestException as e:
        raise LLMError(f"LLM request failed: {e}", 502)

    if response.status_code == 404:
        raise LLMError(f"Model not installed. Run in a terminal: ollama pull {MODEL_NAME}", 503)
    if response.status_code != 200:
        raise LLMError(f"Ollama returned an error ({response.status_code}): {response.text[:200]}", 502)

    text = response.json().get("response", "").strip()
    if not text:
        raise LLMError("The model returned an empty answer. Please try again.", 502)
    return text
