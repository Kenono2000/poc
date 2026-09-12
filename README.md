# PoC Workspace

This repository contains various Proof of Concept (PoC) projects organized by category.

## Structure

- `apps/`: Functional applications and integrated PoCs.
- `libs/`: Shared libraries and utilities.
- `scripts/`: Task-specific scripts (JS, Python).
- `tools/`: Infrastructure and maintenance scripts (PowerShell).

## Getting Started

### Prerequisites
- Node.js
- Python 3.10+
- PowerShell 7+

### Global Setup
1. Copy `.env.example` to `.env` and fill in the required keys.
2. It is recommended to use `uv` for Python dependency management.
3. Install the shared library in editable mode to use it across projects:
   ```powershell
   pip install -e libs/py-libraries
   ```

## Projects

### Apps
- **firestore-export**: Tools for exporting/importing Firestore data.
- **py-pgvector-local**: Local RAG implementation using Postgres and pgvector.
- **py-training**: Machine learning and LLM training scripts.

### Scripts
- **js-scripts**: Bookmark management and other JS utilities.
- **py-scripts**: AI agents and LLM experimentation.

## Maintenance
Maintenance scripts can be found in `tools/ps-scripts/`.
