# Repo Guide 🧭

**Repo Guide** is a Streamlit application designed to help newcomers navigate and understand open-source GitHub repositories with ease.

By default, Repo Guide is pre-configured to analyze the [mattpocock/skills](https://github.com/mattpocock/skills) repository, with 1-click execution to explore repositories containing AI coding agent skills and standard software projects alike.

---

## Features

- 🔗 **Default & Custom URL Support**: Pre-filled with `https://github.com/mattpocock/skills` as the default repository, while allowing users to inspect any public GitHub repository.
- ✨ **One-Click Example**: Includes a dedicated **"Try the example repo"** button to instantly load and analyze the default skills repository.
- 📁 **Repository & Skills Subfolder Mapping**: Inspects top-level files/directories and recursively enumerates subfolders within main skills directories (e.g., `skills/engineering/ask-matt`) using GitHub's public API.
- 🧠 **AI Skills Awareness**: Specially instructed to recognize Markdown-based instruction files (skills) for AI coding assistants and explain how to install/use them rather than assuming runnable application code.
- ✂️ **3,000-Character Truncation**: Automatically limits the README to the first 3,000 characters for focused and efficient inference.
- ⚡ **Instant Caching (`st.cache_data`)**: Caches repository analysis results so that repeated runs on the same repository return instantly.
- 🤖 **Local AI with phi4-mini**: Powered by Microsoft's open-weight **phi4-mini** model running locally via **Ollama** with a 4096 context window (`num_ctx = 4096`).
- 🧭 **4-Part Contributor Guide**:
  1. **What the project does**: Overview and purpose of the project.
  2. **How to run / use it**: Instructions for setup, or how to use/install skills if it's an AI agent skill repository.
  3. **Map of important folders/files**: Directory layout including discovered skill subfolders.
  4. **Three ideas for a first contribution**: Actionable starting points for newcomers.
- 🛡️ **Friendly Error Handling**: Informative messages for invalid URLs, repository 404s, GitHub API rate limits, and Ollama connection status.

---

## Model

This application uses the open-weight **phi4-mini** model (3.8B parameters) served locally using **Ollama**.

---

## Prerequisites

1. **Python 3.10+**
2. **Ollama**: Download and install Ollama from [ollama.com](https://ollama.com).
3. **Pull the phi4-mini Model**:
   ```bash
   ollama pull phi4-mini
   ```
   *(or `ollama run phi4-mini`)*

---

## Installation

Install the required Python packages:

```bash
python -m pip install -r requirements.txt
```

---

## Running the Application

Ensure the Ollama service is running, then launch the Streamlit app with:

```bash
python -m streamlit run app.py
```

Streamlit will start locally and open in your default browser (usually at `http://localhost:8501`).

---

## Troubleshooting

- **Ollama not running**: Launch the Ollama desktop app or execute `ollama serve` in a terminal.
- **Model not found**: Run `ollama pull phi4-mini` to download the model.
- **GitHub rate limits**: Unauthenticated requests to GitHub's public API are limited to 60 requests/hour per IP. Cached analyses do not consume API limits on repeat visits.
