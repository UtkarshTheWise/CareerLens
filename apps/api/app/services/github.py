"""Stage 3 (docs/PIPELINE.md): collect a student's public GitHub evidence. No LLM.

`collect(login, db)` returns a `GithubSnapshot`: the profile, up to 50 repos, and for the top 8
non-fork repos their file tree and commit facts. Every HTTP response is cached for 24 h.
Tokens and file contents are never logged.
"""

import hashlib
import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.errors import ApiError
from app.services.cache import cache_get, cache_set

logger = logging.getLogger("careerlens.github")

API = "https://api.github.com"
GRAPHQL_URL = f"{API}/graphql"
CACHE_TTL = timedelta(hours=24)
TIMEOUT_S = 20.0
TOP_REPOS = 8
MAX_REPOS = 50
CALENDAR_WEEKS = 26
MAX_FILE_CHARS = 20_000
RETRY_WAITS_S = (1.0, 2.0)  # network errors and 5xx: two retries
RETRY_202_WAITS_S = (1.0, 2.0, 4.0)  # "still computing" responses: three retries
_REPO_NAME = re.compile(r"[A-Za-z0-9._-]+")

# ---------------------------------------------------------------- queries

OVERVIEW_QUERY = """
query($login: String!) {
  user(login: $login) {
    id login name bio websiteUrl createdAt
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { firstDay contributionDays { date contributionCount } }
      }
    }
    repositories(
      first: 50, ownerAffiliations: OWNER, privacy: PUBLIC,
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      nodes {
        name description url homepageUrl isFork pushedAt createdAt stargazerCount
        licenseInfo { spdxId }
        primaryLanguage { name }
        languages(first: 10) { edges { size node { name } } }
        repositoryTopics(first: 10) { nodes { topic { name } } }
        defaultBranchRef { target { ... on Commit { history(first: 1) { totalCount } } } }
        readme: object(expression: "HEAD:README.md") { ... on Blob { text } }
        readme_lower: object(expression: "HEAD:readme.md") { ... on Blob { text } }
        pkg: object(expression: "HEAD:package.json") { ... on Blob { text } }
        req: object(expression: "HEAD:requirements.txt") { ... on Blob { text } }
        pyproject: object(expression: "HEAD:pyproject.toml") { ... on Blob { text } }
        workflows: object(expression: "HEAD:.github/workflows") { ... on Tree { entries { name } } }
        root: object(expression: "HEAD:") { ... on Tree { entries { name type } } }
      }
    }
  }
}
"""


def commit_facts_query(count: int) -> str:
    """One aliased query for `count` repos: commit totals, authored commits, and commit dates."""
    variables = ["$owner: String!", "$uid: ID!"]
    blocks = []
    for i in range(count):
        variables += [f"$n{i}: String!", f"$s{i}: GitTimestamp!"]
        blocks.append(
            f"""  r{i}: repository(owner: $owner, name: $n{i}) {{
    defaultBranchRef {{ target {{ ... on Commit {{
      total: history(first: 1) {{ totalCount }}
      authored: history(first: 100, author: {{id: $uid}}) {{ totalCount nodes {{ committedDate additions }} }}
      since_created: history(first: 1, author: {{id: $uid}}, since: $s{i}) {{ totalCount }}
      all: history(first: 100) {{ totalCount nodes {{ committedDate additions }} }}
    }} }} }}
  }}"""
        )
    return f"query({', '.join(variables)}) {{\n" + "\n".join(blocks) + "\n}"


def files_query(count: int) -> str:
    variables = ["$owner: String!", "$name: String!"] + [f"$e{i}: String!" for i in range(count)]
    fields = "\n".join(
        f"    f{i}: object(expression: $e{i}) {{ ... on Blob {{ text isBinary }} }}" for i in range(count)
    )
    return (
        f"query({', '.join(variables)}) {{\n  repository(owner: $owner, name: $name) {{\n{fields}\n  }}\n}}"
    )


# ---------------------------------------------------------------- output models


class WeekCount(BaseModel):
    week_start: date
    count: int


class TreeEntry(BaseModel):
    path: str
    size: int = 0


