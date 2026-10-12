import re
from urllib.parse import urlparse
import requests
import streamlit as st
import ollama

DEFAULT_REPO_URL = "https://github.com/mattpocock/skills"

# Configure page metadata
st.set_page_config(
    page_title="Repo Guide",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom styles for clean, modern aesthetics
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .main-header {
        text-align: center;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
    }

    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .main-subtitle {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 0.75rem;
    }

    .powered-badge {
        display: inline-block;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #cbd5e1;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-bottom: 1.5rem;
    }

    .repo-summary-box {
        background: #f8fafc;
        border-radius: 8px;
        padding: 0.85rem 1.15rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# App Header
st.markdown(
    """
    <div class="main-header">
        <div class="main-title">🧭 Repo Guide</div>
        <div class="main-subtitle">A friendly open-source onboarding guide generator for GitHub repositories</div>
        <div class="powered-badge">Powered by phi4-mini (open-weight, running locally via Ollama)</div>
    </div>
    """,
    unsafe_allow_html=True,
)


class RepoGuideError(Exception):
    """Custom exception for user-friendly error handling."""
    pass


def parse_github_url(url: str):
    """
    Parses and validates a GitHub repository URL, returning (owner, repo).
    Returns (None, None) if invalid.
    """
    url = url.strip()
    if not url:
        return None, None

    if not re.match(r"^https?://", url):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return None, None

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        return None, None

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        return None, None

    owner = path_parts[0]
    repo = path_parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]

    # Validate characters typical for GitHub user and repo names
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", owner) or not re.match(r"^[a-zA-Z0-9_\-\.]+$", repo):
        return None, None

    return owner, repo


def fetch_github_repo_data(owner: str, repo: str):
    """
    Fetches top-level contents, subfolders inside main skills folder(s), and the README.
    """
    headers = {
        "User-Agent": "RepoGuide-StreamlitApp",
        "Accept": "application/vnd.github.v3+json",
    }

    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

    # 1. Fetch top-level file and folder list
    try:
        c_res = requests.get(contents_url, headers=headers, timeout=12)
    except requests.exceptions.Timeout:
        raise RepoGuideError("⏱️ GitHub request timed out. Please check your internet connection and try again.")
    except requests.exceptions.RequestException as e:
        raise RepoGuideError(f"🌐 Network error connecting to GitHub: {e}")

    if c_res.status_code == 404:
        raise RepoGuideError(f"🔍 Repository '{owner}/{repo}' not found. Please ensure the repository is public and the URL is spelled correctly.")
    elif c_res.status_code in (403, 429):
        raise RepoGuideError("⏱️ GitHub API rate limit reached (unauthenticated requests are limited to 60/hour). Please try again later.")
    elif c_res.status_code != 200:
        raise RepoGuideError(f"⚠️ GitHub API returned unexpected status code {c_res.status_code}: {c_res.text}")

    contents_json = c_res.json()
    if not isinstance(contents_json, list):
        raise RepoGuideError("⚠️ Unexpected repository structure received from GitHub.")

    files_list = []
    skills_target_dirs = []
    for item in contents_json:
        name = item.get("name", "")
        item_type = item.get("type", "file")
        if item_type == "dir":
            files_list.append(f"{name}/")
            if "skill" in name.lower():
                skills_target_dirs.append(name)
        else:
            files_list.append(name)

    # 2. Check for skills subfolders inside main skills folder(s)
    skill_subfolders = []
    for s_dir in skills_target_dirs:
        try:
            s_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{s_dir}"
            s_res = requests.get(s_url, headers=headers, timeout=10)
            if s_res.status_code == 200 and isinstance(s_res.json(), list):
                for sub_item in s_res.json():
                    if sub_item.get("type") == "dir":
                        sub_path = f"{s_dir}/{sub_item['name']}"
                        skill_subfolders.append(sub_path)
                        # Check one level deeper for categorized skills (e.g., skills/engineering/code-review)
                        try:
                            nested_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{sub_path}"
                            nested_res = requests.get(nested_url, headers=headers, timeout=10)
                            if nested_res.status_code == 200 and isinstance(nested_res.json(), list):
                                for nested in nested_res.json():
                                    if nested.get("type") == "dir":
                                        skill_subfolders.append(f"{sub_path}/{nested['name']}")
                        except Exception:
                            pass
        except Exception:
            pass

    # 3. Fetch README
    readme_headers = {
        "User-Agent": "RepoGuide-StreamlitApp",
        "Accept": "application/vnd.github.raw",
    }
    readme_text = ""
    try:
        r_res = requests.get(readme_url, headers=readme_headers, timeout=12)
        if r_res.status_code == 200:
            readme_text = r_res.text
        elif r_res.status_code == 404:
            readme_text = "(No README file found in this repository)"
        elif r_res.status_code in (403, 429):
            raise RepoGuideError("⏱️ GitHub API rate limit reached while fetching README. Please try again later.")
        else:
            readme_text = "(Could not fetch README content)"
    except requests.exceptions.RequestException:
        readme_text = "(Could not fetch README content due to a network error)"

    # Truncate the README to the first 3000 characters
    truncated_readme = readme_text[:3000]

    return files_list, skill_subfolders, truncated_readme


@st.cache_data(show_spinner=False)
def analyze_repo_cached(owner: str, repo: str):
    """
    Cached analysis of a repository using GitHub API and local phi4-mini via Ollama.
    Cached via st.cache_data so repeated queries for the same repo are instant.
    """
    # 1. Fetch repo data
    files_list, skill_subfolders, truncated_readme = fetch_github_repo_data(owner, repo)

    # 2. Prepare prompt
    files_formatted = "\n".join([f"- {f}" for f in files_list]) if files_list else "(None)"

    skills_section = ""
    if skill_subfolders:
        skills_section = (
            "\nSubfolders inside the main skills folder(s):\n"
            + "\n".join([f"- {sf}" for sf in skill_subfolders])
            + "\n"
        )

    prompt = f"""You are Repo Guide, an open-source mentor helping new contributors understand this codebase. Always respond in English.

Analyze the GitHub repository '{owner}/{repo}'.

Top-Level Files and Directories:
{files_formatted}
{skills_section}
README Content (truncated to first 3000 characters):
\"\"\"
{truncated_readme}
\"\"\"

Important guidance: This repo may contain Markdown instruction files (skills) for AI coding agents rather than runnable app code. If so, explain what the skills do and how to install or use them, instead of how to run an app.

Please produce a beginner guide with exactly the following four sections:
1) What the project does: Explain the core purpose, key features, and target audience in simple, beginner-friendly terms.
2) How to run it: Provide practical setup and execution instructions based on the README. If this repo contains Markdown instruction files (skills) for AI coding agents rather than runnable app code, explain what the skills do and how to install or use them, instead of how to run an app.
3) A map of the important folders/files: Explain the role of key directories and files found in this repository, including the skills folders and subfolders if present.
4) Three ideas for a first contribution: Suggest 3 realistic, approachable beginner tasks (such as documentation improvements, proposing a new skill or workflow, adding tests, or refining instructions).

Keep your explanations clear, structured, and welcoming for newcomers."""

    # 3. Call local phi4-mini via Ollama
    try:
        response = ollama.chat(
            model="phi4-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "num_ctx": 4096,
            },
        )

        if hasattr(response, "message") and hasattr(response.message, "content"):
            guide_content = response.message.content
        elif isinstance(response, dict) and "message" in response:
            guide_content = response["message"].get("content", "")
        else:
            guide_content = str(response)

    except ollama.ResponseError as e:
        if e.status_code == 404 or "not found" in str(e).lower():
            raise RepoGuideError("📦 Model 'phi4-mini' was not found in Ollama. Please run `ollama run phi4-mini` in your terminal to download and install it.")
        raise RepoGuideError(f"❌ Ollama model error: {e}")
    except Exception as e:
        err_msg = str(e)
        if "connection" in err_msg.lower() or "connect" in err_msg.lower() or "refused" in err_msg.lower():
            raise RepoGuideError("🔌 Ollama is not running. Please make sure the Ollama application is running on your machine (`ollama serve`).")
        raise RepoGuideError(f"❌ Failed to run phi4-mini via Ollama: {err_msg}")

    return {
        "files_list": files_list,
        "skill_subfolders": skill_subfolders,
        "truncated_readme": truncated_readme,
        "guide_content": guide_content,
    }


