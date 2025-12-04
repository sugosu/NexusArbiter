# **AgentArbiter**

### **Deterministic Multi-Agent Orchestration Engine**

Strategy Arbitration • Provider-Agnostic Workflows • JSON-Driven Pipelines • Automatic Action Execution

---

## **Overview**

**AgentArbiter** is a general-purpose multi-agent orchestration framework designed for deterministic, repeatable, and auditable AI-driven workflows.

It reads declarative **run configurations** and **profile definitions**, merges context files, invokes LLM providers (OpenAI, Gemini, etc.), interprets model-generated actions, and executes them through a controlled, rule-driven pipeline.

AgentArbiter is suitable for:

* autonomous code generation
* automated refactoring and validation
* structured content transformation
* multi-step reasoning pipelines
* general AI workflow automation

---

## **Features**

### **Provider-Agnostic Engine**

Use any supported AI provider:

* OpenAI
* Gemini
* Extensible to future providers

Profiles define model parameters.

---

### **JSON-Driven Pipeline Execution**

All execution logic is defined in JSON:

* `runs.json` outlines the pipeline sequence
* Profiles describe model behavior and prompts
* Context files are dynamically merged

Pipelines become portable, deterministic, and easy to version-control.

---

### **Strategy Arbitration & Retry Engine**

AgentArbiter supports structured decision arbitration via:

* strategy files
* retry attempts
* allowed action filters
* deterministic termination through `break`

This enables complex, multi-step workflows with full control.

---

### **Action Execution System**

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
```

Built-in actions include:

* `file_write`
* `file_read`
* `validator`
* `continue`
* `break`
* `trigger_retry`

Actions are executed deterministically and logged.

---

### **Deterministic Logging (“Pipeline Story”)**

Every decision and event is logged to allow full reconstruction of:

* what happened
* why it happened
* which agent decided it
* which profile and strategy were used
* what actions executed
* retry decisions and termination conditions

Example narrative:

```
Pipeline started
Warp field stabilized.
[RUN] Starting 'codegen_step'
Prepared model payload (provider=openai model=gpt-5-turbo)
Executing action #1: file_write
```

---

### **Context Aggregation**

Profiles support `${agent_input}`, `${context_block}`, and `${task_description}` placeholders.

AgentArbiter automatically loads, merges, and injects context file content into the prompt.

---

### **Extensible Architecture**

All core components are modular:

* providers
* actions
* profiles
* strategies
* validators
* logging

New providers and actions can be added with minimal code.

---

## **Project Structure**

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

## **Example Run Configuration**

```json
{
  "runs": [
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
  ]
}
```

---

## **Example Profile**

```json
{
  "model": "gpt-5-turbo",
  "temperature": 0,
  "response_format": { "type": "json_object" },
  "messages": [
    { "role": "system", "content": "Act as a senior architect..." },
    { "role": "user", "content": "${agent_input}\n\n${context_block}" }
  ],
  "provider": "openai"
}
```

---

## **Roadmap**

* Strict JSON validation module
* Token usage metering
* Support for additional AI providers
* CLI interface
* Plugin system for third-party actions
* Workflow visualization
* Automated diff validators
* VS Code integration

---

## **License**

MIT License

