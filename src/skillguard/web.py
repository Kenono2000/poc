"""Embedded FastAPI web dashboard for SkillGuard."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from skillguard.analyzer import analyze
from skillguard.scanner import scan_skills

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SkillGuard Dashboard</title>
  <style>
    :root { --bg: #080c14; --card: #0f1623; --border: #1e293b; --text: #e2e8f0; --muted: #94a3b8; --accent: #06b6d4; --warn: #f59e0b; --crit: #ef4444; --ok: #10b981; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); padding: 16px; line-height: 1.4; }
    header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 14px; }
    h1 { font-size: 1.15rem; color: var(--accent); }
    .stats { display: flex; gap: 12px; font-size: 0.85rem; }
    .stat { background: var(--card); border: 1px solid var(--border); padding: 4px 10px; border-radius: 6px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
    .card h2 { font-size: 0.95rem; margin-bottom: 8px; color: var(--text); }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 600; }
    .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; }
    .critical { background: rgba(239,68,68,0.18); color: var(--crit); }
    .warning { background: rgba(245,158,11,0.18); color: var(--warn); }
    .info { background: rgba(6,182,212,0.18); color: var(--accent); }
    button { background: var(--accent); color: #080c14; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>SkillGuard — Skill & Conflict Monitor</h1>
    <div class="stats">
      <div class="stat">Skills: <strong id="s-count">-</strong></div>
      <div class="stat">Tokens: <strong id="t-count">-</strong></div>
      <div class="stat">Conflicts: <strong id="c-count">-</strong></div>
      <div class="stat">Predictions: <strong id="p-count">-</strong></div>
      <button onclick="loadData()">Refresh</button>
    </div>
  </header>
  <div class="grid">
    <div class="card">
      <h2>Conflicts</h2>
      <table><thead><tr><th>Severity</th><th>Type</th><th>Skills</th><th>Details</th></tr></thead><tbody id="conflicts-body"></tbody></table>
    </div>
    <div class="card">
      <h2>Predicted Problems</h2>
      <table><thead><tr><th>Severity</th><th>Risk</th><th>Target</th><th>Details</th></tr></thead><tbody id="predictions-body"></tbody></table>
    </div>
  </div>
  <div class="card">
    <h2>Discovered Skills</h2>
    <table><thead><tr><th>Scope</th><th>Name</th><th>Tokens</th><th>Guardrail</th><th>Description</th></tr></thead><tbody id="skills-body"></tbody></table>
  </div>
  <script>
    async function loadData() {
      const res = await fetch('/api/scan');
      const data = await res.json();
      document.getElementById('s-count').textContent = data.skills.length;
      document.getElementById('t-count').textContent = data.total_tokens;
      document.getElementById('c-count').textContent = data.conflicts.length;
      document.getElementById('p-count').textContent = data.predictions.length;

      document.getElementById('conflicts-body').innerHTML = data.conflicts.length
        ? data.conflicts.map(c => `<tr><td><span class="badge ${c.severity}">${c.severity}</span></td><td>${c.conflict_type}</td><td>${c.skills.join(', ')}</td><td>${c.message}</td></tr>`).join('')
        : '<tr><td colspan="4" style="color:var(--ok)">No conflicts detected.</td></tr>';

      document.getElementById('predictions-body').innerHTML = data.predictions.length
        ? data.predictions.map(p => `<tr><td><span class="badge ${p.severity}">${p.severity}</span></td><td>${p.risk_score}</td><td>${p.target}</td><td>${p.message}</td></tr>`).join('')
        : '<tr><td colspan="4" style="color:var(--ok)">No problems predicted.</td></tr>';

      document.getElementById('skills-body').innerHTML = data.skills.map(s =>
        `<tr><td>${s.scope}</td><td><strong>${s.name}</strong></td><td>${s.token_count}</td><td>${s.has_negative_guardrail ? 'yes' : 'no'}</td><td>${s.description.slice(0, 100)}</td></tr>`
      ).join('');
    }
    loadData();
  </script>
</body>
</html>"""


def create_app(project_dir: Path) -> FastAPI:
    """Create the embedded FastAPI application."""
    web_app = FastAPI(title="SkillGuard")

    @web_app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return DASHBOARD_HTML

    @web_app.get("/api/scan")
    def api_scan() -> dict:
        skills = scan_skills(project_dir=project_dir)
        return analyze(skills).to_dict()

    return web_app
