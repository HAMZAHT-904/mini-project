from fastapi import FastAPI, HTTPException

from github_processor import RepoError, cleanup, clone_repo, collect_code
from llm_service import LLMError, explain_with_llm
from models import ExplainRequest, ExplainResponse

app = FastAPI(title="GitHub Repository Code Explainer")


@app.get("/")
def health():
    return {"status": "backend running"}


@app.post("/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest):
    repo_path = None
    try:
        repo_path = clone_repo(request.repo_url)      # 1. clone
        data = collect_code(repo_path)                # 2. find + read code (text only)
        explanation = explain_with_llm(               # 3. local LLM explains
            request.repo_url, data["tree"], data["files"]
        )
        return ExplainResponse(explanation=explanation)
    except (RepoError, LLMError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    finally:
        if repo_path:
            cleanup(repo_path)                        # always delete the clone
