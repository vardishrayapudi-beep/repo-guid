"""GitHub API client providing validated URL parsing, bounded tree retrieval, and sanitized error handling."""

from __future__ import annotations

import datetime
import os
import re
from typing import Any
from urllib.parse import urlsplit

import requests

from models import RepoData, RepoGuideError, TrendingRepo

# Ingestion and rate-control limits
MAX_TREE_DEPTH = 3
MAX_TREE_ITEMS = 120
MAX_MANIFEST_SNIPPET_CHARS = 1000
MAX_MANIFESTS_TO_FETCH = 2
MAX_FILE_SIZE_BYTES = 50 * 1024  # 50 KB
MAX_README_CHARS = 3000

# GitHub validation patterns
# Username/Org: 1-39 chars, alphanumeric and single hyphens, cannot start or end with a hyphen
GITHUB_OWNER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")
# Repository: 1-100 chars, alphanumeric, '.', '_', '-' (not '.' or '..')
GITHUB_REPO_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")


def parse_github_url(url: str | None) -> tuple[str, str] | tuple[None, None]:
    """
    Parses and strictly validates a GitHub repository URL, returning (owner, repo).

    Accepts:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - github.com/owner/repo/
    - URLs with query strings or fragments (?tab=readme, #readme)

    Rejects:
    - Subpaths like /issues/123, /pull/4, /releases, /blob/main/file.py
    - Non-GitHub hosts (gitlab.com, bitbucket.org, etc.)
    - Incomplete paths (https://github.com/owner)
    - Invalid owner/repo names containing forbidden characters
    - Malformed or blank text

    Returns (None, None) on any validation failure.
    """
    if not url or not isinstance(url, str):
        return None, None

    cleaned = url.strip()
    if not cleaned:
        return None, None

    # Prepend scheme if missing for clean urlsplit parsing
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = "https://" + cleaned

    try:
        parsed = urlsplit(cleaned)
    except (ValueError, AttributeError):
        return None, None

    # Validate scheme
    if parsed.scheme.lower() not in ("http", "https"):
        return None, None

    # Validate netloc (strip port if present)
    host = parsed.netloc.split(":")[0].lower()
    if host not in ("github.com", "www.github.com"):
        return None, None

    # Parse path segments
    path_segments = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_segments) != 2:
        return None, None

    owner, raw_repo = path_segments[0], path_segments[1]

    # Normalize trailing .git
    repo = raw_repo[:-4] if raw_repo.endswith(".git") else raw_repo

    if not repo or repo in (".", ".."):
        return None, None

    # Strict name format validation
    if not GITHUB_OWNER_REGEX.match(owner):
        return None, None

    if not GITHUB_REPO_REGEX.match(repo):
        return None, None

    return owner, repo


def get_github_token() -> str | None:
    """
    Safely retrieves optional GitHub token from st.secrets or environment variable.
    Never exposes token in UI, error logs, or terminal output.
    """
    token = None
    # 1. Try streamlit secrets if Streamlit is in the runtime environment
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GITHUB_TOKEN" in st.secrets:
                token = str(st.secrets["GITHUB_TOKEN"])
            elif "GH_TOKEN" in st.secrets:
                token = str(st.secrets["GH_TOKEN"])
    except (KeyError, AttributeError, FileNotFoundError, ImportError):
        pass

    # 2. Try environment variables
    if not token:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    if token and isinstance(token, str):
        cleaned = token.strip()
        return cleaned if cleaned else None
    return None


