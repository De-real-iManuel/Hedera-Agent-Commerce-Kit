"""
hack/audit/github.py
---------------------
GithubFileFetcher — pulls a single file from a GitHub repository via the
raw content API (no clone, no auth required for public repos).

Handles:
  * Parsing user/repo from a variety of URL formats
  * Trying `main` then `master` as the default branch
  * Optional GITHUB_TOKEN header for higher rate limits
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import httpx


_REPO_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+?)(?:\.git)?/?$"
)
_BLOB_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)"
)


@dataclass
class FetchedFile:
    owner: str
    repo: str
    branch: str
    path: str
    content: str
    url: str
    status: int


class GithubFileFetcher:
    """Fetch a single text file from a public GitHub repo via raw.githubusercontent.com."""

    def __init__(self, token: str = "", timeout: float = 15.0) -> None:
        self._token = token.strip()
        self._timeout = timeout

    async def fetch(
        self,
        repo_url: str,
        path: str,
        branch: Optional[str] = None,
    ) -> Optional[FetchedFile]:
        """Return a FetchedFile or None if the file can't be retrieved."""
        parsed = self._parse(repo_url)
        if parsed is None:
            return None
        owner, repo, url_branch, url_path = parsed
        # Explicit branch > URL-embedded branch > sensible defaults
        candidates: list[tuple[str, str]] = []
        target_path = url_path or path
        if branch:
            candidates.append((branch, target_path))
        elif url_branch:
            candidates.append((url_branch, target_path))
        else:
            candidates.append(("main", target_path))
            candidates.append(("master", target_path))

        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            for br, p in candidates:
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{p}"
                try:
                    resp = await client.get(url)
                except httpx.HTTPError:
                    continue
                if resp.status_code == 200:
                    return FetchedFile(
                        owner=owner,
                        repo=repo,
                        branch=br,
                        path=p,
                        content=resp.text,
                        url=url,
                        status=200,
                    )
        return None

    # ─── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse(repo_url: str) -> Optional[tuple[str, str, str, str]]:
        """Return (owner, repo, branch, path) — branch/path may be empty."""
        url = repo_url.strip()
        if not url:
            return None
        # blob URL with branch + path
        m = _BLOB_RE.search(url)
        if m:
            return (m["owner"], m["repo"], m["branch"], m["path"])
        # bare repo URL
        m = _REPO_RE.search(url)
        if m:
            return (m["owner"], m["repo"], "", "")
        return None