class RepoData(BaseModel):
    """Everything collected about one repository. `tree` is empty for repos outside the top 8."""

    name: str
    url: str
    description: str | None = None
    homepage: str | None = None
    is_fork: bool = False
    created_at: datetime | None = None
    pushed_at: datetime | None = None
    stars: int = 0
    license: str | None = None
    primary_language: str | None = None
    languages: dict[str, int] = Field(default_factory=dict)  # name -> bytes
    topics: list[str] = Field(default_factory=list)
    readme: str = ""
    # root manifests from the overview query: "package.json", "requirements.txt", "pyproject.toml"
    manifests: dict[str, str] = Field(default_factory=dict)
    workflow_files: list[str] = Field(default_factory=list)
    root_entries: list[str] = Field(default_factory=list)
    # file tree (top 8 non-forks only)
    tree: list[TreeEntry] = Field(default_factory=list)
    tree_truncated: bool = False
    detailed: bool = False  # True when the file tree was collected (top 8 non-forks)
    has_commit_facts: bool = False  # True when the commit fields below were collected
    total_commits: int = 0
    authored_commits: int = 0
    authored_since_created: int = 0
    active_span_weeks: float = 0.0
    # share of all added lines that the repo's first commit adds; None if > 100 commits
    first_commit_share: float | None = None


FileFetcher = Callable[[Sequence[str]], dict[str, str]]


class GithubSnapshot(BaseModel):
    login: str
    user_id: str
    name: str | None = None
    bio: str | None = None
    website: str | None = None
    account_created_at: datetime | None = None
    total_contributions: int = 0
    weeks: list[WeekCount] = Field(default_factory=list)  # last 26 weeks, oldest first
    last_active_date: date | None = None
    repos: list[RepoData] = Field(default_factory=list)

    # not serialised: bound to the client that produced the snapshot
    _fetch_files: Callable[[str, Sequence[str]], dict[str, str]] | None = None

    def fetcher(self, repo_name: str) -> FileFetcher:
        """A function that fetches file contents from one repo on demand (cached, capped)."""
        fetch = self._fetch_files
        if fetch is None:
            return lambda paths: {}
        return lambda paths: fetch(repo_name, paths)

    @property
    def detailed_repos(self) -> list[RepoData]:
        return [r for r in self.repos if r.detailed]


# ---------------------------------------------------------------- client