def get_github_headers(token: str | None = None) -> tuple[dict[str, str], bool]:
    """
    Constructs GitHub API request headers including User-Agent and optional Authorization.
    Returns (headers_dict, is_authenticated).
    """
    active_token = token if token is not None else get_github_token()
    headers = {
        "User-Agent": "RepoGuide-StreamlitApp/2.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if active_token:
        headers["Authorization"] = f"Bearer {active_token}"
        return headers, True
    return headers, False


def format_rate_limit_reset(reset_header: str | None) -> str:
    """Formats the GitHub x-ratelimit-reset epoch timestamp into a human-readable duration."""
    if not reset_header:
        return "in a few minutes"
    try:
        reset_ts = int(reset_header)
        now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        diff_sec = max(0, reset_ts - now_ts)
        if diff_sec < 60:
            return f"in ~{diff_sec} seconds"
        diff_min = (diff_sec + 59) // 60
        reset_time_str = datetime.datetime.fromtimestamp(reset_ts, tz=datetime.timezone.utc).strftime("%H:%M:%S UTC")
        return f"in ~{diff_min} min (at {reset_time_str})"
    except (ValueError, TypeError):
        return "in a few minutes"


def handle_github_error_status(
    response: requests.Response,
    owner: str,
    repo: str,
    is_authenticated: bool,
) -> None:
    """
    Uniformly evaluates GitHub API status codes and raises informative RepoGuideError exceptions.
    Never exposes internal tokens or stack traces to end users.
    """
    if response.status_code == 200:
        return

    if response.status_code == 404:
        raise RepoGuideError(
            f"🔍 Repository '{owner}/{repo}' was not found. Please verify the URL and confirm the repository is public."
        )

    if response.status_code in (403, 429):
        body_snippet = (response.text or "").lower()
        is_rate_limit = "rate limit" in body_snippet or response.headers.get("x-ratelimit-remaining") == "0"
        if is_rate_limit:
            reset_time = format_rate_limit_reset(response.headers.get("x-ratelimit-reset"))
            auth_info = (
                "Authenticated with token (limit: 5,000/hr)"
                if is_authenticated
                else "Unauthenticated (limit: 60/hr)"
            )
            token_tip = (
                ""
                if is_authenticated
                else "\n\n💡 **Tip**: Add a `GITHUB_TOKEN` to `.streamlit/secrets.toml` or your environment to increase your quota to 5,000 requests/hour."
            )
            raise RepoGuideError(
                f"⏱️ **GitHub API Rate Limit Reached**\n\n"
                f"- **Status**: {auth_info}\n"
                f"- **Quota Reset**: Try again {reset_time}"
                f"{token_tip}"
            )
        raise RepoGuideError(f"🔒 Access denied by GitHub (HTTP {response.status_code}).")

    if response.status_code == 401:
        raise RepoGuideError(
            "🔑 GitHub API authentication failed. The configured GITHUB_TOKEN is invalid or expired."
        )

    if response.status_code == 409:
        raise RepoGuideError(f"⚠️ Repository '{owner}/{repo}' is empty or has no commits.")

    if response.status_code >= 500:
        raise RepoGuideError(f"🌐 GitHub service error (HTTP {response.status_code}). Please try again shortly.")

    raise RepoGuideError(f"⚠️ GitHub API returned unexpected status {response.status_code}.")


def fetch_github_repo_data(
    owner: str,
    repo: str,
    token: str | None = None,
    session: requests.Session | None = None,
) -> RepoData:
    """
    Fetches recursive repository structure via Git Trees API, detects key directories & manifests,
    fetches raw manifest snippets and the README with strict boundary limits.
    Captures specific exceptions on optional files, continuing with partial results.
    """
    client = session or requests
    headers, is_authenticated = get_github_headers(token)

    warnings: list[str] = []
    omissions: list[str] = []

    # 1. Fetch Repository Tree via Git Trees API (recursive=1 in a single bounded request)
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    try:
        t_res = client.get(tree_url, headers=headers, timeout=14)
    except requests.exceptions.Timeout:
        raise RepoGuideError("⏱️ GitHub request timed out while fetching repository tree. Please check your network connection.")
    except requests.exceptions.RequestException as e:
        raise RepoGuideError(f"🌐 Network error connecting to GitHub: {e}")

    # If HEAD fails with 404 (e.g. branch rename), try fallback to default branch
    if t_res.status_code == 404:
        meta_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            m_res = client.get(meta_url, headers=headers, timeout=12)
            if m_res.status_code == 200:
                default_branch = m_res.json().get("default_branch", "main")
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
                t_res = client.get(tree_url, headers=headers, timeout=14)
            else:
                handle_github_error_status(m_res, owner, repo, is_authenticated)
        except requests.exceptions.RequestException:
            pass

    handle_github_error_status(t_res, owner, repo, is_authenticated)

    try:
        tree_json = t_res.json()
    except (ValueError, TypeError):
        raise RepoGuideError("⚠️ Invalid response received from GitHub API tree endpoint.")

    raw_tree_items = tree_json.get("tree", []) if isinstance(tree_json, dict) else []
    is_tree_truncated = bool(tree_json.get("truncated", False)) if isinstance(tree_json, dict) else False

    target_manifests = [
        "pyproject.toml", "requirements.txt", "package.json", "package-lock.json",
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile",
        "setup.py", "tsconfig.json", "cargo.toml", "go.mod"
    ]
    target_dir_prefixes = [
        ".github/workflows", "src", "app", "lib", "tests", "test", "docs", "skills"
    ]

    detected_dirs: set[str] = set()
    skill_subfolders: list[str] = []
    top_level_items: list[str] = []
    manifest_candidates: dict[str, int] = {}
    tree_preview_lines: list[str] = []

    total_entries_count = len(raw_tree_items)
    if is_tree_truncated:
        omissions.append("Repository exceeds GitHub Git Tree size limit (truncated by GitHub).")

    for item in raw_tree_items:
        path = item.get("path", "")
        item_type = item.get("type", "blob")
        size = item.get("size", 0) or 0
        parts = path.split("/")
        depth = len(parts)

        # Top-level items
        if depth == 1:
            name_suffix = "/" if item_type == "tree" else ""
            top_level_items.append(f"{path}{name_suffix}")

        # Check key directories
        for prefix in target_dir_prefixes:
            if path == prefix or path.startswith(f"{prefix}/"):
                detected_dirs.add(prefix)

        # Check skill subfolders
        if (path == "skills" or path.startswith("skills/")) and item_type == "tree":
            skill_subfolders.append(path)

        # Check key manifests near root
        filename = parts[-1].lower()
        if depth <= 2 and any(filename == tm.lower() for tm in target_manifests):
            manifest_candidates[path] = size

        # Collect bounded tree preview for the LLM
        if depth <= MAX_TREE_DEPTH and len(tree_preview_lines) < MAX_TREE_ITEMS:
            suffix = "/" if item_type == "tree" else ""
            tree_preview_lines.append(f"{path}{suffix}")

    if len(tree_preview_lines) >= MAX_TREE_ITEMS:
        omissions.append(f"Directory tree preview limited to first {MAX_TREE_ITEMS} items (out of {total_entries_count} total).")
    if any(len(item.get("path", "").split("/")) > MAX_TREE_DEPTH for item in raw_tree_items):
        omissions.append(f"Directory tree view limited to max depth {MAX_TREE_DEPTH}.")

    # 2. Selectively fetch small manifests (up to MAX_MANIFESTS_TO_FETCH, size <= 50KB)
    manifest_snippets: dict[str, str] = {}
    manifest_priority = [
        "pyproject.toml", "package.json", "requirements.txt", "Dockerfile",
        "docker-compose.yml", "Makefile", "setup.py", "tsconfig.json", "cargo.toml", "go.mod"
    ]
    lockfile_names = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "cargo.lock"}
    chosen_manifest_paths: list[str] = []

    for prio in manifest_priority:
        for path in manifest_candidates:
            filename = path.split("/")[-1].lower()
            if filename == prio.lower() and path not in chosen_manifest_paths:
                chosen_manifest_paths.append(path)
                break
        if len(chosen_manifest_paths) >= MAX_MANIFESTS_TO_FETCH:
            break

    for path in manifest_candidates:
        if len(chosen_manifest_paths) >= MAX_MANIFESTS_TO_FETCH:
            break
        filename = path.split("/")[-1].lower()
        if path not in chosen_manifest_paths and filename not in lockfile_names:
            chosen_manifest_paths.append(path)

    for m_path in chosen_manifest_paths:
        m_size = manifest_candidates.get(m_path, 0)
        if m_size > MAX_FILE_SIZE_BYTES:
            omissions.append(f"File '{m_path}' ({m_size // 1024} KB) omitted due to size limit (max {MAX_FILE_SIZE_BYTES // 1024} KB).")
            continue

        raw_content = None
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{m_path}"
        try:
            r_res = client.get(raw_url, timeout=8)
            if r_res.status_code == 200:
                raw_content = r_res.text
            elif r_res.status_code not in (404,):
                warnings.append(f"Could not retrieve raw manifest '{m_path}' (HTTP {r_res.status_code}).")
        except requests.exceptions.Timeout:
            warnings.append(f"Timeout while retrieving manifest '{m_path}'; skipped.")
        except requests.exceptions.RequestException as e:
            warnings.append(f"Network error retrieving manifest '{m_path}': {e}")

        if raw_content is None:
            # Fallback to GitHub contents API
            c_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{m_path}"
            try:
                c_res = client.get(c_url, headers=headers, timeout=10)
                if c_res.status_code == 200:
                    d_url = c_res.json().get("download_url")
                    if d_url:
                        raw_content = client.get(d_url, timeout=8).text
            except (requests.exceptions.RequestException, ValueError, KeyError):
                pass

        if raw_content:
            snippet = raw_content[:MAX_MANIFEST_SNIPPET_CHARS]
            if len(raw_content) > MAX_MANIFEST_SNIPPET_CHARS:
                snippet += f"\n... [truncated to {MAX_MANIFEST_SNIPPET_CHARS} characters]"
            manifest_snippets[m_path] = snippet

    # 3. Fetch README
    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    readme_headers = dict(headers)
    readme_headers["Accept"] = "application/vnd.github.raw"
    readme_text = ""

    try:
        rm_res = client.get(readme_url, headers=readme_headers, timeout=12)
        if rm_res.status_code == 200:
            readme_text = rm_res.text
        elif rm_res.status_code == 404:
            readme_text = "(No README file found in this repository)"
            warnings.append("No README file was found in the repository; continuing analysis using directory structure and manifests.")
        elif rm_res.status_code in (403, 429):
            handle_github_error_status(rm_res, owner, repo, is_authenticated)
        else:
            readme_text = "(Could not fetch README content)"
            warnings.append(f"GitHub returned HTTP {rm_res.status_code} when loading README; proceeding with partial data.")
    except requests.exceptions.Timeout:
        readme_text = "(README retrieval timed out)"
        warnings.append("Network timeout while fetching README; continuing analysis with partial repository data.")
    except requests.exceptions.RequestException as e:
        readme_text = "(README could not be retrieved due to network error)"
        warnings.append(f"Network error while fetching README: {e}")

    if len(readme_text) > MAX_README_CHARS:
        omissions.append(f"README content truncated to first {MAX_README_CHARS} characters (total length: {len(readme_text)}).")
    truncated_readme = readme_text[:MAX_README_CHARS]

    return RepoData(
        owner=owner,
        repo=repo,
        files_list=top_level_items,
        skill_subfolders=skill_subfolders,
        detected_dirs=sorted(detected_dirs),
        detected_manifests=list(manifest_candidates.keys()),
        manifest_snippets=manifest_snippets,
        tree_preview=tree_preview_lines,
        truncated_readme=truncated_readme,
        omissions=omissions,
        warnings=warnings,
        total_entries=total_entries_count,
        is_tree_truncated=is_tree_truncated,
    )


