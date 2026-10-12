# Repo Guide 🧭

**Repo Guide** is a Streamlit application designed to help new open-source contributors easily understand and navigate GitHub repositories.

It fetches public repository structure, subfolders, and README files using the public GitHub API and utilizes local open-weight language models via **Ollama** to synthesize comprehensive, beginner-friendly onboarding guides.

---

## Key Features

- 💡 **Clean Light Grid Theme**: Features a clean light grid theme inspired by modern developer-event landing pages, with subtle dual-layer grid backgrounds, JetBrains Mono typography, and crisp borders.

### 💻 Laptop RAM & Model Picker (Feature 1)
- **RAM Tier Recommendations**:
  - **8 GB**: Small models around 1B–3B parameters (e.g., `llama3.2:1b`, `qwen2.5:1.5b`).
  - **16 GB** *(Default)*: Models around 3B–4B parameters (**`phi4-mini`** is the default).
  - **32 GB or more**: Models around 7B–8B parameters (e.g., `llama3:8b`, `mistral:7b`).
- **Installed Model Auto-Detection**: Inspects models installed on your machine using `ollama.list()` (supporting both dict and object library formats) and defaults to `phi4-mini` if present.
- **Custom Model Name Input**: Type any model installed in your local Ollama runtime to analyze repositories with it.
- **Missing Model Guidance**: If a model is not found, clear instructions with the exact pull command are displayed (e.g., `ollama pull <model-name>`).
- **Dynamic UI & Model-Specific Caching**: The selected model updates the header badge, spinner text (`Running <model> locally...`), inference calls, and `st.cache_data` storage keys.
- **Performance Notice**: Includes a reminder that larger models offer enhanced reasoning but run slower on CPU.

### 💡 Repository Suggestions & Trending Repos (Feature 2)
- **Pre-filled Default**: Pre-fills the input with `https://github.com/mattpocock/skills` while allowing custom URLs.
- **Curated 1-Click Repos**:
  - `mattpocock/skills` (AI Coding Agent Skills)
  - `ollama/ollama` (Local LLM Engine)
  - `streamlit/streamlit` (Interactive Web App Framework)
  - `microsoft/markitdown` (Document to Markdown Utility)
  - `ggml-org/llama.cpp` (C/C++ LLM Inference)
- **Trending New Repositories**:
  - Discover the top repositories created in the last 30 days via GitHub's public Search API (`https://api.github.com/search/repositories?q=created:>YYYY-MM-DD&sort=stars&order=desc&per_page=6`).
  - View repo name, star count, and project description.
  - 1-click loading and analysis.
  - Cached for 1 hour using `st.cache_data(ttl=3600)`.

### 🧭 Comprehensive Contributor Guides
- **4-Part Output**:
  1. **What the project does**: Clear, high-level summary.
  2. **How to run / use it**: Setup instructions, or skill installation guide if Markdown agent instructions are detected.
  3. **Map of important folders/files**: Directory layout including discovered skills subfolders.
  4. **Three ideas for a first contribution**: Actionable starting points for newcomers.
- **Smart Truncation**: Truncates README to the first 3,000 characters for optimal inference speed.
- **AI Agent Skills Awareness**: Distinguishes between runnable application code and AI agent skills/instructions.

---

## Model

By default, the application runs **phi4-mini** (3.8B parameters) served locally via **Ollama** with a context window of 4096 tokens (`num_ctx = 4096`).

---

## Prerequisites

1. **Python 3.10+**
2. **Ollama**: Download and install from [ollama.com](https://ollama.com).
3. **Pull the phi4-mini Model** (or any model of your choice):
   ```bash
   ollama pull phi4-mini
   ```

---

## Installation

Install dependencies from `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

---

## Running the Application

Make sure the Ollama daemon is running, then start the Streamlit application:

```bash
python -m streamlit run app.py
```

The app will launch in your browser (typically at `http://localhost:8501`).
