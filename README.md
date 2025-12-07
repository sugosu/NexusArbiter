# NexusArbiter

NexusArbiter is a deterministic, multi-provider AI orchestration framework designed for reliable code generation pipelines, structured execution flows, and advanced strategy-based reruns. It unifies OpenAI, Gemini, and custom providers into a consistent execution engine with traceable inputs, validated outputs, and reproducible runs.

NexusArbiter focuses on:

• Determinism – outputs must be structured and predictable  
• Traceability – optional logging for requests and responses  
• Control – explicit actions such as file_write, continue, break, rerun  
• Extensibility – profiles, runs, and strategies are modular  
• Reliability – system retry and controlled rerun attempts  

------------------------------------------------------------

## Key Features

### Multi-provider AI Execution
You can run OpenAI, Gemini, or custom providers in a single pipeline.  
Provider selection may occur in:

• profiles  
• run configuration  
• strategy-level rerun overrides  

### Deterministic Action Contract
Models must return a structured JSON response with an agent.actions array.
This ensures predictable behavior and eliminates ambiguity during execution.

### Strategy-Based Reruns
Validators can request reruns of earlier steps.  
Strategies define:

• number of attempts  
• alternative profiles  
• alternative providers  
• alternative context files  

Once attempts are exhausted, the validator continues execution.

### System Retry Policy
Retry logic handles:

• timeouts  
• 429 (rate limit)  
• 5xx server errors  
• network errors  

Configured globally in runs.json.

### Optional Request/Response Logging
When enabled, NexusArbiter writes:

• request payloads  
• raw responses  
• metadata (run, attempt, provider)  

to disk for debugging and auditing.

------------------------------------------------------------

## Repository Structure

NexusArbiter/
  core/
    actions/
    ai_client/
    config/
    logger/
    runtime/
    strategy/
    utils/
  context_files/
    profiles/
    runs/
    strategies/
    general/
  app/
  tests/
  README.md
  LICENSE

------------------------------------------------------------

## How NexusArbiter Works

### 1. RunConfig Loads Pipeline Definition
Runs.json defines the steps to execute, along with allowed actions, profiles, strategies, and parameters.

### 2. PipelineRunner Executes Runs
It manages:

• ordering  
• retry attempts  
• rerun triggers  
• break / continue flow  

### 3. AppRunner Handles Provider Invocation
AppRunner loads a profile, builds a prompt, calls the provider, parses the structured output, and executes the actions.

### 4. Action Execution Layer
Available built-in actions:

• file_write  
• continue  
• break  
• rerun  

Actions update the environment and control the pipeline.

### 5. Validator-Driven Reruns
Validators may request reruns, activating a strategy block.  
Overrides may modify:

• provider  
• profile  
• context files  

Execution then returns to the validator until attempts expire.

------------------------------------------------------------

## Profiles, Context, and Strategies

### Profiles
Define:

• provider and model  
• temperature, top_p, max_tokens  
• system and user templates  
• placeholders such as task_description, agent_input, rules_block, context_block  

### Context Files
Used to inject:

• prior outputs  
• code  
• configuration  
• reference material  

### Strategies
Define deterministic rerun behavior via blocks and attempts, enabling correction cycles.

------------------------------------------------------------

## Testing

The framework includes tests for:

• file_write, continue, break, rerun actions  
• strategy loading  
• rerun control flow  
• registry correctness  
• provider behavior stubs  

Additional integration tests can be added for full pipelines.

------------------------------------------------------------

## Roadmap

Future enhancements include:

• structured per-attempt logs  
• parallel execution engine  
• expanded provider compatibility  
• CLI tooling  
• visual pipeline debugger  
• browser UI for traces  
• plugin system for custom actions  
• curated example pipelines (e.g., full project generators)

------------------------------------------------------------

## License

This project is licensed under the MIT License.
See the LICENSE file for details.
