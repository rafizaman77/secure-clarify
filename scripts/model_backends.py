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
    out on but didn't.

    A FRESH single-use executor per call (not a shared module-level pool) is
    deliberate: confirmed directly (a 9h47m guardrail_eval.py hang, live
    `lsof` showing 19 leaked CLOSE_WAIT sockets and 0 active connections) that
    a shared pool degrades over a long run -- each permanently-stuck call
    consumes one of its worker threads forever, and once enough of those
    accumulate every subsequent call queues behind dead workers and never
    even starts, regardless of how the retry loop above it behaves. A
    throwaway executor means a stuck call only ever strands its own thread,
    never blocks unrelated future calls."""
    # No `with` here -- ThreadPoolExecutor.__exit__ calls shutdown(wait=True),
    # which would block on exactly the stuck thread this function exists to
    # not wait for. shutdown(wait=False) lets a stuck worker be abandoned
    # (leaked, not blocking) instead of hanging the caller.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        lambda: urllib.request.urlopen(req, timeout=socket_timeout).read())
    try:
        return future.result(timeout=hard_timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

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
    trip the burst limit less often.

    OpenAI's own API (as opposed to Groq/Together/Fireworks/OpenRouter, which
    all still accept the original field) rejects `max_tokens` on its current
    model lineup (gpt-5.x, o-series) with a 400 asking for
    `max_completion_tokens` instead -- confirmed directly against
    api.openai.com. Detected from base_url so every other provider's
    already-published behavior is untouched."""

    last_call = [0.0]  # wall-clock of the previous request start (for min_interval)
    token_field = "max_completion_tokens" if "api.openai.com" in base_url else "max_tokens"

    def generate(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            token_field: max_tokens,
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


def anthropic_generate_fn(api_key: str, model: str, temperature: float = 0.0,
                          max_tokens: int = 512, timeout: float = 60.0,
                          max_retries: int = 8, min_interval: float = 0.0,
                          base_url: str = "https://api.anthropic.com/v1/messages"):
    """Claude's native Messages API -- NOT the OpenAI-compatible shape that
    openai_compatible_generate_fn handles (Anthropic has no such endpoint for
    chat completions). Differs in three ways that matter here: the auth
    header is `x-api-key` (not `Authorization: Bearer`) plus a required
    `anthropic-version` header, the request has no `messages[].role="system"`
    (there's a separate top-level `system` field, unused here since every
    caller already puts its full instructions in the single user-turn
    prompt), and the response's text lives at `content[0]["text"]`, not
    `choices[0]["message"]["content"]`. Same retry/hard-timeout treatment as
    the OpenAI-compatible path for the same reason: urllib's own socket
    timeout is not reliable on this platform (see
    _urlopen_hard_timeout's docstring), and a 429 carries a `Retry-After`
    worth honoring rather than hammering."""

    last_call = [0.0]

    def generate(prompt: str) -> str:
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Claude 4.6+/5-family models (e.g. claude-sonnet-5) reject an explicit
        # temperature=0.0 outright ("`temperature` is deprecated for this
        # model") -- confirmed directly against api.anthropic.com. Every
        # caller here uses temperature=0.0 as its "deterministic" default, so
        # omit the field entirely for that case rather than sending a value
        # these models 400 on. Explicitly disable adaptive thinking too: these
        # models think by default, which (a) breaks the "greedy decoding"
        # comparability with every other backend's temperature=0 runs, (b)
        # non-deterministically reorders `content` (a `thinking` block can
        # land before the `text` block), and (c) burns extra tokens/latency
        # across a ~2000-call grid for no benefit here. A caller that
        # explicitly wants sampling (temperature > 0, e.g.
        # robustness_subset.py) still gets temperature sent and thinking left
        # on its model default.
        if temperature != 0.0:
            body["temperature"] = temperature
        else:
            body["thinking"] = {"type": "disabled"}
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            base_url, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                     "x-api-key": api_key,
                     "anthropic-version": "2023-06-01",
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
                # `content` is not always [text_block] -- a thinking-enabled
                # response (or a future block type) can put non-text blocks
                # first, so scan for the first "text" block rather than
                # indexing content[0] directly.
                for block in data["content"]:
                    if block.get("type") == "text":
                        return block["text"]
                raise KeyError("no text block in response content")
            except concurrent.futures.TimeoutError as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))
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
            except (urllib.error.URLError, KeyError, IndexError, TimeoutError) as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"anthropic generate_fn failed after {max_retries} attempts: {last_err}")

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
                # NOT a bare urlopen: confirmed directly (2026-07-27) that this
                # path hung with ZERO output and no exception for 4+ minutes on
                # a live run, exactly the failure openai_compatible_generate_fn's
                # docstring already documented for urllib on this platform --
                # its own socket `timeout=` parameter does not reliably fire.
                # This path used a bare `with urllib.request.urlopen(req,
                # timeout=timeout)` with no hard wall-clock backstop, so a hang
                # here had NO recovery at all (not "eventually times out slowly" --
                # literally forever). _urlopen_hard_timeout is the same fix
                # already relied on for the Groq/OpenAI path; this brings Ollama
                # Cloud calls up to the same protection.
                raw = _urlopen_hard_timeout(req, socket_timeout=timeout, hard_timeout=timeout + 10)
                data = json.loads(raw.decode("utf-8"))
                return data["response"]
            except concurrent.futures.TimeoutError as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))
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
        # gpt-5.x's JSON responses run noticeably more verbose per hypothesis
        # than the open-weight models this default was tuned against (long
        # prose-y field values rather than short ones) -- confirmed directly:
        # the 512-token default truncates mid-object on a k=5 sample_intents
        # call, _extract_json/_repair_json can't recover a cut-off string, and
        # the silent all-empty-hypothheses fallback then reads as "zero
        # information gain" on every task regardless of lambda. Only bump this
        # for the real OpenAI endpoint so Groq/Together/etc keep their
        # already-validated 512 default unchanged.
        #
        # Gemini needs a much larger budget again, for a different reason:
        # its 3.x models always think before answering, those thinking tokens
        # are billed against max_tokens, and they are NOT counted in the
        # response's `completion_tokens` -- so an overrun is invisible in the
        # usage field and shows up only as finish_reason="length". Measured
        # directly against gemini-3.6-flash on a k=5 sample_intents-shaped
        # prompt: thinking alone runs 1100-1400 tokens, so at the 512 default
        # the model burns ~487 of it thinking, emits 21 tokens of content, and
        # returns truncated JSON every single time. 4096 leaves ~1900 tokens
        # of headroom over the observed worst case (thinking + ~900 tokens of
        # content) and returns finish_reason="stop". Note thinking cannot be
        # switched off on this endpoint -- `reasoning_effort: "none"` is
        # rejected with a 400, and "low" does not reliably reduce it.
        if "api.openai.com" in base_url:
            openai_max_tokens = 1536
        elif "generativelanguage.googleapis.com" in base_url:
            openai_max_tokens = 4096
        else:
            openai_max_tokens = 512
        gen = openai_compatible_generate_fn(base_url=base_url, api_key=api_key,
                                            model=model, min_interval=min_interval,
                                            temperature=temperature,
                                            max_tokens=openai_max_tokens)
    elif backend == "anthropic":
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise SystemExit(
                f"Set {api_key_env} in your environment first "
                f"(export {api_key_env}=... / $env:{api_key_env}='...').")
        min_interval = float(os.environ.get("GEN_MIN_INTERVAL", "0"))
        # Same verbosity problem the api.openai.com branch above documents, and
        # worse here: measured directly against claude-sonnet-5, a k=3
        # sample_intents call already emits ~450 output tokens, so the real
        # k=5 call (estimators.estimate_info_gain's default) overruns the
        # 512-token default and gets cut mid-object. _extract_json cannot
        # repair a truncated string, and its all-empty-hypotheses fallback
        # reads as "zero information gain" on every task regardless of
        # lambda -- a degenerate calibration that looks like a real finding.
        gen = anthropic_generate_fn(api_key=api_key, model=model,
                                    min_interval=min_interval, temperature=temperature,
                                    max_tokens=2048)
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
    ap.add_argument("--backend", choices=["scripted", "openai", "anthropic", "ollama", "hf_local"],
                    default="scripted")
    ap.add_argument("--model", default="ScriptedAgent")
    ap.add_argument("--base-url", default="https://api.groq.com/openai/v1/chat/completions")
    ap.add_argument("--api-key-env", default="GROQ_API_KEY")
    ap.add_argument("--host", default="http://localhost:11434")
