Understood.
You want **the entire README.md ONLY inside one single fenced code block**, with **no text outside**, so you can copy-paste cleanly.

Here it is.
Everything below is **exactly** the README.md content and nothing else.

---

````markdown
# AgentArbiter

### Deterministic Multi-Agent Orchestration Engine  
Strategy Arbitration • Provider-Agnostic Workflows • JSON-Driven Pipelines • Automatic Action Execution

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Example Workflows](#example-workflows)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Attribution](#attribution)

---

## Overview

**AgentArbiter** is a general-purpose multi-agent orchestration framework designed for deterministic, repeatable, and auditable AI-driven workflows.

It reads declarative **run configurations** and **profile definitions**, merges context files, invokes AI providers (OpenAI, Gemini, etc.), interprets model-generated actions, and executes them through a controlled, rule-driven pipeline.

AgentArbiter is suitable for:

- autonomous code generation  
- automated refactoring and validation  
- structured content transformation  
- multi-step reasoning pipelines  
- general AI workflow automation  

---

## Features

### Provider-Agnostic Engine
Supports multiple AI providers:
- OpenAI  
- Gemini  
- Extensible provider system  

Profiles define model parameters. Runs may override providers dynamically.

---

### JSON-Driven Pipeline Execution
All execution logic is defined in JSON:
- `runs.json` outlines the execution sequence  
- Profiles describe model behavior and prompt structure  
- Context files are dynamically merged and injected  

Pipelines become portable, deterministic, and version-controlled.

---

### Strategy Arbitration & Retry Engine
AgentArbiter supports structured AI-driven decision arbitration:
- strategy files  
- retry logic  
- provider overrides  
- allowed-actions filters  
- deterministic halting via `break`  

This enables flexible, powerful workflows while retaining strict control.

---

### Action Execution System
Models output structured JSON actions, for example:

```json
{
  "agent": {
    "actions": [
      {
        "type": "file_write",
        "params": {
          "target_path": "app/main.py",
          "content": "print('Hello World')"
        }
      }
    ]
  }
}
````

Built-in actions include:

* `file_write`
* `file_read`
* `validator`
* `continue`
* `break`
* `trigger_retry`

Actions are executed deterministically and logged.

---

### Deterministic Logging (“Pipeline Story”)

Every decision and event is logged to allow full reconstruction of:

* what happened
* why it happened
* which agent or strategy decided it
* which provider and profile were used
* what actions were executed
* retry and break conditions

Example:

```
Pipeline started
Warp field stabilized.
[RUN] Starting 'codegen_step'
Prepared model payload (provider=openai model=gpt-5-turbo)
Executing action #1: file_write → app/main.py
```

---

### Context Aggregation

Profiles support `${agent_input}`, `${context_block}`, and `${task_description}` placeholders.

AgentArbiter loads, merges, and injects context file content automatically.

---

### Extensible Architecture

Core components are modular:

* providers
* actions
* profiles
* strategies
* validators
* logging

Adding new provider clients or actions requires minimal code.

---

## Architecture Overview

AgentArbiter follows a layered orchestration model:

```
               +---------------------+
               |    PipelineRunner   |
               | (executes runs.json)|
               +----------+----------+
                          |
                          v
               +---------------------+
               |     RunExecutor     |
               | (retry + strategy)  |
               +----------+----------+
                          |
                          v
               +---------------------+
               |      AppRunner      |
               | (profile, AI call,  |
               |  context merging)   |
               +----------+----------+
                          |
                          v
               +---------------------+
               |   Provider Client   |
               |  (OpenAI/Gemini)    |
               +----------+----------+
                          |
                          v
               +---------------------+
               |    Action Engine    |
               | (file ops, checks)  |
               +---------------------+
```

---

## Installation

```bash
git clone https://github.com/sugosu/AgentArbiter.git
cd AgentArbiter
pip install -r requirements.txt
```

Optional virtual environment:

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
```

---

## Usage

### Running a pipeline

```bash
python main.py --config context_files/runs/example.json
```

This executes the sequence defined in `runs.json` and logs the pipeline narrative.

---

### Creating a new run

```json
{
  "name": "generate_component",
  "profile_file": "context_files/profiles/code_generation.json",
  "context_files": [
    "context_files/project_manifest.json"
  ],
  "target_file": "app/component.py",
  "allowed_actions": [
    "file_write",
    "validator",
    "trigger_retry",
    "continue"
  ]
}
```

---

## Configuration

### Profiles

```json
{
  "model": "gpt-5-turbo",
  "provider": "openai",
  "messages": [
    { "role": "system", "content": "Act as a senior architect." },
    { "role": "user", "content": "${agent_input}\n\n${context_block}" }
  ],
  "response_format": { "type": "json_object" }
}
```

---

### Strategies

```json
{
  "attempts": [
    { "profile": "profile_1.json" },
    { "profile": "profile_2.json" }
  ]
}
```

---

### Allowed Actions

Runs strictly filter which actions the model may produce.

---

## Example Workflows

### 1. Automated Code Generation Workflow

* Load project manifest
* Generate module
* Validate output
* Retry with alternate strategy if validation fails

### 2. Refactoring Workflow

* Load existing code
* Ask AI to refactor
* Validate style and structure
* Write file only if validation passes

### 3. Documentation Workflow

* Generate documentation based on context files
* Validate structure
* Write markdown output

---

## Project Structure

```
core/
  runtime/
    pipeline_runner.py
    run_executor.py
    app_runner.py
  actions/
    base_action.py
    registry.py
  ai_client/
    openai_client.py
    gemini_client.py
    ai_response_parser.py
context_files/
  profiles/
  runs/
  strategies/
app/
main.py
```

---

## Roadmap

* Strict JSON validation module
* Token usage metering
* Support for additional AI providers
* CLI utility
* Third-party action plugins
* Workflow visualization tools
* Automated diff validators
* VS Code extension

---

## Contributing

1. Fork this repository
2. Create a feature branch

   ```bash
   git checkout -b feature/my-feature
   ```
3. Commit your changes
4. Push your branch and open a Pull Request

Contributions are welcome.

---

## License

MIT License

---

## Attribution

AgentArbiter is an independent project and not affiliated with Nethermind’s “ArbiterAgent” or AgentArena.
Terminology overlap reflects common language in multi-agent orchestration systems.

```
