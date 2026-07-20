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

import concurrent.futures
import json
import time
import urllib.error
import urllib.request

_HTTP_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="groq-http")


def _urlopen_hard_timeout(req: urllib.request.Request, socket_timeout: float,
                          hard_timeout: float):
    """Run urlopen in a worker thread and enforce a HARD wall-clock timeout via
    future.result(), instead of trusting urllib's own socket timeout alone.

    Observed directly in this environment: individual Groq requests
    occasionally hang well past the requested socket timeout (no exception,
    no data, indefinitely) -- rare (roughly 1 in 10-20 calls) but frequent
    enough to stall a 96-task run for many minutes with zero visible
    progress. Python can't forcibly kill a blocked OS-level socket read from
    the outside, so the abandoned thread may linger, but future.result(
    timeout=...) still lets the CALLER move on and retry rather than hang
    forever waiting for a call that urllib itself should have already timed
    out on but didn't."""
    future = _HTTP_EXECUTOR.submit(
        lambda: urllib.request.urlopen(req, timeout=socket_timeout).read())
    return future.result(timeout=hard_timeout)

# Hosted providers (Groq, Together, Fireworks, OpenRouter, ...) sit behind
# Cloudflare, whose default managed rules 403 the stock `Python-urllib/x.y`
# User-Agent as a bot signature (Cloudflare error 1010). Any non-bot UA passes,
# so every outbound request must set one explicitly or the openai backend fails
# 100% of the time with a misleading "403 Forbidden".
_USER_AGENT = "secure-clarify/1.0"

_hf_cache: dict[str, tuple] = {}  # model_id -> (tokenizer, model) -- load once per process


