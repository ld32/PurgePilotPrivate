# PurgePilot

Scan data folders and use a local or remote **LLM server** to estimate how
confident each file or sub-folder can be safely purged.

---

## How it works

1. **Scan** – PurgePilot walks one or more directories and collects metadata
   (path, size, last-modified timestamp) for every file and sub-folder.
2. **Ask** – The full file list is sent as a prompt to any
   [OpenAI-compatible](https://platform.openai.com/docs/api-reference/chat)
   chat-completions endpoint (local [Ollama](https://ollama.com), OpenAI, etc.).
3. **Estimate** – The LLM returns a confidence score (`0.0` = keep,
   `1.0` = definitely purge) and a short reason for each entry.
4. **Report** – PurgePilot prints a ranked text report (or machine-readable
   JSON) so you can decide what to delete.

---

## Installation

```bash
pip install .
```

Or install with development dependencies (pytest, etc.):

```bash
pip install ".[dev]"
```

---

## Local LLM server (Ollama – CPU-only setup)

PurgePilot works with any OpenAI-compatible endpoint, but the easiest
self-hosted option is [Ollama](https://ollama.com).  The instructions
below cover a **CPU-only** setup (no NVIDIA/AMD GPU required).

### 1 – Install Ollama

| Platform | Command |
|---|---|
| **Linux** | `curl -fsSL https://ollama.com/install.sh \| OLLAMA_INSTALL_DIR=~/.local sh` |
| **macOS** | Download the `.dmg` from <https://ollama.com/download> and drag it to Applications |
| **Windows** | Download the installer from <https://ollama.com/download> and run it |

### 2 – Choose a model that fits your RAM

When running on CPU, the model weights must fit entirely in system RAM.
Use the table below as a starting point:

| Available RAM | Recommended model | Approx. size on disk |
|---|---|---|
| 8 GB | `phi3:mini` (3.8 B) | ~2.3 GB |
| 16 GB | `llama3.2:3b` (3 B) | ~2.0 GB |
| 32 GB | `llama3.1:8b` (8 B) | ~4.7 GB |
| 64 GB+ | `llama3.1:70b-instruct-q4_K_M` (70 B, 4-bit) | ~40 GB |

> **Tip:** 4-bit quantised models (the default `q4_K_M` variants) use
> roughly half the RAM of their full-precision counterparts and run at
> an acceptable speed on modern CPUs.

Pull the model before first use:

```bash
ollama pull phi3:mini          # replace with your chosen model
```

### 3 – Tune memory usage

Set these environment variables **before** starting Ollama to control
how much RAM it may consume:

```bash
# Keep only one model loaded at a time (saves RAM when you switch models)
export OLLAMA_MAX_LOADED_MODELS=1

# Process one request at a time (reduces peak RAM on low-memory hosts)
export OLLAMA_NUM_PARALLEL=1

# Unload the model from RAM after 5 minutes of inactivity
export OLLAMA_KEEP_ALIVE=5m
```

On **Windows** set these as user environment variables via
*System Properties → Advanced → Environment Variables*, or prepend them
to the `ollama serve` command in PowerShell:

```powershell
$env:OLLAMA_MAX_LOADED_MODELS=1
$env:OLLAMA_NUM_PARALLEL=1
$env:OLLAMA_KEEP_ALIVE="5m"
ollama serve
```

### 4 – Start the server

```bash
ollama serve
```

Ollama listens on `http://localhost:11434` by default.  Leave this
terminal open (or run it as a system service) while using PurgePilot.

### 5 – Point PurgePilot at the local server

```bash
purge-pilot /path/to/data \
  --api-url http://localhost:11434/v1 \
  --model phi3:mini
```

---

## Usage

```
purge-pilot [OPTIONS] DIR [DIR ...]
```

### Examples

Scan a single directory using a local Ollama server:

```bash
purge-pilot /mnt/data/backups --api-url http://localhost:11434/v1 --model llama3
```

Scan multiple directories and output JSON:

```bash
purge-pilot /tmp/logs /var/cache \
  --api-url http://localhost:11434/v1 \
  --model llama3 \
  --output json
```

Use the OpenAI API with an API key from an environment variable:

```bash
export PURGE_PILOT_API_KEY="sk-..."
purge-pilot ~/Downloads --api-url https://api.openai.com/v1 --model gpt-4o
```

### Environment variables

| Variable | Description |
|---|---|
| `PURGE_PILOT_API_URL` | Default value for `--api-url` |
| `PURGE_PILOT_MODEL` | Default value for `--model` |
| `PURGE_PILOT_API_KEY` | Default value for `--api-key` |

### All options

| Option | Default | Description |
|---|---|---|
| `DIR` | *(required)* | One or more directories to scan |
| `--api-url URL` | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `--model NAME` | `llama3` | LLM model name |
| `--api-key TOKEN` | *(none)* | Bearer token for the API |
| `--threshold FLOAT` | `0.7` | Confidence cut-off for "high risk" summary |
| `--max-depth INT` | `10` | Maximum recursion depth |
| `--include-hidden` | *(off)* | Include hidden files/dirs (`.` prefix) |
| `--output text\|json` | `text` | Output format |
| `--timeout SECONDS` | `120` | HTTP request timeout |
| `-v, --verbose` | *(off)* | Enable debug logging |

---

## Sample output

```
Scanning /mnt/data/backups …
  Found 42 entries (15,728,640,000 bytes). Querying LLM …

Purge confidence report for: /mnt/data/backups
------------------------------------------------------------------------
🔴  [████████████████████] 0.97  2019-full-backup.tar.gz
        4-year-old full backup, almost certainly superseded by newer snapshots.
🔴  [███████████████░░░░░] 0.82  logs/access.log.2021
        Rotated log file from 2021, no longer needed for operations.
🟢  [███░░░░░░░░░░░░░░░░░] 0.18  datasets/current_month.csv
        Actively-used dataset modified recently.
...

Summary: 15 of 42 entries above confidence threshold 0.70
```

---

## Running tests

```bash
pytest
```

---

## Project layout

```
purge_pilot/
  __init__.py      – package marker
  scanner.py       – recursive directory walker
  llm_client.py    – OpenAI-compatible LLM API client
  main.py          – CLI entry point
tests/
  test_scanner.py
  test_llm_client.py
  test_main.py
pyproject.toml
```