def fetch_trending_repos(
    target_date: str,
    token: str | None = None,
    session: requests.Session | None = None,
) -> list[TrendingRepo]:
    """
    Fetches trending GitHub repositories created in the past 30 days.
    """
    client = session or requests
    headers, is_authenticated = get_github_headers(token)
    url = f"https://api.github.com/search/repositories?q=created:>{target_date}&sort=stars&order=desc&per_page=6"

    try:
        res = client.get(url, headers=headers, timeout=12)
    except requests.exceptions.Timeout:
        raise RepoGuideError("⏱️ GitHub trending search request timed out. Please check your internet connection.")
    except requests.exceptions.RequestException as e:
        raise RepoGuideError(f"🌐 Network error querying trending repositories: {e}")

    handle_github_error_status(res, "trending", "search", is_authenticated)

    try:
        data = res.json()
    except (ValueError, TypeError):
        raise RepoGuideError("⚠️ Unexpected non-JSON response from GitHub trending search API.")

    items = data.get("items", []) if isinstance(data, dict) else []
    results: list[TrendingRepo] = []
    for item in items:
        results.append(
            TrendingRepo(
                full_name=item.get("full_name", ""),
                html_url=item.get("html_url", ""),
                stars=item.get("stargazers_count", 0),
                description=item.get("description") or "No description provided.",
            )
        )
    return results
