import re
from pydantic import BaseModel, field_validator

# Accepts only: https://github.com/<user>/<repo>  (optional .git or trailing /)
GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?$")


class ExplainRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def check_github_url(cls, value: str) -> str:
        value = value.strip()
        if not GITHUB_URL_PATTERN.match(value):
            raise ValueError(
                "Invalid GitHub URL. Use the format: https://github.com/username/repository"
            )
        return value


class ExplainResponse(BaseModel):
    explanation: str
