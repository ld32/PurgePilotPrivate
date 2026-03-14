# PurgePilot Configuration

## AI Prompt

This is the prompt used by the AI to determine which files and folders should be purged. Customize this prompt to guide the AI's decision-making process.

```
You are an AI assistant tasked with analyzing a codebase to identify files and folders that can be safely purged. Consider factors such as:
- Unused imports or dependencies
- Temporary files (e.g., logs, caches)
- Build artifacts
- Duplicate files
- Files not referenced in the codebase

For each file/folder, provide a confidence score (0-100) and a brief explanation. Only suggest purging if confidence is above 80.
```

## Important Data (Never Purge)

This section lists folders and files that should never be purged under any circumstances. These are critical to the project's functionality or integrity.

- purge_pilot/__init__.py
- pyproject.toml
- README.md
- LICENSE
- tests/ (entire directory)
- .git/ (if present)

## Recycle Bin Data (Move to Recycle Bin)

This section lists files and folders that should be moved to a recycle bin
location first, instead of being immediately hard-deleted.

- Downloads/
- old_exports/
- archive_staging/

## Recycle Bin Path

Set the destination path used for recycled items.
- .purgepilot/recycle_bin

## Trash Data (Always Delete)

This section lists folders and files that should always be deleted during the purge process. These are typically temporary, generated, or unnecessary files.

- __pycache__/
- *.pyc
- *.pyo
- .pytest_cache/
- build/
- dist/
- *.log
- *.tmp