# State management for URL input and trigger
if "repo_input_url" not in st.session_state:
    st.session_state.repo_input_url = DEFAULT_REPO_URL

if "trigger_run" not in st.session_state:
    st.session_state.trigger_run = False


def on_try_example_click():
    st.session_state.repo_input_url = DEFAULT_REPO_URL
    st.session_state.trigger_run = True


# URL Input (pre-filled with default value, editable by the user)
repo_url = st.text_input(
    "GitHub Repository URL",
    key="repo_input_url",
    placeholder="https://github.com/owner/repository",
    help="Paste the URL of any public GitHub repository",
)

col_act1, col_act2 = st.columns([2, 1])
with col_act1:
    analyze_clicked = st.button("Generate Beginner Guide 🚀", type="primary", use_container_width=True)
with col_act2:
    st.button("Try the example repo", on_click=on_try_example_click, use_container_width=True)

should_run = analyze_clicked or st.session_state.trigger_run
if should_run:
    # Reset trigger flag
    st.session_state.trigger_run = False

    target_url = st.session_state.repo_input_url.strip()
    if not target_url:
        st.error("⚠️ Please enter a GitHub repository URL.")
    else:
        owner, repo = parse_github_url(target_url)
        if not owner or not repo:
            st.error("⚠️ Invalid GitHub URL. Please enter a valid public repository URL (e.g., https://github.com/mattpocock/skills).")
        else:
            try:
                # Show spinner while phi4-mini and data pipeline run
                with st.spinner("Running phi4-mini locally..."):
                    result = analyze_repo_cached(owner, repo)

                st.success(f"Guide successfully generated for **{owner}/{repo}**!")

                files_list = result["files_list"]
                skill_subfolders = result["skill_subfolders"]
                truncated_readme = result["truncated_readme"]
                guide_content = result["guide_content"]

                # Repository Summary Box
                skills_badge = f"<br/><strong>Skills subfolders found:</strong> {len(skill_subfolders)}" if skill_subfolders else ""
                st.markdown(
                    f"""
                    <div class="repo-summary-box">
                        <strong>Repository:</strong> <a href="https://github.com/{owner}/{repo}" target="_blank">{owner}/{repo}</a><br/>
                        <strong>Top-level entries:</strong> {len(files_list)} items found{skills_badge}<br/>
                        <strong>README content:</strong> {len(truncated_readme)} characters analyzed (truncated to first 3,000)
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Expandable details for fetched contents & README
                with st.expander("🔍 View Raw Fetched Structure & Truncated README"):
                    st.subheader("Top-Level Files and Directories")
                    st.code("\n".join(files_list), language="text")

                    if skill_subfolders:
                        st.subheader(f"Skills Subfolders ({len(skill_subfolders)} detected)")
                        st.code("\n".join(skill_subfolders), language="text")

                    st.subheader("Truncated README (First 3000 chars)")
                    st.code(truncated_readme, language="markdown")

                # Beginner Guide Output
                st.subheader(f"📖 Beginner Guide: {owner}/{repo}")
                st.markdown(guide_content)

                # Download Helper
                st.download_button(
                    label="📥 Download Guide as Markdown",
                    data=guide_content,
                    file_name=f"{repo}_beginner_guide.md",
                    mime="text/markdown",
                )

            except RepoGuideError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
