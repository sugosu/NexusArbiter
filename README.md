# NexusArbiter

**A file-based, deterministic multi-agent framework for structured AI interactions.**

NexusArbiter is designed for real-world and enterprise use cases, offering:

- **Reproducibility** — Consistent outputs from identical inputs
- **Auditability** — Full transparency into agent decisions
- **Predictability** — Deterministic behavior you can rely on
- **Configurability** — Flexible JSON-based workflow definitions

---

## Quick Start

### Requirements

- Python 3.10+
- API key for OpenAI or Gemini
- Windows, macOS, or Linux

### Installation

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set your OpenAI API key:

**macOS / Linux:**
```bash
export OPENAI_API_KEY="your_api_key_here"
```

**Windows:**

Create a `.env` file in the root folder:
```
OPENAI_API_KEY=your_api_key_here
```

> Need an API key? See the [OpenAI Quickstart Guide](https://platform.openai.com/docs/quickstart)

### Run Your First Workflow

```bash
python cli.py run /example/template/template_run.json
```

This launches the example workflow, which generates a Library Manager application by default. To customize the task, edit the first task description in `template_run.json`.

---

## 💡 Tip: AI-Assisted Learning

This repository includes a `merged_all` file containing all project files concatenated together. Feed this file to an AI assistant to get a comprehensive walkthrough of the entire framework in minutes.

---

## Documentation

*Coming soon — explore the `/example` directory for workflow templates and patterns.*

## License

*Add your license here*
