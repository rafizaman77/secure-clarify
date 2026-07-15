"""Ready-made generate_fn factories for secure_clarify.agent.OpenModelAgent.

OpenModelAgent(model_id, generate_fn) needs exactly one thing: a callable
generate_fn(prompt: str) -> str. Everything else (prompting, JSON parsing,
fail-safe fallbacks) is already implemented in agent.py. This module supplies
that one callable for the inference routes that actually fit this project's
constraints -- no local GPU (this dev environment is CPU-only torch, no CUDA)
-- so an OpenAI-compatible hosted API or Ollama are the two realistic options,
not a raw local transformers/vLLM pipeline.

Usage:
    from scripts.model_backends import openai_compatible_generate_fn
    from secure_clarify.agent import OpenModelAgent

    gen = openai_compatible_generate_fn(
        base_url="https://api.groq.com/openai/v1/chat/completions",
        api_key=os.environ["GROQ_API_KEY"],
        model="llama-3.1-8b-instant",
    )
    agent = OpenModelAgent(model_id="llama-3.1-8b-instant", generate_fn=gen)

Recommended providers (all OpenAI-chat-compatible, all serve open-weight
models, so this is one function for all of them -- just change base_url/model):
  - Groq       https://api.groq.com/openai/v1/chat/completions   (fast, free tier)
  - Together   https://api.together.xyz/v1/chat/completions
  - Fireworks  https://api.fireworks.ai/inference/v1/chat/completions
  - OpenRouter https://openrouter.ai/api/v1/chat/completions      (aggregates many)

No API key / want fully local and free instead: install Ollama
(https://ollama.com), `ollama pull llama3.1:8b`, then use ollama_generate_fn.
It runs on CPU here, so keep models small (3-8B) and expect it to be slow for
the full 120-task grid -- fine for the single-task smoke check in
scripts/smoke_real_model.py, budget real time for the full run_primary.py pass.

Third option, used for this repo's own real-numbers run: hf_local_generate_fn
loads a small open-weight instruction model directly via transformers, no API
key and no separate Ollama install needed -- just network access once to
download the weights from Hugging Face. The system Python here has a broken
numpy/scikit-learn ABI that breaks transformers' import chain, so this project
uses an isolated `.venv_model/` (see docs/DAILY_LOG.md) rather than touching
the system environment; run scripts through that venv's Python when using this
backend.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

_hf_cache: dict[str, tuple] = {}  # model_id -> (tokenizer, model) -- load once per process


def openai_compatible_generate_fn(base_url: str, api_key: str, model: str,
                                  temperature: float = 0.0, max_tokens: int = 512,
                                  timeout: float = 60.0, max_retries: int = 3):
    """Works with Groq / Together / Fireworks / OpenRouter / a local vLLM
    `--api-key` server -- anything speaking the OpenAI chat-completions shape.
    Deterministic decoding (temperature=0) as required for the main runs."""

    def generate(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(
            base_url, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"})
        last_err = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError) as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))
        # Fail safe: agent.py's callers (sample_intents/classify_malice/act)
        # all treat unparseable output as "no usable signal" rather than
        # crashing, so returning an empty string on total API failure is safe,
        # not silently wrong -- but it WILL suppress real experimental signal,
        # so surface the failure loudly rather than swallowing it quietly.
        raise RuntimeError(f"generate_fn failed after {max_retries} attempts: {last_err}")

    return generate


def ollama_generate_fn(model: str, host: str = "http://localhost:11434",
                       temperature: float = 0.0, timeout: float = 120.0,
                       max_retries: int = 2):
    """Local, free, no API key. Install Ollama, `ollama pull <model>` first
    (e.g. `ollama pull llama3.1:8b` or `ollama pull qwen2.5:7b`). CPU-only
    here, so this is slow -- fine for scripts/smoke_real_model.py, plan for
    real wall-clock time before running scripts/tune_dev.py / run_primary.py
    against it on the full dev/test split."""

    def generate(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{host}/api/generate", data=payload, method="POST",
            headers={"Content-Type": "application/json"})
        last_err = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["response"]
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError) as e:
                last_err = e
                time.sleep(2)
        raise RuntimeError(
            f"ollama generate_fn failed after {max_retries} attempts (is `ollama serve` "
            f"running and is '{model}' pulled?): {last_err}")

    return generate


def hf_local_generate_fn(model_id: str, max_new_tokens: int = 400):
    """Local transformers inference, greedy/deterministic. Loads once per
    process (module-level cache) since a real model load takes real time.
    Keep model_id small (e.g. 'Qwen/Qwen2.5-0.5B-Instruct',
    'HuggingFaceTB/SmolLM2-360M-Instruct') -- this is CPU-only."""

    def _load():
        if model_id not in _hf_cache:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            tok = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(model_id)
            model.eval()
            _hf_cache[model_id] = (tok, model)
        return _hf_cache[model_id]

    def generate(prompt: str) -> str:
        import torch
        tok, model = _load()
        messages = [{"role": "user", "content": prompt}]
        chat_prompt = tok.apply_chat_template(messages, tokenize=False,
                                              add_generation_prompt=True)
        inputs = tok(chat_prompt, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                 do_sample=False, temperature=None, top_p=None,
                                 pad_token_id=tok.eos_token_id)
        new_tokens = out[0][inputs["input_ids"].shape[1]:]
        return tok.decode(new_tokens, skip_special_tokens=True)

    return generate


def build_agent(backend: str, model: str, base_url: str = "", api_key_env: str = "",
                host: str = "http://localhost:11434"):
    """Shared factory used by smoke_real_model.py / tune_dev.py / run_primary.py
    so all three scripts accept the same --backend/--model/... flags."""
    import os
    from secure_clarify.agent import OpenModelAgent, ScriptedAgent

    if backend == "scripted":
        return ScriptedAgent(gullible=0.8)
    if backend == "openai":
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise SystemExit(
                f"Set {api_key_env} in your environment first "
                f"(export {api_key_env}=... / $env:{api_key_env}='...').")
        gen = openai_compatible_generate_fn(base_url=base_url, api_key=api_key, model=model)
    elif backend == "ollama":
        gen = ollama_generate_fn(model=model, host=host)
    elif backend == "hf_local":
        gen = hf_local_generate_fn(model_id=model)
    else:
        raise SystemExit(f"Unknown --backend {backend!r}")
    return OpenModelAgent(model_id=model, generate_fn=gen)


def add_backend_args(ap) -> None:
    """Shared CLI flags for scripts that need to pick a model backend."""
    ap.add_argument("--backend", choices=["scripted", "openai", "ollama", "hf_local"],
                    default="scripted")
    ap.add_argument("--model", default="ScriptedAgent")
    ap.add_argument("--base-url", default="https://api.groq.com/openai/v1/chat/completions")
    ap.add_argument("--api-key-env", default="GROQ_API_KEY")
    ap.add_argument("--host", default="http://localhost:11434")
