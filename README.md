# Repo Guide 🧭

**Repo Guide** is a developer tool and Streamlit application designed to help new open-source contributors easily explore and onboard onto public GitHub repositories.

By inspecting repository trees, build manifests, and documentation through the GitHub API and running local open-weight language models via **Ollama**, Repo Guide synthesizes structured, beginner-friendly onboarding guides—with zero cloud LLM dependencies, total data privacy, and strong prompt injection defense.

---

## Architecture Overview

Repo Guide is organized into clear, focused modules designed for testability and maintainability:

```
mlh/
├── app.py                 # Streamlit frontend, UI theme, caching, and state management
├── github_client.py       # GitHub API integration, URL validation, and rate limit handling
├── ollama_client.py       # Ollama client queries, model discovery, and chat execution
├── prompt_builder.py      # Prompt construction with untrusted data boundary delimiters
├── models.py              # Core data classes (RepoData, TrendingRepo) and RepoGuideError
├── requirements.txt       # Reproducible dependencies with compatible bounded versions
├── pyproject.toml         # Build metadata and pytest test configuration
├── tests/
│   └── test_repo_guide.py # Comprehensive offline unit tests (100% mocked)
└── .streamlit/
    ├── config.toml        # Streamlit UI theme settings
    └── secrets.toml       # (Optional, git-ignored) GitHub personal access token
```

### Data & Execution Flow

```
[User Input: GitHub URL]
           │
           ▼
[github_client.parse_github_url] ──(Validation: owner, repo, no subpaths)
           │
           ▼
[github_client.fetch_github_repo_data]
   ├── Git Trees API (HEAD?recursive=1)
   ├── Detect key manifests & directories
   └── Fetch README & selective manifest snippets
           │
           ▼
[prompt_builder.build_safe_prompt]
   └── Wraps repository data in <<<UNTRUSTED_REPOSITORY_DATA>>> delimiters
           │
           ▼
[ollama_client.run_ollama_chat] ──(Local Ollama model: phi4-mini, llama3, etc.)
           │
           ▼
[Structured Beginner Guide displayed in Streamlit UI]
```

---

## Features

- 💡 **Light Grid Theme**: Designed with clean developer-event styling, subtle dual-layer background grids, high-contrast monospace typography (JetBrains Mono), and crisp borders.
- 🛡️ **Prompt Injection Defense**: Repository content is strictly treated as untrusted reference data enclosed in boundary delimiters. The model is forbidden from executing repo commands or adopting role changes.
- 🌲 **Git Trees API Ingestion**: Maps recursive repository structure in a single bounded request, with automatic fallback to the default branch if needed.
- 📦 **Key Manifest Detection**: Discovers build and configuration manifests (`pyproject.toml`, `package.json`, `requirements.txt`, `Dockerfile`, `Makefile`, `Cargo.toml`, etc.) and retrieves bounded snippets.
- 🧩 **Agent Skills Awareness**: Automatically detects and analyzes AI-agent skill collections (`skills/` directory), explaining agent capabilities rather than pretending the project is runnable application software.
- 💻 **RAM-Based Model Recommendations**:
  - **8 GB**: Small models around 1B–3B parameters (`llama3.2:1b`, `qwen2.5:1.5b`).
  - **16 GB** *(Default)*: Models around 3B–4B parameters (**`phi4-mini`**).
  - **32 GB+**: Models around 7B–8B parameters (`llama3:8b`, `mistral:7b`).
- ⚡ **Two-Tier Caching & Invalidation**: GitHub data is cached for 30 minutes; generated guides are cached for 1 hour. Features a **🔄 Refresh Data** button to force immediate re-evaluation.
- ⏱️ **Rate-Limit Intelligence**: Displays human-readable reset countdowns from `x-ratelimit-reset` headers and supports optional authentication.
- 🔥 **Trending Repositories Discovery**: 1-click discovery and inspection of popular projects created in the past 30 days.

---

## Prerequisites

