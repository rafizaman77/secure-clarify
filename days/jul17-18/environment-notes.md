# Environment notes: why `.venv_model/` exists

The system Python (`C:\Users\rafza\AppData\Local\Programs\Python\Python311`)
has `numpy==2.4.2` installed alongside a `scikit-learn` build compiled against
a different numpy ABI. Importing `transformers.AutoModelForCausalLM` there
fails:

```
File "sklearn\utils\murmurhash.pyx", line 1, in init sklearn.utils.murmurhash
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

`transformers`' generation utilities import `sklearn` transitively (for
assisted-generation candidate scoring), so this breaks even though nothing in
this project touches scikit-learn directly.

**Decision:** rather than upgrade/downgrade packages in the system Python (a
shared environment outside this project's control — doing so could break
other things depending on it), created an isolated `.venv_model/` scoped to
this repo, with its own pinned `torch`/`transformers`/`numpy`/`scikit-learn`.
`.venv_model/` is gitignored. Run real-model scripts through it:

```bash
.venv_model/Scripts/python.exe scripts/smoke_real_model.py --backend hf_local --model Qwen/Qwen2.5-0.5B-Instruct
.venv_model/Scripts/python.exe scripts/tune_dev.py --tasks tasks/main_120.json --backend hf_local --model Qwen/Qwen2.5-0.5B-Instruct
.venv_model/Scripts/python.exe scripts/run_primary.py --tasks tasks/main_120.json --backend hf_local --model Qwen/Qwen2.5-0.5B-Instruct
```

Everything else in the repo (ScriptedAgent runs, the API/Ollama backends,
`test_smoke.py`) continues to run fine on the system Python — `.venv_model/`
is only needed for the `--backend hf_local` route.

**Update:** the actual held-out numbers ended up coming from `--backend
ollama` (`ollama:mistral-nemo:12b`), which needs neither `.venv_model/` nor
any of the above — Ollama runs as its own local server outside Python
entirely. `hf_local` / `.venv_model/` remain here as a documented fallback
(no Ollama install, no API key, just Hugging Face network access) for
whoever runs the next model family in Jul 22-23.
