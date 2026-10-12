import re
from datetime import date, timedelta
from urllib.parse import urlparse
import requests
import streamlit as st
import ollama

DEFAULT_REPO_URL = "https://github.com/mattpocock/skills"

# Configure page metadata
st.set_page_config(
    page_title="Repo Guide",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_theme():
    """
    Applies a clean 'light grid' developer-event landing page theme:
    - #fafafa page background
    - Dual-layer faint background grids with edge fade masks
    - Monospace typography (JetBrains Mono)
    - High contrast text (#16181d, #3b4252) and signature blue (#0069ff) accents
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

        /* Global Font Enforcement */
        html, body, [class*="css"], .stMarkdown, p, span, div, input, button, select, textarea, label {
            font-family: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace !important;
        }

        /* Base App Background */
        .stApp {
            background-color: #fafafa !important;
            color: #16181d !important;
            min-height: 100vh;
        }

        /* Position content container over the grid */
        [data-testid="stAppViewContainer"] > .main {
            position: relative;
            z-index: 1;
        }

        /* Fixed Background Grid Containers */
        .grid-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }

        /* Faint Base Grid across page (rgba(120, 140, 180, 0.12), ~28px spacing) */
        .grid-layer-main {
            position: absolute;
            inset: 0;
            background-image: 
                repeating-linear-gradient(to right, rgba(120, 140, 180, 0.12) 0px, rgba(120, 140, 180, 0.12) 1px, transparent 1px, transparent 28px),
                repeating-linear-gradient(to bottom, rgba(120, 140, 180, 0.12) 0px, rgba(120, 140, 180, 0.12) 1px, transparent 1px, transparent 28px);
            mask-image: radial-gradient(ellipse at 50% 45%, rgba(0, 0, 0, 1) 35%, rgba(0, 0, 0, 0) 80%);
            -webkit-mask-image: radial-gradient(ellipse at 50% 45%, rgba(0, 0, 0, 1) 35%, rgba(0, 0, 0, 0) 80%);
        }

        /* Accent Grid (soft pink/red rgba(255, 120, 140, 0.14) on right half only) */
        .grid-layer-pink {
            position: absolute;
            top: 0;
            right: 0;
            width: 50%;
            height: 100%;
            background-image: 
                repeating-linear-gradient(to right, rgba(255, 120, 140, 0.14) 0px, rgba(255, 120, 140, 0.14) 1px, transparent 1px, transparent 28px),
                repeating-linear-gradient(to bottom, rgba(255, 120, 140, 0.14) 0px, rgba(255, 120, 140, 0.14) 1px, transparent 1px, transparent 28px);
            mask-image: linear-gradient(to left, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0) 90%),
                        radial-gradient(ellipse at 70% 40%, rgba(0, 0, 0, 1) 20%, rgba(0, 0, 0, 0) 85%);
            -webkit-mask-image: linear-gradient(to left, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0) 90%),
                                radial-gradient(ellipse at 70% 40%, rgba(0, 0, 0, 1) 20%, rgba(0, 0, 0, 0) 85%);
        }

        /* Typography & Body Text */
        body, p, li, span {
            color: #3b4252;
            line-height: 1.7;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #16181d !important;
            letter-spacing: -0.02em;
        }

        /* Main Header Layout */
        .main-header {
            text-align: center;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            position: relative;
            z-index: 1;
        }

        .main-title {
            font-size: 2.7rem;
            font-weight: 800;
            color: #16181d !important;
            background: none !important;
            -webkit-text-fill-color: initial !important;
            margin-bottom: 0.2rem;
            letter-spacing: -0.03em;
        }

        .main-subtitle {
            color: #0069ff !important;
            font-size: 0.95rem;
            font-weight: 700;
            margin-bottom: 0.85rem;
            letter-spacing: -0.01em;
        }

        /* Powered Badge: Clean Monospace Pill */
        .powered-badge {
            display: inline-block;
            background: #eef2f7 !important;
            border: 1px solid #d5dbe6 !important;
            border-radius: 9999px !important;
            padding: 0.28rem 0.85rem !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            color: #3b4252 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 1.25rem !important;
            box-shadow: none !important;
        }

        /* Primary Button: Solid Blue (#0069ff), Square Corners (2px), Bold */
        div.stButton > button[kind="primary"] {
            background-color: #0069ff !important;
            background: #0069ff !important;
            color: #ffffff !important;
            border: 1px solid #0069ff !important;
            border-radius: 2px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            transition: background-color 0.15s ease, border-color 0.15s ease !important;
            transform: none !important;
        }

        div.stButton > button[kind="primary"]:hover {
            background-color: #0050cc !important;
            background: #0050cc !important;
            border-color: #0050cc !important;
            color: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Secondary Buttons: White Background, 1px #d5dbe6 Border, Square-ish Corners */
        div.stButton > button,
        div[data-testid="stDownloadButton"] > button {
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #16181d !important;
            border: 1px solid #d5dbe6 !important;
            border-radius: 3px !important;
            font-weight: 500 !important;
            box-shadow: none !important;
            transition: border-color 0.15s ease, color 0.15s ease !important;
            transform: none !important;
        }

        div.stButton > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            border-color: #0069ff !important;
            color: #0069ff !important;
            background-color: #ffffff !important;
            background: #ffffff !important;
            transform: none !important;
            box-shadow: none !important;
        }

        /* Inputs, Selectboxes, Text Areas: 4px Radius, Blue Focus Ring */
        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stTextArea"] textarea {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid #d5dbe6 !important;
            border-radius: 4px !important;
            color: #16181d !important;
            box-shadow: none !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #0069ff !important;
            box-shadow: 0 0 0 2px rgba(0, 105, 255, 0.20) !important;
        }

        /* Sidebar: #f4f6fa background with 1px right border #e1e6ef */
        [data-testid="stSidebar"] {
            background-color: #f4f6fa !important;
            background: #f4f6fa !important;
            border-right: 1px solid #e1e6ef !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"] * {
            color: #16181d;
        }

        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stCaption {
            color: #5c6370 !important;
        }

        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background-color: #ffffff !important;
            border: 1px solid #d5dbe6 !important;
            border-radius: 4px !important;
        }

        /* Guide Output Card */
        .guide-card {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid #e1e6ef !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 12px rgba(20, 30, 60, 0.06) !important;
            padding: 1.75rem !important;
            margin-top: 1.25rem !important;
            margin-bottom: 1.5rem !important;
            color: #16181d !important;
            line-height: 1.7;
        }

        /* Section Headings inside Guide: Near-Black with Blue Left Border */
        .guide-card h1, .guide-card h2, .guide-card h3, .guide-card h4 {
            color: #16181d !important;
            border-left: 3px solid #0069ff !important;
            padding-left: 0.65rem !important;
            margin-top: 1.35rem !important;
            margin-bottom: 0.75rem !important;
            font-weight: 700 !important;
        }

        /* Summary Box */
        .repo-summary-box {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid #e1e6ef !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 8px rgba(20, 30, 60, 0.04) !important;
            padding: 1rem 1.25rem !important;
            margin-bottom: 1.25rem !important;
            color: #16181d !important;
        }

        .repo-summary-box a {
            color: #0069ff !important;
            font-weight: 600;
            text-decoration: none;
        }

        .repo-summary-box a:hover {
            text-decoration: underline;
        }

        /* Suggestion Section Wrapper */
        .suggestions-wrapper {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid #e1e6ef !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 8px rgba(20, 30, 60, 0.04) !important;
            padding: 1.25rem 1.4rem !important;
            margin-top: 1.25rem !important;
            margin-bottom: 1.5rem !important;
        }

        /* Expanders & Alerts matching Light Style */
        div[data-testid="stExpander"] {
            background-color: #ffffff !important;
            background: #ffffff !important;
            border: 1px solid #e1e6ef !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 4px rgba(20, 30, 60, 0.04) !important;
            color: #16181d !important;
        }

        div[data-testid="stAlert"] {
            background-color: #f1f4f9 !important;
            background: #f1f4f9 !important;
            border: 1px solid #d5dbe6 !important;
            border-radius: 6px !important;
            color: #16181d !important;
        }

        /* Code Blocks */
        pre, code {
            background-color: #f1f4f9 !important;
            background: #f1f4f9 !important;
            border: 1px solid #e1e6ef !important;
            border-radius: 4px !important;
            color: #0069ff !important;
            font-family: 'JetBrains Mono', monospace !important;
        }

        pre code {
            color: #16181d !important;
        }

        /* Spinner & Captions Contrast */
        div[data-testid="stSpinner"] > div {
            color: #16181d !important;
        }

        .stCaption, caption {
            color: #5c6370 !important;
        }

        label, [data-testid="stWidgetLabel"] p {
            color: #16181d !important;
            font-weight: 600;
        }

        /* Responsive on narrow screens */
        @media (max-width: 768px) {
            .main-title {
                font-size: 2rem !important;
            }
            .main-subtitle {
                font-size: 0.85rem !important;
            }
            .guide-card {
                padding: 1.15rem !important;
            }
            .suggestions-wrapper {
                padding: 1rem !important;
            }
        }
        </style>

        <!-- Fixed Light Background Grid Layers -->
        <div class="grid-backdrop">
            <div class="grid-layer-main"></div>
            <div class="grid-layer-pink"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Apply the Clean Light Grid Theme
apply_theme()


class RepoGuideError(Exception):
    """Custom exception for user-friendly error handling."""
    pass


def get_installed_ollama_models():
    """
    Retrieves installed Ollama models, handling both response formats:
    - Object with .models attribute (each with .model or .name)
    - Dict with 'models' key (each with 'model' or 'name')
    """
    try:
        data = ollama.list()
    except Exception:
        return []

    raw_models = getattr(data, "models", None)
    if raw_models is None and isinstance(data, dict):
        raw_models = data.get("models", [])

    if not raw_models:
        return []

    model_names = []
    for m in raw_models:
        name = None
        if hasattr(m, "model") and m.model:
            name = m.model
        elif hasattr(m, "name") and m.name:
            name = m.name
        elif isinstance(m, dict):
            name = m.get("model") or m.get("name")

        if name and name not in model_names:
            model_names.append(name)

    return model_names


# -----------------------------------------------------------------------------
# SIDEBAR: FEATURE 1 - Model Picker for Different Laptops
# -----------------------------------------------------------------------------
st.sidebar.header("Choose your model")

ram_choice = st.sidebar.selectbox(
    "Pick your laptop RAM:",
    options=["8 GB", "16 GB", "32 GB or more"],
    index=1,
    help="Select your system RAM to see recommended model parameters",
)

if ram_choice == "8 GB":
    st.sidebar.info("💡 **Recommended for 8 GB:** small models, around 1B-3B parameters (e.g., `llama3.2:1b`, `qwen2.5:1.5b`).")
elif ram_choice == "16 GB":
    st.sidebar.info("💡 **Recommended for 16 GB:** models around 3B-4B parameters (`phi4-mini` is the default).")
else:
    st.sidebar.info("💡 **Recommended for 32 GB or more:** models around 7B-8B parameters (e.g., `llama3:8b`, `mistral:7b`).")

installed_models = get_installed_ollama_models()

if installed_models:
    # Default to phi4-mini or phi4-mini:latest if installed
    default_idx = 0
    for idx, m in enumerate(installed_models):
        if m == "phi4-mini" or m.startswith("phi4-mini:"):
            default_idx = idx
            break

    selected_from_dropdown = st.sidebar.selectbox(
        "Installed Ollama models",
        options=installed_models,
        index=default_idx,
        help="Choose from models installed locally in Ollama",
    )
else:
    st.sidebar.warning("⚠️ No models installed in Ollama. Run: `ollama pull phi4-mini` in terminal.")
    selected_from_dropdown = "phi4-mini"

custom_model_input = st.sidebar.text_input(
    "Use another Ollama model name",
    placeholder="e.g., mistral, qwen2.5:3b",
    help="Type any custom model name you have installed in Ollama",
)

# Final selected model priority: custom input overrides selectbox
selected_model = custom_model_input.strip() if custom_model_input.strip() else selected_from_dropdown

# Check if model is missing from installed list
if installed_models and selected_model not in installed_models and not any(m.startswith(f"{selected_model}:") for m in installed_models):
    st.sidebar.warning(f"⚠️ Model `{selected_model}` is not in your installed list.\nTo install, run:\n`ollama pull {selected_model}`")

st.sidebar.caption("💡 Larger models give better answers but run slower on CPU.")


# -----------------------------------------------------------------------------
# MAIN APP HEADER
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="main-header">
        <div class="main-title">Repo Guide</div>
        <div class="main-subtitle">A friendly open-source onboarding guide generator for GitHub repositories</div>
        <div class="powered-badge">Powered by {selected_model} (open-weight, running locally via Ollama)</div>
    </div>
    """,
    unsafe_allow_html=True,
)


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
def analyze_repo_cached(owner: str, repo: str, model_name: str):
    """
    Cached analysis of a repository using GitHub API and local Ollama model.
    Includes model_name in arguments so each model gets its own cached result.
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

    # 3. Call local model via Ollama
    try:
        response = ollama.chat(
            model=model_name,
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
            raise RepoGuideError(f"📦 Model '{model_name}' was not found in Ollama. Please run `ollama pull {model_name}` in your terminal to download and install it.")
        raise RepoGuideError(f"❌ Ollama model error: {e}")
    except Exception as e:
        err_msg = str(e)
        if any(k in err_msg.lower() for k in ["connection", "connect", "refused"]):
            raise RepoGuideError("🔌 Ollama is not running. Please make sure the Ollama application is running on your machine (`ollama serve`).")
        elif "not found" in err_msg.lower():
            raise RepoGuideError(f"📦 Model '{model_name}' was not found in Ollama. Run: `ollama pull {model_name}`")
        raise RepoGuideError(f"❌ Failed to run {model_name} via Ollama: {err_msg}")

    return {
        "files_list": files_list,
        "skill_subfolders": skill_subfolders,
        "truncated_readme": truncated_readme,
        "guide_content": guide_content,
    }


@st.cache_data(ttl=3600)
def fetch_trending_repos(target_date: str):
    """
    Fetches trending GitHub repositories created in the past 30 days.
    Cached for 1 hour with st.cache_data(ttl=3600).
    """
    headers = {
        "User-Agent": "RepoGuide-StreamlitApp",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/search/repositories?q=created:>{target_date}&sort=stars&order=desc&per_page=6"
    try:
        res = requests.get(url, headers=headers, timeout=12)
    except requests.exceptions.Timeout:
        raise RepoGuideError("⏱️ GitHub trending search request timed out. Please check your internet connection.")
    except requests.exceptions.RequestException as e:
        raise RepoGuideError(f"🌐 Network error querying trending repositories: {e}")

    if res.status_code in (403, 429):
        raise RepoGuideError("⏱️ GitHub API rate limit reached for search queries. Please try again later.")
    elif res.status_code != 200:
        raise RepoGuideError(f"⚠️ GitHub search returned unexpected status code {res.status_code}.")

    data = res.json()
    items = data.get("items", [])
    results = []
    for item in items:
        results.append({
            "full_name": item.get("full_name", ""),
            "html_url": item.get("html_url", ""),
            "stars": item.get("stargazers_count", 0),
            "description": item.get("description") or "No description provided.",
        })
    return results


# -----------------------------------------------------------------------------
# STATE MANAGEMENT & CALLBACKS
# -----------------------------------------------------------------------------
if "repo_input_url" not in st.session_state:
    st.session_state.repo_input_url = DEFAULT_REPO_URL

if "trigger_run" not in st.session_state:
    st.session_state.trigger_run = False

if "show_trending" not in st.session_state:
    st.session_state.show_trending = False


def select_and_run_repo(target_url: str):
    """Callback to reliably set the URL in session state and trigger analysis."""
    st.session_state.repo_input_url = target_url
    st.session_state.trigger_run = True


def toggle_trending():
    st.session_state.show_trending = True


# -----------------------------------------------------------------------------
# MAIN INPUT SECTION
# -----------------------------------------------------------------------------
repo_url = st.text_input(
    "GitHub Repository URL",
    key="repo_input_url",
    placeholder="https://github.com/owner/repository",
    help="Paste the URL of any public GitHub repository",
)

col_act1, col_act2 = st.columns([2, 1])
with col_act1:
    analyze_clicked = st.button("Generate Beginner Guide →", type="primary", use_container_width=True)
with col_act2:
    st.button("Try the example repo", on_click=select_and_run_repo, args=(DEFAULT_REPO_URL,), use_container_width=True)


# -----------------------------------------------------------------------------
# FEATURE 2: REPO SUGGESTIONS
# -----------------------------------------------------------------------------
st.markdown('<div class="suggestions-wrapper">', unsafe_allow_html=True)
st.markdown("### 💡 Need ideas? Try these repos")

curated_repos = [
    ("Skills (mattpocock/skills)", "https://github.com/mattpocock/skills"),
    ("Ollama (ollama/ollama)", "https://github.com/ollama/ollama"),
    ("Streamlit (streamlit/streamlit)", "https://github.com/streamlit/streamlit"),
    ("MarkItDown (microsoft/markitdown)", "https://github.com/microsoft/markitdown"),
    ("llama.cpp (ggml-org/llama.cpp)", "https://github.com/ggml-org/llama.cpp"),
]

cur_cols = st.columns(len(curated_repos))
for idx, (label, c_url) in enumerate(curated_repos):
    with cur_cols[idx]:
        st.button(
            label,
            key=f"curated_{idx}",
            on_click=select_and_run_repo,
            args=(c_url,),
            use_container_width=True,
        )

# Trending Repositories Section
st.write("")
col_trend_btn, _ = st.columns([1, 2])
with col_trend_btn:
    st.button("🔥 Find trending new repos", on_click=toggle_trending, use_container_width=True)

if st.session_state.show_trending:
    st.markdown("#### 🔥 Trending New Repositories (Past 30 Days)")
    date_30_days_ago = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        trending_list = fetch_trending_repos(date_30_days_ago)
        if not trending_list:
            st.info("No repositories found for this period.")
        else:
            for t_idx, item in enumerate(trending_list):
                t_col1, t_col2 = st.columns([1, 2])
                with t_col1:
                    st.button(
                        f"⭐ {item['stars']:,} • {item['full_name']}",
                        key=f"trending_item_{t_idx}",
                        on_click=select_and_run_repo,
                        args=(item["html_url"],),
                        use_container_width=True,
                    )
                with t_col2:
                    st.caption(item["description"])
    except RepoGuideError as e:
        st.warning(str(e))
    except Exception as e:
        st.warning(f"⚠️ Could not load trending repositories: {e}")

st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# EXECUTION & OUTPUT
# -----------------------------------------------------------------------------
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
                # Spinner uses selected model dynamically
                with st.spinner(f"Running {selected_model} locally..."):
                    result = analyze_repo_cached(owner, repo, selected_model)

                st.success(f"Guide successfully generated for **{owner}/{repo}** using **{selected_model}**!")

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
                        <strong>Model used:</strong> {selected_model}<br/>
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

                # Beginner Guide Output inside Light Theme Card
                st.markdown('<div class="guide-card">', unsafe_allow_html=True)
                st.subheader(f"📖 Beginner Guide: {owner}/{repo}")
                st.markdown(guide_content)
                st.markdown('</div>', unsafe_allow_html=True)

                # Download Helper
                st.download_button(
                    label="📥 Download Guide as Markdown",
                    data=guide_content,
                    file_name=f"{repo}_{selected_model.replace(':', '_')}_guide.md",
                    mime="text/markdown",
                )

            except RepoGuideError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
