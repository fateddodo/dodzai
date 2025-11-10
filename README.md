# DodzAI Desktop

DodzAI is a multi-provider desktop AI workspace built with Python and Tkinter.
The project bundles a rich orchestration layer that lets you connect to hosted
providers such as OpenAI, Google Gemini and Hugging Face while also supporting
local Ollama models.  When network access is not available the application
falls back to a fully offline echo model so the interface remains usable.

The repository contains both the reusable orchestration engine and a Tkinter
user interface that showcases the core functionality.  The engine can be used
programmatically in other Python projects by importing :class:`dodzai.DodzAIEngine`.

## Highlights

- **Unified chat experience** – talk to models from multiple providers using a
  single conversation history.  Provider metadata and model selection are
  handled through a registry abstraction so switching between providers is a
  single dropdown change.
- **Persistent workspace** – user accounts, API keys, preferred modes and
  conversation history are stored locally using SQLite and JSON files inside the
  `~/.dodzai` directory.
- **Multimodal support** – image generation, basic vision analysis and voice
  assistance (text-to-speech and best-effort speech recognition) are available
  when the underlying provider or local environment supports them.  Fallback
  placeholder utilities are used when dependencies are missing.
- **Agent tooling** – a lightweight agent runtime executes tool plans with a
  sandboxed Python interpreter and an optional HTTP GET helper, demonstrating
  how automated workflows can be layered on top of the chat interface.
- **Offline resilience** – every provider implementation offers a deterministic
  offline mode so the UI remains responsive even without network access.

## Getting Started

### Requirements

- Python 3.11+
- Optional dependencies for advanced features (install only what you need):
  - `openai` for OpenAI access
  - `google-cloud-aiplatform` for Gemini via Vertex AI
  - `huggingface_hub` for Hugging Face inference
  - `requests` for Ollama or the agent web tool
  - `Pillow` for nicer placeholder image rendering
  - `pyttsx3` and `speech_recognition` for voice features

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # optional, create this file with the deps you need
```

The project intentionally avoids hard dependencies so the base experience works
out-of-the-box.  Install the packages that correspond to the providers you plan
to use.

### Launching the desktop application

```bash
python -m dodzai
```

On first launch the application automatically creates a demo user (username
`demo`, password `demo`).  Use the **Settings → API Keys** menu to add your own
credentials.  Provider specific environment variables such as
`OPENAI_API_KEY`, `GOOGLE_API_KEY` or `HUGGINGFACE_API_TOKEN` are also picked up
automatically when present.

## Project Structure

```
dodzai/
├── agents/          # Lightweight agent runtime and built-in tools
├── providers/       # Provider implementations for OpenAI, Google, Hugging Face and Ollama
├── services/        # Persistence and auxiliary services (history, profiles, voice)
├── ui/              # Tkinter desktop interface
├── utils/           # Helper modules (paths, markdown parsing, image helpers)
├── engine.py        # DodzAIEngine entry point
└── __main__.py      # Allows `python -m dodzai`
```

## Extending DodzAI

- **Add a provider** – subclass :class:`dodzai.providers.base.LLMProvider` and
  register it in `dodzai/providers/registry.py`.
- **Add an agent tool** – inherit from :class:`dodzai.agents.Tool` and register
  it using :meth:`DodzAIEngine.register_tool`.
- **Integrate into your own project** – import :class:`dodzai.DodzAIEngine` and
  orchestrate providers, conversations and multimodal actions without the UI.

## Packaging

The desktop client is designed to work with PyInstaller.  A typical command is:

```bash
pyinstaller -n DodzAI --onefile dodzai/__main__.py
```

Bundle any provider credentials or additional assets you require by extending
that command or adjusting the PyInstaller spec file as needed.
