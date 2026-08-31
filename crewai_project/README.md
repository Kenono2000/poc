# crewai-pro

Four standalone CrewAI workflows behind one CLI, structured as a proper Python
project (src layout, real package, real entry point).

## Workflows

| # | Workflow                  | Flag                       | Agents                                  |
|---|---------------------------|----------------------------|-----------------------------------------|
| 1 | AI Agent Frameworks       | `WORKFLOW_AI_RESEARCH`     | researcher, writer                      |
| 2 | CrewAI News Research      | `WORKFLOW_CREWAI_NEWS`     | web_researcher                          |
| 3 | Drive Relocation Analyzer | `WORKFLOW_RELOCATION`      | drive_analyst, relocation_specialist, report_writer |
| 4 | LinkedIn Job Search       | `WORKFLOW_LINKEDIN_JOBS`   | job_researcher                          |

Each workflow is independently gated by an env var so you only enable what you need.

## Layout

```
crewai_project/
├── pyproject.toml
├── .env.example
├── src/crewai_pro/
│   ├── __init__.py
│   ├── config.py              # env loading + workflow flags
│   ├── cli.py                 # `crewai-pro` entry point + REPL
│   ├── tools/
│   │   ├── __init__.py
│   │   └── drive_relocation.py
│   ├── agents/
│   │   ├── __init__.py        # re-exports all agents
│   │   ├── research.py        # researcher, writer
│   │   ├── news.py            # web_researcher
│   │   ├── relocation.py      # drive_analyst, relocation_specialist, report_writer
│   │   └── jobs.py            # job_researcher
│   └── workflows/
│       ├── __init__.py
│       ├── ai_research.py
│       ├── crewai_news.py
│       ├── relocation.py
│       └── linkedin_jobs.py
└── tests/
```

## Install

```bash
cd crewai_project
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .
cp .env.example .env            # fill in API keys + toggle workflows
```

## Run

```bash
crewai-pro                      # interactive REPL over enabled workflows
crewai-pro --list               # show enabled workflows
crewai-pro --run 3              # run workflow #3 non-interactively
crewai-pro --all                # run every enabled workflow in sequence
```

## Programmatic use

```python
from crewai_pro.workflows import get_workflow

wf = get_workflow("relocation")  # raises if disabled / unknown
result = wf.run()
```