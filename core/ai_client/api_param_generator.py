# ai_param_generator.py (patched)
from typing import Any, Dict, Optional, Literal, Mapping, Union, List
import copy

PresetName = Literal["fast_chat", "code_generation", "function_calling", "reasoning_heavy"]

class AIParamGenerator:
    """
    Builds ready-to-send payloads for OpenAI's /v1/chat/completions
    and dispatches them using an injected OpenAIClient instance.
    """

    def __init__(self, client, default_user: str = "onat"):
        self.client = client
        self.default_user = default_user

        # --- Preset templates (safe to deepcopy, merged with overrides) ---
        # Note: 'metadata' is removed (not supported on chat/completions).
        #       Model default set to gpt-4o (public REST API).
        self._presets: Dict[PresetName, Dict[str, Any]] = {
            "fast_chat": {
                "model": "gpt-4o",
                "temperature": 0.7,
                "top_p": 1,
                "max_tokens": 600,
                "messages": [
                    {"role": "system", "content": "You are a concise, helpful assistant."},
                    {"role": "user", "content": "Give me three ideas for naming a new internal AI framework."}
                ],
                "user": self.default_user
            },
            "code_generation": {
                "model": "gpt-4o",
                "temperature": 0,
                "top_p": 1,
                "max_tokens": 1200,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a senior software engineer. Produce clean, correct code and minimal explanations. "
                            "Your answer must be formatted strictly as JSON with two keys: 'code' and 'context'. "
                            "Example: {\"code\": \"...\", \"context\": \"...\"}. "
                            "Do not include anything else outside this JSON structure."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            "Write a Python @dataclass named RepoConfig with fields repo_path:str, default_branch:str=\"main\", remote_name:str=\"origin\", author_name:str=\"AI Agent\", author_email:str=\"ai@example.com\", including type hints and a class-level docstring."
                   )
                }
                ],
                # Chat Completions supports only {"type": "json_object"} (no schema).
                "response_format": {"type": "json_object"},
                "user": self.default_user
            }
        }

    # ---------------- Public API ----------------

    def build(
        self,
        preset: PresetName,
        overrides: Optional[Mapping[str, Any]] = None,
        *,
        extend_messages: bool = False
    ) -> Dict[str, Any]:
        base = copy.deepcopy(self._presets[preset])
        if overrides:
            base = self._merge(base, overrides, extend_messages=extend_messages)

        self._validate(base)
        return self._strip_nones(base)

    def send(
        self,
        preset: PresetName,
        overrides: Optional[Mapping[str, Any]] = None,
        *,
        extend_messages: bool = False,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        body = self.build(preset, overrides, extend_messages=extend_messages)
        return self.client.send_request(body=body, headers=headers, timeout=timeout)

    # Convenience builders/senders
    def build_fast_chat(self, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        return self.build("fast_chat", overrides)

    def build_code_generation(self, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        return self.build("code_generation", overrides)

    def send_fast_chat(self, overrides: Optional[Mapping[str, Any]] = None, **send_kwargs) -> Dict[str, Any]:
        return self.send("fast_chat", overrides, **send_kwargs)

    def send_code_generation(self, overrides: Optional[Mapping[str, Any]] = None, **send_kwargs) -> Dict[str, Any]:
        return self.send("code_generation", overrides, **send_kwargs)

    def send_function_calling(self, overrides: Optional[Mapping[str, Any]] = None, **send_kwargs) -> Dict[str, Any]:
        return self.send("function_calling", overrides, **send_kwargs)

    def send_reasoning_heavy(self, overrides: Optional[Mapping[str, Any]] = None, **send_kwargs) -> Dict[str, Any]:
        return self.send("reasoning_heavy", overrides, **send_kwargs)

    # ---------------- Internals ----------------

    def _merge(
        self,
        base: Dict[str, Any],
        overrides: Mapping[str, Any],
        *,
        extend_messages: bool
    ) -> Dict[str, Any]:
        result = copy.deepcopy(base)

        def _merge_dict(dst: Dict[str, Any], src: Mapping[str, Any]) -> Dict[str, Any]:
            for k, v in src.items():
                if k == "messages":
                    if extend_messages and isinstance(v, list) and isinstance(dst.get(k), list):
                        dst[k] = dst.get(k, []) + list(v)
                    else:
                        dst[k] = copy.deepcopy(v)
                elif isinstance(v, Mapping) and isinstance(dst.get(k), dict):
                    dst[k] = _merge_dict(dst[k], v)
                else:
                    dst[k] = copy.deepcopy(v)
            return dst

        return _merge_dict(result, overrides)

    def _validate(self, body: Dict[str, Any]) -> None:
        msgs = body.get("messages")
        if not isinstance(msgs, list) or len(msgs) == 0:
            raise ValueError("`messages` must be a non-empty list.")
        if msgs[-1].get("role") not in {"user", "assistant", "tool"}:
            raise ValueError("Last message should generally be from 'user' or 'assistant' (or 'tool' if mid-tool).")

        temp = body.get("temperature", 1)
        if not (0 <= temp <= 2):
            raise ValueError("`temperature` must be between 0 and 2.")
        top_p = body.get("top_p", 1)
        if not (0 < top_p <= 1):
            raise ValueError("`top_p` must be in (0, 1].")

        max_tokens = body.get("max_tokens")
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise ValueError("`max_tokens` must be a positive integer when provided.")

        # response_format: only allow {"type": "json_object"} on chat/completions
        rf = body.get("response_format")
        if rf:
            if not isinstance(rf, dict) or rf.get("type") not in {"json_object"}:
                raise ValueError("On /v1/chat/completions, `response_format` must be {'type': 'json_object'} or omitted.")

        tools = body.get("tools")
        if tools is not None and not isinstance(tools, list):
            raise ValueError("`tools` must be a list when provided.")
        if tools:
            names: List[str] = []
            for t in tools:
                if not isinstance(t, dict) or t.get("type") != "function":
                    raise ValueError("Each tool must be a dict with type='function'.")
                fn = t.get("function", {})
                name = fn.get("name")
                if not name:
                    raise ValueError("Each function tool needs a unique `name`.")
                if name in names:
                    raise ValueError(f"Duplicate tool function name: {name}")
                names.append(name)

    def _strip_nones(self, body: Dict[str, Any]) -> Dict[str, Any]:
        def _clean(v: Any) -> Any:
            if isinstance(v, dict):
                return {k: _clean(x) for k, x in v.items() if x is not None}
            if isinstance(v, list):
                return [_clean(x) for x in v if x is not None]
            return v
        return _clean(body)
    
    def build_code_from_string(
        self,
        code_str: str,
        instruction: str,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 2000,
        json_output: bool = True
    ) -> Dict[str, Any]:
        """
        Build a request that sends Python source code as input plus an instruction.
        Returns a body compatible with /v1/chat/completions.
        If json_output=True, asks the model to return: {"code": "<updated code>"}.
        """
        system_msg = (
            "You are a senior software engineer. Produce clean, correct code and minimal explanations. "
            "If JSON is requested, respond in JSON only with a single object containing the key \"code\"."
        )

        if json_output:
            user_msg = (
                "Task (respond in JSON only): {\"code\": string}. Do not include any extra keys.\n"
                f"Instruction: {instruction}\n"
                "Here is the Python source code:\n"
                "```python\n"
                f"{code_str}\n"
                "```"
            )
            response_format = {"type": "json_object"}
        else:
            user_msg = (
                f"Instruction: {instruction}\n"
                "Return only the updated code below, no extra commentary:\n"
                "```python\n"
                f"{code_str}\n"
                "```"
            )
            response_format = None  # plain-text code output

        body = {
            "model": model,
            "temperature": temperature,
            "top_p": 1,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "user": self.default_user,
        }

        if response_format is not None:
            body["response_format"] = response_format

        self._validate(body)
        return self._strip_nones(body)

    def send_code_from_string(
        self,
        code_str: str,
        instruction: str,
        **send_kwargs
    ) -> Dict[str, Any]:
        """
        Build and send the parameterized code-transform request in one step.
        """
        body = self.build_code_from_string(code_str=code_str, instruction=instruction)
        return self.client.send_request(body=body, **send_kwargs)
        