def request_fingerprint(method: str, url: str, body: Any = None) -> str:
    """Stable key of a request: cache key in production, file name in recorded fixtures."""
    payload = json.dumps([method.upper(), url, body], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class GitHubClient:
    """GraphQL + REST access with caching, retries and contract-shaped errors."""

    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        token = (settings or get_settings()).github_token
        if not token:
            raise ApiError(503, "github_not_configured", "GitHub access is not configured on the server")
        self._db = db
        self._sleep = sleep
        self.calls = 0  # real HTTP requests made (cache hits excluded)
        self._http = httpx.Client(
            transport=transport,
            timeout=TIMEOUT_S,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "careerlens-api",
            },
        )

    def close(self) -> None:
        self._http.close()

    # ---- public helpers

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Run a GraphQL query and return `data`. Raises ApiError for failures."""
        body = {"query": query, "variables": variables}
        key = request_fingerprint("POST", GRAPHQL_URL, body)
        cached = cache_get(self._db, key)
        if cached is not None:
            return cached
        payload = self._send("POST", GRAPHQL_URL, body)
        data = self._unwrap_graphql(payload)
        cache_set(self._db, key, "github", data, CACHE_TTL)
        return data

    def rest_get(self, path: str, *, missing_ok: bool = False) -> Any | None:
        """GET a REST path. With `missing_ok`, 404 and 409 (empty repo) return None."""
        url = f"{API}{path}"
        key = request_fingerprint("GET", url)
        cached = cache_get(self._db, key)
        if cached is not None:
            return cached
        payload = self._send("GET", url, None, missing_ok=missing_ok)
        if payload is not None:
            cache_set(self._db, key, "github", payload, CACHE_TTL)
        return payload

    # ---- internals

    @staticmethod
    def _unwrap_graphql(payload: dict[str, Any]) -> dict[str, Any]:
        errors = payload.get("errors") or []
        data = payload.get("data")
        for err in errors:
            kind = err.get("type")
            if kind == "RATE_LIMITED":
                raise ApiError(429, "rate_limited", "GitHub rate limit reached", {"retry_after_s": 60})
            if kind == "NOT_FOUND" and (data is None or data.get("user") is None):
                raise ApiError(404, "github_not_found", "GitHub user not found")
        if data is None:
            logger.warning("github graphql failed: %s", [e.get("type") for e in errors])
            raise ApiError(502, "github_unavailable", "GitHub returned an error")
        if errors:  # partial data (e.g. one repo unreadable): keep going with what we have
            logger.info("github graphql partial errors: %s", [e.get("type") for e in errors])
        return data

    def _rate_limited(self, response: httpx.Response) -> ApiError | None:
        remaining = response.headers.get("x-ratelimit-remaining")
        message = ""
        try:
            message = str(response.json().get("message", "")).lower()
        except ValueError:
            pass
        limited = (
            response.status_code == 429
            or remaining == "0"
            or "rate limit" in message
            or "abuse" in message
            or "retry-after" in response.headers
        )
        if not limited:
            return None
        wait = 60
        if "retry-after" in response.headers:
            wait = int(response.headers["retry-after"])
        elif response.headers.get("x-ratelimit-reset", "").isdigit():
            wait = max(1, int(response.headers["x-ratelimit-reset"]) - int(time.time()))
        return ApiError(429, "rate_limited", "GitHub rate limit reached", {"retry_after_s": wait})

    def _send(self, method: str, url: str, body: Any, *, missing_ok: bool = False) -> Any | None:
        started = time.perf_counter()
        net_retries = list(RETRY_WAITS_S)
        pending_retries = list(RETRY_202_WAITS_S)
        while True:
            self.calls += 1
            try:
                response = self._http.request(method, url, json=body)
            except httpx.HTTPError as exc:
                if net_retries:
                    self._sleep(net_retries.pop(0))
                    continue
                logger.warning("github %s unreachable: %s", method, type(exc).__name__)
                raise ApiError(502, "github_unavailable", "Could not reach GitHub") from exc

            status = response.status_code
            if status == 202:  # GitHub is still computing the answer: ask again shortly
                if pending_retries:
                    self._sleep(pending_retries.pop(0))
                    continue
                raise ApiError(502, "github_unavailable", "GitHub is still preparing this data")
            if status >= 500:
                if net_retries:
                    self._sleep(net_retries.pop(0))
                    continue
                raise ApiError(502, "github_unavailable", "GitHub is having problems")
            if status == 401:
                raise ApiError(503, "github_auth_failed", "The server's GitHub token was rejected")
            if status in (403, 429):
                limited = self._rate_limited(response)
                if limited is not None:
                    raise limited
                raise ApiError(502, "github_unavailable", f"GitHub refused the request (HTTP {status})")
            if status in (404, 409) and missing_ok:
                return None
            if status == 404:
                raise ApiError(404, "github_not_found", "GitHub resource not found")
            if status >= 400:
                raise ApiError(502, "github_unavailable", f"GitHub returned HTTP {status}")
            logger.info(
                "github %s ok status=%d calls_total=%d ms=%d",
                "graphql" if url == GRAPHQL_URL else "rest",
                status,
                self.calls,
                (time.perf_counter() - started) * 1000,
            )
            return response.json()


# ---------------------------------------------------------------- collect

_LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")


def _iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _blob_text(node: dict[str, Any] | None) -> str:
    return ((node or {}).get("text") or "")[:MAX_FILE_CHARS]


def _parse_repo(node: dict[str, Any]) -> RepoData:
    history = ((node.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}
    manifests = {
        name: text
        for name, key in (
            ("package.json", "pkg"),
            ("requirements.txt", "req"),
            ("pyproject.toml", "pyproject"),
        )
        if (text := _blob_text(node.get(key)))
    }
    return RepoData(
        name=node["name"],
        url=node["url"],
        description=node.get("description"),
        homepage=node.get("homepageUrl") or None,
        is_fork=bool(node.get("isFork")),
        created_at=_iso(node.get("createdAt")),
        pushed_at=_iso(node.get("pushedAt")),
        stars=node.get("stargazerCount") or 0,
        license=(node.get("licenseInfo") or {}).get("spdxId"),
        primary_language=(node.get("primaryLanguage") or {}).get("name"),
        languages={e["node"]["name"]: e["size"] for e in (node.get("languages") or {}).get("edges") or []},
        topics=[t["topic"]["name"] for t in (node.get("repositoryTopics") or {}).get("nodes") or []],
        readme=_blob_text(node.get("readme")) or _blob_text(node.get("readme_lower")),
        manifests=manifests,
        workflow_files=[e["name"] for e in (node.get("workflows") or {}).get("entries") or []],
        root_entries=[e["name"] for e in (node.get("root") or {}).get("entries") or []],
        total_commits=history.get("totalCount") or 0,
    )


def _weeks(calendar: dict[str, Any]) -> tuple[list[WeekCount], date | None]:
    weeks = calendar.get("weeks") or []
    parsed = [
        WeekCount(
            week_start=date.fromisoformat(w["firstDay"]),
            count=sum(d["contributionCount"] for d in w["contributionDays"]),
        )
        for w in weeks
    ]
    active_days = [
        date.fromisoformat(d["date"])
        for w in weeks
        for d in w["contributionDays"]
        if d["contributionCount"] > 0
    ]
    return parsed[-CALENDAR_WEEKS:], max(active_days, default=None)


def _apply_commit_facts(repo: RepoData, facts: dict[str, Any] | None) -> None:
    target = ((facts or {}).get("defaultBranchRef") or {}).get("target")
    if not target:
        return
    repo.has_commit_facts = True
    repo.total_commits = target["total"]["totalCount"]
    repo.authored_commits = target["authored"]["totalCount"]
    repo.authored_since_created = target["since_created"]["totalCount"]
    dates = sorted(_iso(n["committedDate"]) for n in target["authored"]["nodes"])
    repo.active_span_weeks = round((dates[-1] - dates[0]).total_seconds() / (7 * 86400), 2) if dates else 0.0
    everything = target["all"]
    if everything["nodes"] and everything["totalCount"] <= len(everything["nodes"]):
        added = [(n["committedDate"], n["additions"]) for n in everything["nodes"]]
        total_added = sum(a for _, a in added)
        first_added = min(added)[1]  # ISO timestamps sort chronologically
        repo.first_commit_share = round(first_added / total_added, 4) if total_added > 0 else None


def _fetch_commit_facts(client: GitHubClient, owner: str, user_id: str, repos: list[RepoData]) -> None:
    if not repos:
        return
    variables: dict[str, Any] = {"owner": owner, "uid": user_id}
    for i, repo in enumerate(repos):
        variables[f"n{i}"] = repo.name
        created = repo.created_at or datetime(2008, 1, 1, tzinfo=UTC)
        variables[f"s{i}"] = created.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = client.graphql(commit_facts_query(len(repos)), variables)
    for i, repo in enumerate(repos):
        _apply_commit_facts(repo, data.get(f"r{i}"))


def fetch_files(client: GitHubClient, owner: str, repo: str, paths: Sequence[str]) -> dict[str, str]:
    """Contents of the given files at HEAD (text only, capped). Missing and binary files are omitted."""
    unique = list(dict.fromkeys(p for p in paths if p))
    out: dict[str, str] = {}
    for start in range(0, len(unique), 20):
        chunk = unique[start : start + 20]
        variables: dict[str, Any] = {"owner": owner, "name": repo}
        variables.update({f"e{i}": f"HEAD:{path}" for i, path in enumerate(chunk)})
        data = client.graphql(files_query(len(chunk)), variables)
        node = data.get("repository") or {}
        for i, path in enumerate(chunk):
            blob = node.get(f"f{i}")
            if blob and not blob.get("isBinary") and blob.get("text") is not None:
                out[path] = blob["text"][:MAX_FILE_CHARS]
    return out


def collect(login: str, db: Session, *, client: GitHubClient | None = None) -> GithubSnapshot:
    """Stage 3. Raises ApiError (github_not_found, rate_limited, github_unavailable, ...)."""
    if not _LOGIN.fullmatch(login or ""):
        raise ApiError(404, "github_not_found", "That is not a valid GitHub username")
    client = client or GitHubClient(db)
    started = time.perf_counter()
    data = client.graphql(OVERVIEW_QUERY, {"login": login})
    user = data.get("user")
    if user is None:
        raise ApiError(404, "github_not_found", "GitHub user not found")
    owner = user["login"]
    repos = [_parse_repo(n) for n in (user["repositories"]["nodes"] or []) if n][:MAX_REPOS]
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks, last_active = _weeks(calendar)

    top = [r for r in repos if not r.is_fork and r.total_commits > 0][:TOP_REPOS]
    for repo in top:
        tree = client.rest_get(f"/repos/{owner}/{repo.name}/git/trees/HEAD?recursive=1", missing_ok=True)
        if tree:
            repo.tree = [
                TreeEntry(path=e["path"], size=e.get("size", 0)) for e in tree["tree"] if e["type"] == "blob"
            ]
            repo.tree_truncated = bool(tree.get("truncated"))
        repo.detailed = True
    forks = [r for r in repos if r.is_fork and r.total_commits > 0][:TOP_REPOS]  # facts only, no tree
    _fetch_commit_facts(client, owner, user["id"], top)
    _fetch_commit_facts(client, owner, user["id"], forks)

    snapshot = GithubSnapshot(
        login=owner,
        user_id=user["id"],
        name=user.get("name"),
        bio=user.get("bio"),
        website=user.get("websiteUrl") or None,
        account_created_at=_iso(user.get("createdAt")),
        total_contributions=calendar["totalContributions"],
        weeks=weeks,
        last_active_date=last_active,
        repos=repos,
    )
    snapshot._fetch_files = lambda repo_name, paths: fetch_files(client, owner, repo_name, paths)
    logger.info(
        "github collect login=%s repos=%d detailed=%d http_calls=%d ms=%d",
        owner, len(repos), len(top), client.calls, (time.perf_counter() - started) * 1000,
    )  # fmt: skip
    return snapshot
