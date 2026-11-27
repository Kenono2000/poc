# SkillGuard
Lightweight CLI and embedded web dashboard to manage global and project-specific agent skills, evaluate skill conflicts, and predict skill problems.
## Features
- **Skill Discovery**: Scans global (`~/.gemini/config/skills`, `~/.agents/skills`) and project (`.agent/skills`, `.gemini/skills`) `SKILL.md` files.
- **Conflict Evaluation**: Detects `name_collision`, `trigger_overlap`, and `rule_contradiction` across scopes.
- **Problem Prediction**: Flags `token_bloat`, `trigger_ambiguity`, `missing_guardrail`, and `brittle_path` issues.
- **Embedded Web Dashboard**: Local dark-mode UI served via FastAPI at `http://127.0.0.1:8765`.
## Installation
```powershell
# Local editable install (with dev tools)
python -m pip install -e ".[dev]"
# Or install on another machine via pipx
pipx install git+https://github.com/Kenono2000/poc.git
```
## Usage
```powershell
# List discovered skills
skillguard scan --project d:\src\poc
# Evaluate conflicts and predict problems
skillguard check --project d:\src\poc
# Launch the embedded web dashboard
skillguard ui --project d:\src\poc --port 8765
```
## Development
```powershell
python -m pytest -q
python -m ruff check --select E,W,F,I,B,S src tests
```