1. **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13, or 3.14)
2. **Ollama**: Download and install from [ollama.com](https://ollama.com)

---

## Ollama Setup

1. Start the Ollama daemon:
   ```bash
   ollama serve
   ```
2. Pull the recommended default model (`phi4-mini`):
   ```bash
   ollama pull phi4-mini
   ```
   *(Optional: You can also pull smaller models like `ollama pull llama3.2:1b` or larger models like `ollama pull llama3:8b`).*
3. Verify installed models:
   ```bash
   ollama list
   ```

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/vardishrayapudi-beep/mlh.git
cd mlh
python -m pip install -r requirements.txt
```

---

## GitHub Token Configuration (Optional)

By default, the unauthenticated GitHub API rate limit is **60 requests per hour**. Configuring a GitHub Personal Access Token (PAT) increases your rate limit to **5,000 requests per hour**.

You can supply your token using either method:

### Method A: Streamlit Secrets (Recommended)
Create a `.streamlit/secrets.toml` file in the project root:
```toml
GITHUB_TOKEN = "ghp_yourPersonalAccessTokenHere"
```
*(Note: `.streamlit/secrets.toml` is already included in `.gitignore` to prevent committing credentials).*

### Method B: Environment Variable
```bash
# Windows PowerShell:
$env:GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere"

# Windows Command Prompt:
set GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere

# macOS / Linux:
export GITHUB_TOKEN="ghp_yourPersonalAccessTokenHere"
```

---

## Running the Application

Ensure the Ollama service is running, then start the Streamlit app:

```bash
python -m streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.

---

## Running Automated Tests

Repo Guide includes an extensive offline unit test suite powered by `pytest`. The test suite mocks all network requests and Ollama calls, requiring zero live connections or active services:

```bash
python -m pytest
```

To run tests with detailed verbosity:
```bash
python -m pytest -v
```

The test suite validates:
- Valid and invalid GitHub URL parsing
- `.git` suffix and trailing slash normalization
- Subpath rejection (`/issues`, `/blob`, `/pull`, `/releases`)
- GitHub API status code handling (401, 403, 404, 409, 500+)
- Rate limit calculation and unauthenticated tips
- README missing (404) and partial network failure fallbacks
- Trending repository response transformation
- Ollama response parsing for both dictionary and object formats
- Missing model (`ollama pull`) and service offline errors
- Prompt boundary delimiters and untrusted content markers

---

## Cache Behavior

Repo Guide employs tiered Streamlit caching (`@st.cache_data`) for high performance and minimal API usage:

| Data Type | Cache TTL | Invalidation Trigger |
| :--- | :--- | :--- |
| **GitHub Repository Trees & Manifests** | 30 minutes (`ttl=1800`) | "🔄 Refresh Data" button or cache clear |
| **Generated Onboarding Guides** | 1 hour (`ttl=3600`) | "🔄 Refresh Data", model change, or "🧹 Clear App Cache" |
| **Trending Repositories** | 1 hour (`ttl=3600`) | "🔄 Refresh Data" or cache clear |

- **Cache Keys**: Keys incorporate `(owner, repo, model_name, cache_digest, refresh_nonce)` to guarantee isolation.
- **Forced Invalidation**: Clicking **🔄 Refresh Data** increments the session nonce, bypassing cached responses and pulling fresh content from GitHub and Ollama.
- **Manual Cache Purge**: Click **🧹 Clear App Cache** in the sidebar at any time to flush all cached entries.

---

## Security Note: Untrusted Repository Content

> [!IMPORTANT]
> External repository files, README markdown, and manifest contents are **untrusted user data**.
> Malicious repositories may attempt indirect prompt injection (e.g., hidden text attempting to override system behavior, exfiltrate data, or execute harmful commands).

Repo Guide defends against these attacks by:
1. Enclosing all ingested repository data inside clear boundary delimiters (`<<<UNTRUSTED_REPOSITORY_DATA>>>`, `<<<UNTRUSTED_README>>>`).
2. Explicitly instructing the model to treat repository content strictly as passive subject matter.
3. Forbidding the model from adopting commands, persona changes, or instructions found inside the repository.
4. Escaping user-controlled values (`html.escape`) before rendering inside custom HTML components to prevent XSS.

---

## Troubleshooting

### 1. "Ollama is not running"
- **Cause**: The Ollama background service is not running.
- **Solution**: Open the Ollama desktop application or run `ollama serve` in a terminal window.

### 2. "Model 'phi4-mini' was not found in Ollama"
- **Cause**: The chosen model has not been downloaded yet.
- **Solution**: Run `ollama pull phi4-mini` (or the model name displayed in the warning) in your terminal.

### 3. "GitHub API Rate Limit Reached"
- **Cause**: The 60 requests/hour unauthenticated quota was exceeded.
- **Solution**: Check the reset countdown displayed on the screen or configure a `GITHUB_TOKEN` in `.streamlit/secrets.toml` to gain 5,000 requests/hour.

### 4. "Invalid GitHub URL"
- **Cause**: The URL provided contains subpaths (such as `/issues/1` or `/blob/main/file.py`), points to a non-GitHub host, or is malformed.
- **Solution**: Use the standard repository URL format: `https://github.com/owner/repository`.

---

## Known Limitations

- **Public Repositories Only**: The app is designed for public GitHub repositories; private repositories are not accessed unless a token with private repo scope is provided.
- **Ingestion Limits**: To prevent context window overflow on local models, repositories are bounded to a tree depth of 3, up to 120 items, up to 2 key manifests (max 50 KB each), and README content up to 3,000 characters. Transparent notices are displayed when limits are applied.
- **Single-Host Support**: Currently validates and inspects repositories hosted on GitHub (`github.com`). Other hosts (GitLab, Bitbucket, self-hosted Git) are not supported.

---

## Contribution Guidelines

Contributions are welcome! Please follow these guidelines:

1. **Keep Code Modular**: Add models to `models.py`, API logic to `github_client.py`, Ollama logic to `ollama_client.py`, and prompts to `prompt_builder.py`.
2. **Preserve Security Directives**: Never remove prompt boundary delimiters or untrusted data markers.
3. **Add Tests**: All new features or bug fixes must include unit tests in `tests/test_repo_guide.py` mocking network and Ollama calls.
4. **Run Verification**: Ensure all tests pass prior to submitting changes:
   ```bash
   python -m pytest
   ```

---

## License

This project is licensed under the terms of the MIT License. See [LICENSE](LICENSE) for details.
