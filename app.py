"""Repo Guide - An interactive Streamlit app generating beginner-friendly onboarding guides for GitHub repositories."""

from __future__ import annotations

import datetime
import html
import streamlit as st

from models import RepoGuideError, RepoData
from github_client import (
    parse_github_url,
    get_github_token,
    fetch_github_repo_data,
    fetch_trending_repos,
)
from ollama_client import (
    get_installed_ollama_models,
    run_ollama_chat,
)
from prompt_builder import build_safe_prompt

DEFAULT_REPO_URL = "https://github.com/mattpocock/skills"

# Configure page metadata
st.set_page_config(
    page_title="Repo Guide",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_theme() -> None:
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


# -----------------------------------------------------------------------------
# CACHED SERVICE CALLS (TTL: 30 min for GitHub, 1 hr for Ollama & Trending)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_github_repo_data_cached(owner: str, repo: str, is_authenticated: bool, refresh_nonce: int = 0) -> RepoData:
    """Fetches GitHub repository structure and content with a 30-minute cache TTL."""
    return fetch_github_repo_data(owner, repo)


@st.cache_data(ttl=3600, show_spinner=False)
def generate_guide_cached(owner: str, repo: str, model_name: str, cache_digest: str, refresh_nonce: int = 0) -> dict:
    """
    Coordinates GitHub data fetching, safe prompt construction, and Ollama generation.
    Cached for 1 hour.
    """
    token_present = get_github_token() is not None
    data = fetch_github_repo_data_cached(owner, repo, token_present, refresh_nonce)

    system_prompt, user_prompt = build_safe_prompt(owner, repo, data)
    guide_content = run_ollama_chat(model_name, system_prompt, user_prompt)

    return {
        "data": data,
        "guide_content": guide_content,
    }


@st.cache_data(ttl=3600)
def fetch_trending_repos_cached(target_date: str, is_authenticated: bool, refresh_nonce: int = 0) -> list[dict]:
    """Fetches trending repositories with a 1-hour cache TTL."""
    trending_models = fetch_trending_repos(target_date)
    return [item.to_dict() for item in trending_models]


# -----------------------------------------------------------------------------
# SIDEBAR: MODEL PICKER FOR LAPTOPS & REPO SETTINGS
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
    st.sidebar.warning("⚠️ No models found in Ollama.\nTo install the recommended model, run:\n`ollama pull phi4-mini`")
    selected_from_dropdown = "phi4-mini"

custom_model_input = st.sidebar.text_input(
    "Use another Ollama model name",
    placeholder="e.g., mistral, qwen2.5:3b",
    help="Type any custom model name you have installed in Ollama",
)

selected_model = custom_model_input.strip() if custom_model_input.strip() else selected_from_dropdown

if installed_models and selected_model not in installed_models and not any(m.startswith(f"{selected_model}:") for m in installed_models):
    st.sidebar.warning(f"⚠️ Model `{selected_model}` is not in your installed list.\nTo install, run:\n`ollama pull {selected_model}`")

st.sidebar.caption("💡 Larger models give better answers but run slower on CPU.")

st.sidebar.markdown("---")
# GitHub Token Status in Sidebar
token_present = get_github_token() is not None
if token_present:
    st.sidebar.caption("🔑 **GitHub API**: Authenticated (5,000 req/hr)")
else:
    st.sidebar.caption("🌐 **GitHub API**: Public mode (60 req/hr)")

if st.sidebar.button("🧹 Clear App Cache", use_container_width=True, help="Clears cached repository data and generated guides"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared!")


# -----------------------------------------------------------------------------
# MAIN APP HEADER (XSS-safe escaped rendering)
# -----------------------------------------------------------------------------
safe_model_display = html.escape(selected_model)
st.markdown(
    f"""
    <div class="main-header">
        <div class="main-title">Repo Guide</div>
        <div class="main-subtitle">A friendly open-source onboarding guide generator for GitHub repositories</div>
        <div class="powered-badge">Powered by {safe_model_display} (open-weight, running locally via Ollama)</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# STATE MANAGEMENT & CALLBACKS
# -----------------------------------------------------------------------------
if "repo_input_url" not in st.session_state:
    st.session_state.repo_input_url = DEFAULT_REPO_URL

if "trigger_run" not in st.session_state:
    st.session_state.trigger_run = False

if "show_trending" not in st.session_state:
    st.session_state.show_trending = False

if "refresh_nonce" not in st.session_state:
    st.session_state.refresh_nonce = 0


def select_and_run_repo(target_url: str) -> None:
    """Callback to reliably set the URL in session state and trigger analysis."""
    st.session_state.repo_input_url = target_url
    st.session_state.trigger_run = True


def toggle_trending() -> None:
    st.session_state.show_trending = True


def trigger_cache_refresh() -> None:
    st.session_state.refresh_nonce += 1
    st.session_state.trigger_run = True


# -----------------------------------------------------------------------------
# MAIN INPUT SECTION
# -----------------------------------------------------------------------------
repo_url = st.text_input(
    "GitHub Repository URL",
    key="repo_input_url",
    placeholder="https://github.com/owner/repository",
    help="Paste the URL of any public GitHub repository (e.g., https://github.com/mattpocock/skills)",
)

col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
with col_act1:
    analyze_clicked = st.button("Generate Beginner Guide →", type="primary", use_container_width=True)
with col_act2:
    st.button("Try the example repo", on_click=select_and_run_repo, args=(DEFAULT_REPO_URL,), use_container_width=True)
with col_act3:
    st.button("🔄 Refresh Data", on_click=trigger_cache_refresh, use_container_width=True, help="Bypasses cache and fetches fresh data from GitHub and Ollama")


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
    date_30_days_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        trending_list = fetch_trending_repos_cached(date_30_days_ago, token_present, st.session_state.refresh_nonce)
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
    st.session_state.trigger_run = False

    target_url = st.session_state.repo_input_url.strip()
    if not target_url:
        st.error("⚠️ Please enter a GitHub repository URL.")
    else:
        owner, repo = parse_github_url(target_url)
        if not owner or not repo:
            st.error(
                "⚠️ **Invalid GitHub URL.** Please enter a valid repository URL.\n\n"
                "- Expected format: `https://github.com/owner/repository`\n"
                "- Note: Subpaths like `/issues/1` or `/blob/main/...` are not supported."
            )
        else:
            try:
                with st.spinner(f"Fetching repository and analyzing with {selected_model} locally..."):
                    digest = f"{owner}/{repo}"
                    result = generate_guide_cached(
                        owner,
                        repo,
                        selected_model,
                        digest,
                        st.session_state.refresh_nonce,
                    )

                data: RepoData = result["data"]
                guide_content: str = result["guide_content"]

                st.success(f"Guide successfully generated for **{owner}/{repo}** using **{selected_model}**!")

                # Visible Indication for Partial Results
                if data.warnings:
                    st.warning(
                        "⚠️ **Partial Results Notice:** Some optional repository data could not be fully loaded:\n"
                        + "\n".join([f"- {w}" for w in data.warnings])
                    )

                # Repository Summary Box (HTML-escaped)
                safe_owner = html.escape(owner)
                safe_repo = html.escape(repo)
                safe_model = html.escape(selected_model)

                skills_badge = f"<br/><strong>Skills subfolders detected:</strong> {len(data.skill_subfolders)}" if data.skill_subfolders else ""
                dirs_badge = f"<br/><strong>Key directories:</strong> {html.escape(', '.join(data.detected_dirs))}" if data.detected_dirs else ""
                manifests_badge = f"<br/><strong>Detected manifests:</strong> {html.escape(', '.join(data.detected_manifests))}" if data.detected_manifests else ""

                st.markdown(
                    f"""
                    <div class="repo-summary-box">
                        <strong>Repository:</strong> <a href="https://github.com/{safe_owner}/{safe_repo}" target="_blank">{safe_owner}/{safe_repo}</a><br/>
                        <strong>Model used:</strong> {safe_model}<br/>
                        <strong>Total tree entries:</strong> {data.total_entries} items mapped{skills_badge}{dirs_badge}{manifests_badge}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Expandable details for fetched contents, manifests & tree
                with st.expander("🔍 View Inspected Structure, Manifests & Omissions"):
                    if data.omissions:
                        st.subheader("Collection Limits & Omissions")
                        for o in data.omissions:
                            st.info(f"ℹ️ {o}")

                    if data.warnings:
                        st.subheader("Non-Fatal Warnings")
                        for w in data.warnings:
                            st.warning(f"⚠️ {w}")

                    st.subheader("Top-Level Files & Directories")
                    st.code("\n".join(data.files_list), language="text")

                    if data.manifest_snippets:
                        st.subheader("Analyzed Manifest Snippets")
                        for path, snip in data.manifest_snippets.items():
                            st.write(f"**{path}**")
                            st.code(snip, language="text")

                    if data.skill_subfolders:
                        st.subheader(f"Skills Subfolders ({len(data.skill_subfolders)} mapped)")
                        st.code("\n".join(data.skill_subfolders), language="text")

                    st.subheader("Bounded Tree Preview (Depth <= 3)")
                    st.code("\n".join(data.tree_preview), language="text")

                    st.subheader("Truncated README (First 3000 chars)")
                    st.code(data.truncated_readme, language="markdown")

                # Beginner Guide Output inside Light Theme Card
                st.markdown('<div class="guide-card">', unsafe_allow_html=True)
                st.subheader(f"📖 Beginner Guide: {owner}/{repo}")
                st.markdown(guide_content)
                st.markdown('</div>', unsafe_allow_html=True)

                # Download Helper
                safe_file_model = selected_model.replace(":", "_").replace("/", "_")
                st.download_button(
                    label="📥 Download Guide as Markdown",
                    data=guide_content,
                    file_name=f"{repo}_{safe_file_model}_guide.md",
                    mime="text/markdown",
                )

            except RepoGuideError as e:
                st.error(str(e))
            except Exception as e:
                # Sanitized error display to prevent internal leaks
                st.error(f"❌ An error occurred while generating the guide. Please verify your inputs and local services: {type(e).__name__}")