def openai_compatible_generate_fn(base_url: str, api_key: str, model: str,
                                  temperature: float = 0.0, max_tokens: int = 512,
                                  timeout: float = 60.0, max_retries: int = 8,
                                  min_interval: float = 0.0):
    """Works with Groq / Together / Fireworks / OpenRouter / a local vLLM
    `--api-key` server -- anything speaking the OpenAI chat-completions shape.
    Deterministic decoding (temperature=0) as required for the main runs.

    Rate limits: free tiers throttle sustained use, so a full 120-task grid WILL
    hit HTTP 429 repeatedly. That is expected and recoverable -- the 429 carries
    a `Retry-After` header telling us exactly how long to wait, so on 429 we
    honor it and continue rather than failing the run. Two calibration lessons
    the hard way on Groq's llama-3.3-70b free tier: (1) the binding limit is NOT
    the per-minute token bucket (which stays ~healthy) but a daily/burst limit
    whose Retry-After is 130-300s, so the wait cap must be well above that --
    an earlier 8s, then 65s, cap could not outlast it and aborted mid-run; and
    (2) honoring the FULL Retry-After (rather than hammering early) also avoids
    the escalating penalty Groq applies when a client ignores it. Other errors
    (network blips, 5xx) still use short exponential backoff. A small
    `min_interval` throttle between calls further smooths sustained runs so they
    trip the burst limit less often."""

    last_call = [0.0]  # wall-clock of the previous request start (for min_interval)

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
                     "Authorization": f"Bearer {api_key}",
                     "User-Agent": _USER_AGENT})
        if min_interval > 0:
            gap = min_interval - (time.time() - last_call[0])
            if gap > 0:
                time.sleep(gap)
        last_call[0] = time.time()
        last_err = None
        for attempt in range(max_retries):
            try:
                raw = _urlopen_hard_timeout(req, socket_timeout=timeout, hard_timeout=timeout + 10)
                data = json.loads(raw.decode("utf-8"))
                return data["choices"][0]["message"]["content"]
            except concurrent.futures.TimeoutError as e:
                # urllib's own socket timeout occasionally does not fire on
                # this platform (observed directly: calls hanging well past
                # `timeout` seconds with no exception) -- the hard wall-clock
                # timeout above is what actually bounds it. The abandoned
                # worker thread is left to finish or die on its own; we just
                # don't wait for it.
                last_err = e
                time.sleep(min(2 ** attempt, 8))
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 429:
                    # Honor Retry-After (seconds) so we wait exactly long
                    # enough for the window to reset; fall back to a growing
                    # wait if the header is absent. The cap must exceed Groq's
                    # observed 130-300s burst-limit Retry-After (a lower cap
                    # retries too early and burns all attempts before the window
                    # clears), while still bounding a truly exhausted daily
                    # limit to a finite failure.
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait = float(retry_after) if retry_after else 30.0 * (attempt + 1)
                    except (TypeError, ValueError):
                        wait = 30.0 * (attempt + 1)
                    time.sleep(min(wait + 2.0, 310.0))
                else:
                    time.sleep(min(2 ** attempt, 8))
            except (urllib.error.URLError, KeyError, TimeoutError) as e:
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
                       max_retries: int = 8, api_key: str = "", min_interval: float = 0.0):
    """Local (default): free, no API key. Install Ollama, `ollama pull
    <model>` first (e.g. `ollama pull llama3.1:8b`). CPU-only here, so this
    is slow -- fine for scripts/smoke_real_model.py, plan for real wall-clock
    time before running scripts/tune_dev.py / run_primary.py against it on
    the full dev/test split.

    Cloud (pass api_key + host="https://ollama.com"): no local install or
    GPU needed at all -- ollama.com hosts inference and bills against the
    account's session/weekly usage limits (visible on the ollama.com
    dashboard). Model names need the `:cloud` suffix (e.g.
    `gpt-oss:20b-cloud`, `qwen3.5:cloud`) -- see https://ollama.com/search?c=cloud
    for the current catalog. Same request/response shape as local, just adds
    an Authorization header and points at ollama.com instead of localhost.

    Learned directly running this: a run spanning multiple full 96-task
    pipelines (dev calibration + primary + oracle ablation + guardrail eval,
    x2 models) hit HTTP 429 partway through -- the original max_retries=2
    with a flat 2s sleep (fine for a flaky local server) gave up almost
    immediately on a real rate limit instead of honoring the dashboard's
    stated reset window. Now mirrors openai_compatible_generate_fn's 429
    handling: read Retry-After (seconds) off the response if present, wait
    that long (capped at 310s) before the next attempt, and use more retries
    by default since a rate-limit reset can legitimately take a while."""

    last_call = [0.0]

    def generate(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(
            f"{host}/api/generate", data=payload, method="POST", headers=headers)
        if min_interval > 0:
            gap = min_interval - (time.time() - last_call[0])
            if gap > 0:
                time.sleep(gap)
        last_call[0] = time.time()
        last_err = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["response"]
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait = float(retry_after) if retry_after else 30.0 * (attempt + 1)
                    except (TypeError, ValueError):
                        wait = 30.0 * (attempt + 1)
                    time.sleep(min(wait + 2.0, 310.0))
                else:
                    time.sleep(min(2 ** attempt, 8))
            except (urllib.error.URLError, KeyError, TimeoutError) as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(
            f"ollama generate_fn failed after {max_retries} attempts (is `ollama serve` "
            f"running and is '{model}' pulled? or has the ollama.com usage limit been hit -- "
            f"check the dashboard's session/weekly reset window): {last_err}")

    return generate


def _make_json_complete_stopping_criteria(tok, prompt_len: int):
    """Stop generation as soon as the text generated so far contains a
    complete, balanced top-level JSON array/object -- small CPU models here
    run at only ~5-7 tok/s and, observed directly, do NOT emit an EOS token
    on their own for these prompts (they ramble past a complete JSON answer
    for the full token budget). Without this, every call burns the entire
    max_new_tokens allowance regardless of how short the actual answer is,
    which is the dominant cost at 120-task scale on CPU. Checked every few
    tokens (not every token) since decoding + bracket-scanning the whole
    running text on every step would itself add meaningful overhead."""
    from transformers import StoppingCriteria, StoppingCriteriaList

    class _JSONComplete(StoppingCriteria):
        def __init__(self):
            self.check_every = 4
            self.steps = 0

        def __call__(self, input_ids, scores, **kwargs) -> bool:
            self.steps += 1
            if self.steps % self.check_every != 0:
                return False
            text = tok.decode(input_ids[0][prompt_len:], skip_special_tokens=True)
            start = None
            for i, ch in enumerate(text):
                if ch in "{[":
                    start = i
                    break
            if start is None:
                return False
            depth, in_str, esc = 0, False, False
            for c in text[start:]:
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                    continue
                if c == '"':
                    in_str = True
                elif c in "{[":
                    depth += 1
                elif c in "}]":
                    depth -= 1
                    if depth == 0:
                        return True  # balanced top-level structure closed
            return False

    return StoppingCriteriaList([_JSONComplete()])


def hf_local_generate_fn(model_id: str, max_new_tokens: int = 200, temperature: float = 0.0):
    """Local transformers inference. Loads once per process (module-level
    cache) since a real model load takes real time. Keep model_id small (e.g.
    'Qwen/Qwen2.5-0.5B-Instruct', 'HuggingFaceTB/SmolLM2-360M-Instruct') --
    this is CPU-only. Stops as soon as a complete JSON value has been emitted
    (see _make_json_complete_stopping_criteria) rather than always burning
    the full max_new_tokens budget.

    temperature=0.0 (the default, used for every main run) is greedy/
    deterministic. temperature>0 enables sampling -- ONLY for
    scripts/robustness_subset.py's stochastic-repetition check (plan section
    11); every dev-calibration and primary test-split run must stay at 0."""

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
        prompt_len = inputs["input_ids"].shape[1]
        stopping = _make_json_complete_stopping_criteria(tok, prompt_len)
        gen_kwargs = dict(max_new_tokens=max_new_tokens, pad_token_id=tok.eos_token_id,
                          stopping_criteria=stopping)
        if temperature > 0:
            gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.95)
        else:
            gen_kwargs.update(do_sample=False, temperature=None, top_p=None)
        with torch.no_grad():
            out = model.generate(**inputs, **gen_kwargs)
        new_tokens = out[0][prompt_len:]
        return tok.decode(new_tokens, skip_special_tokens=True)

    return generate


