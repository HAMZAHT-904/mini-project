"""
Clones a GitHub repo and picks the most relevant source files.

SECURITY: We only open files and read them as plain text.
We NEVER run, import, or execute anything from the cloned repository.

HOW THE SIZE LIMIT WORKS (token/context management):
A small local LLM can only read a limited amount of text at once.
So we do NOT send the whole repo. Instead we:
  1. Skip junk folders (node_modules, .git, venv, ...) and non-code files.
  2. Give every file a priority score (README, package.json, main.py, src/ ... rank high).
  3. Sort by score and add files until we hit these limits:
       MAX_FILES, MAX_CHARS_PER_FILE (each file is cut), MAX_TOTAL_CHARS (overall).
  4. Also send a short file list so the LLM knows what else exists.
"""
import os
import shutil
import stat
import uuid
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

TEMP_DIR = Path(__file__).resolve().parent.parent / "temp_repos"

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go",
    ".rs", ".php", ".rb", ".html", ".css", ".jsx", ".tsx", ".sql",
}
# Not code, but very useful to understand a project (name -> priority score)
SPECIAL_FILES = {
    "readme.md": 100, "package.json": 90, "requirements.txt": 90,
    "pom.xml": 90, "build.gradle": 80, "go.mod": 80, "cargo.toml": 80,
    "main.py": 70, "app.py": 70, "index.js": 70, "server.js": 70,
    "main.java": 70, "program.cs": 70, "main.go": 70, "index.html": 50,
}
IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv", "env",
    "dist", "build", "target", ".idea", ".vscode", "vendor", "site-packages",
}

MAX_FILE_BYTES = 100_000            # skip files bigger than 100 KB (likely generated)
MAX_FILES = 15                      # send at most 15 files
MAX_CHARS_PER_FILE = 3000           # cut each file after 3000 characters
MAX_TOTAL_CHARS = 12000             # overall cap (~3000-4000 tokens)
MAX_REPO_BYTES = 200 * 1024 * 1024  # refuse repos over 200 MB (after clone)


class RepoError(Exception):
    """Error with a friendly message and an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def cleanup(path) -> None:
    """Delete the cloned folder (Windows needs read-only flags removed first)."""
    path = Path(path)
    if not path.exists():
        return

    def _on_error(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=_on_error)


def clone_repo(repo_url: str) -> Path:
    """Shallow-clone (latest commit only = fast) into temp_repos/<random-id>."""
    TEMP_DIR.mkdir(exist_ok=True)
    target = TEMP_DIR / uuid.uuid4().hex
    try:
        Repo.clone_from(
            repo_url,
            str(target),
            depth=1,
            env={"GIT_TERMINAL_PROMPT": "0"},  # never ask for a password
        )
    except GitCommandError as e:
        cleanup(target)
        text = str(e).lower()
        if any(k in text for k in ("not found", "could not read username",
                                   "authentication", "terminal prompts disabled")):
            raise RepoError(
                "Repository not found, or it is private. Only public repositories are supported.",
                404,
            )
        raise RepoError("Git clone failed. Check your internet connection and the URL.", 502)
    except Exception:
        cleanup(target)
        raise RepoError("Could not clone the repository (is Git installed?).", 500)
    return target


def _priority(rel_path: Path) -> int:
    """Higher score = more important file."""
    name = rel_path.name.lower()
    score = SPECIAL_FILES.get(name, 10)
    if "src" in [p.lower() for p in rel_path.parts[:-1]]:
        score += 20
    score -= len(rel_path.parts)  # files nearer the root matter more
    if "test" in str(rel_path).lower():
        score -= 15               # tests are less useful for explaining the project
    return score


def _read_text(path: Path):
    """Read a file as text. Returns None for binary/unreadable files."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(MAX_CHARS_PER_FILE + 1)
    except OSError:
        return None
    if "\x00" in content:  # binary file
        return None
    return content


def collect_code(repo_path: Path) -> dict:
    """Return {'tree': '...', 'files': [(relative_path, content), ...]}."""
    candidates = []
    total_bytes = 0

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]  # skip junk folders
        for filename in filenames:
            full = Path(root) / filename
            try:
                size = full.stat().st_size
            except OSError:
                continue
            total_bytes += size
            if total_bytes > MAX_REPO_BYTES:
                raise RepoError("Repository is too large (over 200 MB).", 413)
            is_code = full.suffix.lower() in CODE_EXTENSIONS
            is_special = filename.lower() in SPECIAL_FILES
            if (is_code or is_special) and size <= MAX_FILE_BYTES:
                candidates.append(full.relative_to(repo_path))

    if not candidates:
        raise RepoError(
            "No supported source-code files found (empty repository or unsupported languages).",
            422,
        )

    candidates.sort(key=_priority, reverse=True)

    selected, used = [], 0
    for rel in candidates:
        if len(selected) >= MAX_FILES or used >= MAX_TOTAL_CHARS:
            break
        content = _read_text(repo_path / rel)
        if not content or not content.strip():
            continue
        content = content[:MAX_CHARS_PER_FILE]
        content = content[: MAX_TOTAL_CHARS - used]
        selected.append((rel.as_posix(), content))
        used += len(content)

    if not selected:
        raise RepoError("Source files were found but they were empty or unreadable.", 422)

    tree = "\n".join(p.as_posix() for p in sorted(candidates)[:60])
    return {"tree": tree, "files": selected}
