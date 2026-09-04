# CrewAI Combined Workflows

This project combines multiple CrewAI workflows into a single manageable project.

## Workflows

1. **AI Agent Frameworks Research & Article**: Researches latest AI agent trends and writes an article.
2. **CrewAI News Research**: Searches for the latest news about CrewAI.
3. **Drive Relocation Analyzer**: Analyzes C: drive for relocatable items.
4. **LinkedIn Job Search**: Searches for Principal/Staff AI Platform roles on LinkedIn.

## Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Usage

Run the interactive CLI:
```bash
python src/main.py
```

Or via the installed script:
```bash
crewai-pro
```