def build_agent(backend: str, model: str, base_url: str = "", api_key_env: str = "",
                host: str = "http://localhost:11434", temperature: float = 0.0):
    """Shared factory used by smoke_real_model.py / tune_dev.py / run_primary.py
    so all three scripts accept the same --backend/--model/... flags.

    temperature=0.0 (default) is deterministic/greedy -- required for every
    dev-calibration and primary test-split run. Only
    scripts/robustness_subset.py's stochastic-repetition check (plan section
    11) should ever pass temperature>0."""
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
        # GEN_MIN_INTERVAL (seconds) paces sustained runs under a free-tier
        # burst limit without a code change -- set it for a full grid, leave it
        # unset (0) for a one-off smoke call.
        min_interval = float(os.environ.get("GEN_MIN_INTERVAL", "0"))
        gen = openai_compatible_generate_fn(base_url=base_url, api_key=api_key,
                                            model=model, min_interval=min_interval,
                                            temperature=temperature)
    elif backend == "ollama":
        # OLLAMA_API_KEY set + host pointed at https://ollama.com -> cloud
        # inference (no local install/GPU needed); unset + default localhost
        # host -> the original local-only path, api_key="" sends no auth
        # header, exactly the prior behavior.
        ollama_key = os.environ.get("OLLAMA_API_KEY", "")
        ollama_min_interval = float(os.environ.get("GEN_MIN_INTERVAL", "0"))
        gen = ollama_generate_fn(model=model, host=host, temperature=temperature,
                                 api_key=ollama_key, min_interval=ollama_min_interval)
    elif backend == "hf_local":
        gen = hf_local_generate_fn(model_id=model, temperature=temperature)
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
