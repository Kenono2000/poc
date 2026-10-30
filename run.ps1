<#
.SYNOPSIS
    Central Workspace Orchestrator for c:\src
.DESCRIPTION
    Unified management, service orchestration, testing, cleanup, and status reporting
    across workspace projects:
      - Enterprise RAG Stack (FastAPI, Streamlit UI, FastMCP, Pytest, Docker DB/Jaeger)
      - Abyssium Studio (Vite React dev, build, lint)
      - Ollama Local AI (deepseek-r1:8b)
      - Workspace Health & Port Monitor
      - Safe Multi-Project Clean & Environment Setup
.EXAMPLE
    .\poc\run.ps1                 # Interactive menu mode (enter option number)
    .\poc\run.ps1 status          # Overview of git, venv, docker, and active ports
    .\poc\run.ps1 api             # Run FastAPI backend (:8000)
    .\poc\run.ps1 ui              # Run Streamlit UI (:8501)
    .\poc\run.ps1 mcp             # Run FastMCP Gateway
    .\poc\run.ps1 mcp-ui          # Run FastMCP Inspector / Evaluate UI (Local Testing)
    .\poc\run.ps1 mcp-eval-ui     # Run FastMCP Evaluate UI (interactive tool evaluation)
    .\poc\run.ps1 test            # Run offline pytest suite (130 tests)
    .\poc\run.ps1 ingest          # Run document ingestion pipeline
    .\poc\run.ps1 docker-up       # Start Postgres 16 (pgvector) + Jaeger Badger
    .\poc\run.ps1 docker-down     # Stop docker compose services
    .\poc\run.ps1 studio          # Launch Abyssium Studio Vite dev server (:5173)
    .\poc\run.ps1 build           # Build Abyssium Studio production bundle
    .\poc\run.ps1 lint            # Run Abyssium Studio ESLint validation
    .\poc\run.ps1 ollama          # Run local Ollama AI session (deepseek-r1:8b)
    .\poc\run.ps1 activate        # Show Python venv activation command
    .\poc\run.ps1 clean           # Safely prune node_modules and pycache (excludes .venv)
    .\poc\run.ps1 setup           # Verify & install dependencies for Python and Node
    .\poc\run.ps1 help            # Display reference guide and available commands
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Action = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

# Workspace resolution (run.ps1 is located in <WorkspaceRoot>\poc)
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Get-Location }
$WorkspaceRoot = Split-Path -Parent $ScriptDir

# Fallback: if executed from within another subfolder or directly
if (-not (Test-Path (Join-Path $WorkspaceRoot "enterprise-rag-pgvector-rbac"))) {
    if (Test-Path (Join-Path $ScriptDir "enterprise-rag-pgvector-rbac")) {
        $WorkspaceRoot = $ScriptDir
    } elseif (Test-Path "c:\src\enterprise-rag-pgvector-rbac") {
        $WorkspaceRoot = "c:\src"
    }
}

# Python venv detection
$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"
$VenvFastMcp = Join-Path $WorkspaceRoot ".venv\Scripts\fastmcp.exe"
$VenvMcp = Join-Path $WorkspaceRoot ".venv\Scripts\mcp.exe"
$VenvActivate = Join-Path $WorkspaceRoot ".venv\Scripts\Activate.ps1"
$PythonCmd = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

# Menu definition mapping numbers to actions and descriptions
$MenuItems = [ordered]@{
    "1"  = @{ Action = "status";      Category = "Workspace Diagnostics"; Desc = "Workspace Status, Ports & Git Health" }
    "2"  = @{ Action = "api";         Category = "Enterprise RAG Stack";   Desc = "Start FastAPI Backend (uvicorn on :8000)" }
    "3"  = @{ Action = "ui";          Category = "Enterprise RAG Stack";   Desc = "Start Streamlit UI (streamlit on :8501)" }
    "4"  = @{ Action = "mcp";         Category = "Enterprise RAG Stack";   Desc = "Start FastMCP Gateway (python -m app.mcp)" }
    "5"  = @{ Action = "mcp-ui";      Category = "Enterprise RAG Stack";   Desc = "Start FastMCP Inspector / Evaluate UI (Local Testing)" }
    "6"  = @{ Action = "test";        Category = "Enterprise RAG Stack";   Desc = "Run Pytest Suite (130 offline tests)" }
    "7"  = @{ Action = "ingest";      Category = "Enterprise RAG Stack";   Desc = "Run Document Ingestion Pipeline" }
    "8"  = @{ Action = "docker-up";   Category = "Enterprise RAG Stack";   Desc = "Start Postgres 16 (pgvector) + Jaeger" }
    "9"  = @{ Action = "docker-down"; Category = "Enterprise RAG Stack";   Desc = "Stop Docker Compose Services" }
    "10" = @{ Action = "studio";      Category = "Abyssium Studio";        Desc = "Start Vite Dev Server (:5173)" }
    "11" = @{ Action = "build";       Category = "Abyssium Studio";        Desc = "Build Production Bundle (Vite)" }
    "12" = @{ Action = "lint";        Category = "Abyssium Studio";        Desc = "Run ESLint Validation" }
    "13" = @{ Action = "ollama";      Category = "Ollama Local AI";        Desc = "Run Local DeepSeek Model (deepseek-r1:8b)" }
    "14" = @{ Action = "activate";    Category = "Workspace Maintenance";  Desc = "Show Python venv Activation Command" }
    "15" = @{ Action = "clean";       Category = "Workspace Maintenance";  Desc = "Safely Prune node_modules & pycache" }
    "16" = @{ Action = "setup";       Category = "Workspace Maintenance";  Desc = "Verify & Install Python/Node Dependencies" }
    "17" = @{ Action = "help";        Category = "Workspace Maintenance";  Desc = "Display Reference Guide & Help" }
}

function Show-Header {
    param([string]$Title, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host "============================================================" -ForegroundColor $Color
}

function Show-InteractiveMenu {
    Show-Header "Workspace Orchestrator - Interactive Menu" "Cyan"
    Write-Host "Select an option by entering its number, or type the command name directly.`n" -ForegroundColor DarkGray

    $currentCategory = ""
    foreach ($entry in $MenuItems.GetEnumerator()) {
        $key = $entry.Key
        $item = $entry.Value
        if ($item.Category -ne $currentCategory) {
            $currentCategory = $item.Category
            Write-Host "[$currentCategory]" -ForegroundColor Yellow
        }
        $numStr = "[$($key.PadLeft(2))]".PadRight(6)
        $actionStr = "$($item.Action)".PadRight(13)
        Write-Host "  $numStr" -ForegroundColor Cyan -NoNewline
        Write-Host " $actionStr" -ForegroundColor DarkCyan -NoNewline
        Write-Host " : $($item.Desc)" -ForegroundColor White
    }
    Write-Host "`n  [ 0]   quit          : Exit menu`n" -ForegroundColor DarkGray
}

function Show-Help {
    Show-Header "Workspace Orchestrator - Available Commands" "Cyan"
    Write-Host "Usage: .\poc\run.ps1 [command] [extra arguments]" -ForegroundColor Yellow
    Write-Host "       .\poc\run.ps1 (without arguments launches interactive numbered menu)`n" -ForegroundColor DarkGray

    Write-Host "Enterprise RAG Stack (enterprise-rag-pgvector-rbac):" -ForegroundColor Green
    Write-Host "  api, rag-api       Start FastAPI backend (uvicorn app.main:app on :8000)"
    Write-Host "  ui, streamlit      Start Streamlit UI (streamlit run streamlit_app.py on :8501)"
    Write-Host "  mcp, rag-mcp       Start FastMCP Gateway (python -m app.mcp)"
    Write-Host "  mcp-ui, inspector  Start FastMCP Inspector / Evaluate UI (local web testing)"
    Write-Host "  mcp-eval-ui        Start FastMCP Evaluate UI (alias for mcp-ui)"
    Write-Host "  test, rag-test     Run pytest test suite (accepts pytest args, e.g. -k rbac)"
    Write-Host "  ingest, rag-ingest Run data ingestion pipeline (python scripts/ingest.py)"
    Write-Host "  db, docker-up      Start PostgreSQL 16 (pgvector) + Jaeger (docker compose up -d)"
    Write-Host "  docker-down        Stop docker compose services"

    Write-Host "`nAbyssium Studio (abyssium-studio):" -ForegroundColor Green
    Write-Host "  studio, web        Start Vite dev server (npm run dev on :5173)"
    Write-Host "  build              Build production bundle (npm run build)"
    Write-Host "  lint               Run ESLint validation (npm run lint)"

    Write-Host "`nOllama & AI Runtime:" -ForegroundColor Green
    Write-Host "  ollama             Run local DeepSeek model (deepseek-r1:8b --verbose)"

    Write-Host "`nWorkspace Maintenance:" -ForegroundColor Green
    Write-Host "  status, st         Show git status, active listening ports, venv, and containers"
    Write-Host "  setup              Verify & install dependencies for Python and Node projects"
    Write-Host "  clean              Safely purge node_modules and pycache (excludes .venv)"
    Write-Host "  help, ?            Display this reference guide`n"
}

function Start-MenuLoop {
    while ($true) {
        Show-InteractiveMenu
        try {
            $selection = Read-Host "Enter option number [0-$($MenuItems.Count), or 'q' to quit]"
        } catch {
            break
        }
        if ($null -eq $selection) { break }
        $selection = $selection.Trim()
        if ([string]::IsNullOrWhiteSpace($selection)) { continue }

        if ($selection -in "0", "q", "quit", "exit") {
            Write-Host "`nExiting Workspace Orchestrator. Goodbye!" -ForegroundColor Cyan
            break
        }

        $chosenAction = $null
        if ($MenuItems.Contains($selection)) {
            $chosenAction = $MenuItems[$selection].Action
        } else {
            # Check if user entered action name or alias directly
            $chosenAction = $selection
        }

        Invoke-WorkspaceAction -TargetAction $chosenAction -Arguments @()

        Write-Host ""
        try {
            $resume = Read-Host "Press [Enter] to return to menu (or 'q' to quit)"
        } catch {
            break
        }
        if ($resume -and ($resume.Trim().ToLower() -in "q", "quit", "exit")) {
            Write-Host "`nExiting Workspace Orchestrator. Goodbye!" -ForegroundColor Cyan
            break
        }
    }
}

function Invoke-WorkspaceAction {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetAction,

        [string[]]$Arguments = @()
    )

    if ($MenuItems.Contains($TargetAction)) {
        $TargetAction = $MenuItems[$TargetAction].Action
    }

    if ($TargetAction -in "0", "q", "quit", "exit") {
        Write-Host "Exiting Workspace Orchestrator." -ForegroundColor Cyan
        return
    }

    # Normalize composite actions (e.g. 'mcp evaluate ui', 'mcp eval ui', 'mcp ui')
    if ($TargetAction.ToLower() -in "mcp", "rag-mcp" -and $Arguments) {
        $joined = ($Arguments -join " ").ToLower().Trim()
        if ($joined -in "evaluate ui", "eval ui", "evaluate", "eval", "ui", "inspector") {
            $TargetAction = "mcp-ui"
            $Arguments = @()
        }
    }

    $ExtraArgs = $Arguments

    switch ($TargetAction.ToLower()) {
    # -------------------------------------------------------------
    # Workspace Status & Diagnostics
    # -------------------------------------------------------------
    { $_ -in "status", "st" } {
        Show-Header "Workspace Status & Environment Health" "Cyan"
        Write-Host "Workspace Root : $WorkspaceRoot" -ForegroundColor DarkGray
        Write-Host "Timestamp      : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray

        # 1. Projects & Git Status
        Write-Host "`n[Projects & Repositories]" -ForegroundColor Yellow
        $Projects = @("enterprise-rag-pgvector-rbac", "abyssium-studio", "suntiq-product", "poc")
        foreach ($proj in $Projects) {
            $projPath = Join-Path $WorkspaceRoot $proj
            if (Test-Path $projPath) {
                $isGit = Test-Path (Join-Path $projPath ".git")
                if ($isGit) {
                    $branch = (git -C $projPath branch --show-current 2>$null)
                    if (-not $branch) { $branch = "(detached)" }
                    $dirty = (git -C $projPath status --porcelain 2>$null)
                    $statusText = if ($dirty) { "[modified]" } else { "[clean]" }
                    $statusColor = if ($dirty) { "Yellow" } else { "Green" }
                    Write-Host "  * " -NoNewline
                    Write-Host "$($proj.PadRight(32))" -ForegroundColor White -NoNewline
                    Write-Host "git: ($branch) " -ForegroundColor Cyan -NoNewline
                    Write-Host $statusText -ForegroundColor $statusColor
                } else {
                    Write-Host "  * " -NoNewline
                    Write-Host "$($proj.PadRight(32))" -ForegroundColor White -NoNewline
                    Write-Host "(no git)" -ForegroundColor DarkGray
                }
            }
        }

        # 2. Runtimes
        Write-Host "`n[Runtimes]" -ForegroundColor Yellow
        if (Test-Path $VenvPython) {
            $pyVer = & $VenvPython --version 2>&1
            Write-Host "  * Python (.venv)               : " -NoNewline
            Write-Host "$pyVer ($VenvPython)" -ForegroundColor Green
        } else {
            Write-Host "  * Python (.venv)               : " -NoNewline
            Write-Host "NOT FOUND at $VenvPython" -ForegroundColor Red
        }

        $nodeVer = (node --version 2>$null)
        if ($nodeVer) {
            Write-Host "  * Node.js                      : " -NoNewline
            Write-Host "$nodeVer" -ForegroundColor Green
        } else {
            Write-Host "  * Node.js                      : " -NoNewline
            Write-Host "NOT FOUND" -ForegroundColor DarkGray
        }

        # 3. Active Ports
        Write-Host "`n[Services & Port Listeners]" -ForegroundColor Yellow
        $ListeningPorts = @((Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue).LocalPort)
        $ServiceMap = [ordered]@{
            8000  = "FastAPI Gateway (enterprise-rag)"
            8501  = "Streamlit UI (enterprise-rag)"
            5173  = "Abyssium Studio (Vite)"
            5432  = "PostgreSQL 16 + pgvector"
            16686 = "Jaeger Tracing UI"
            4317  = "Jaeger OTLP gRPC"
            11434 = "Ollama Local LLM Service"
        }
        foreach ($entry in $ServiceMap.GetEnumerator()) {
            $port = [int]$entry.Key
            $desc = $entry.Value
            $isListening = $ListeningPorts -contains $port
            $label = if ($isListening) { "RUNNING" } else { "STOPPED" }
            $color = if ($isListening) { "Green" } else { "DarkGray" }
            Write-Host "  * Port $($port.ToString().PadRight(6)) " -NoNewline
            Write-Host ("[$label]".PadRight(12)) -ForegroundColor $color -NoNewline
            Write-Host " $desc" -ForegroundColor White
        }

        # 4. Docker Containers
        Write-Host "`n[Docker Containers]" -ForegroundColor Yellow
        try {
            $containers = docker ps --format "{{.Names}}#{{.Status}}#{{.Ports}}" 2>$null
            if ($containers) {
                foreach ($c in $containers) {
                    $parts = $c -split '#'
                    Write-Host "  * $($parts[0].PadRight(24)) : " -NoNewline
                    Write-Host "$($parts[1])" -ForegroundColor Green
                }
            } else {
                Write-Host "  * No active Docker containers running." -ForegroundColor DarkGray
            }
        } catch {
            Write-Host "  * Docker daemon not responding or unavailable." -ForegroundColor DarkGray
        }
        Write-Host ""
    }

    # -------------------------------------------------------------
    # Enterprise RAG Stack
    # -------------------------------------------------------------
    { $_ -in "rag-api", "api" } {
        Show-Header "Starting FastAPI Gateway (Port 8000)" "Green"
        Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "Health: http://localhost:8000/healthz | http://localhost:8000/readyz`n" -ForegroundColor DarkGray
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            & $PythonCmd -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload @ExtraArgs
        } finally {
            Pop-Location
        }
    }

    { $_ -in "rag-ui", "streamlit", "ui" } {
        Show-Header "Starting Streamlit UI (Port 8501)" "Green"
        Write-Host "URL: http://localhost:8501`n" -ForegroundColor Cyan
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            & $PythonCmd -m streamlit run streamlit_app.py --server.port 8501 @ExtraArgs
        } finally {
            Pop-Location
        }
    }

    { $_ -in "rag-mcp", "mcp" } {
        Show-Header "Starting FastMCP Gateway" "Green"
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            & $PythonCmd -m app.mcp @ExtraArgs
        } finally {
            Pop-Location
        }
    }

    { $_ -in "rag-mcp-ui", "mcp-ui", "mcp-dev", "inspector", "mcp-inspector", "mcp-eval-ui", "mcp-evaluate-ui", "mcp-eval", "mcp-evaluate", "evaluate-ui", "eval-ui", "mcp evaluate ui", "mcp eval ui" } {
        Show-Header "Starting FastMCP Inspector & Evaluate UI (Local Testing)" "Green"
        Write-Host "Interactive UI for testing and evaluating FastMCP tools, schemas, and RBAC policies." -ForegroundColor Cyan
        Write-Host "Server Target: SDLC-Harness-Gateway (app/mcp/gateway.py:mcp)`n" -ForegroundColor DarkGray
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            if (Test-Path $VenvFastMcp) {
                & $VenvFastMcp dev inspector app/mcp/gateway.py:mcp @ExtraArgs
            } elseif (Test-Path $VenvMcp) {
                & $VenvMcp dev app/mcp/gateway.py:mcp @ExtraArgs
            } else {
                npx -y @modelcontextprotocol/inspector $PythonCmd -m app.mcp @ExtraArgs
            }
        } finally {
            Pop-Location
        }
    }

    { $_ -in "rag-test", "test" } {
        Show-Header "Running Pytest Test Suite" "Green"
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            if ($ExtraArgs) {
                & $PythonCmd -m pytest @ExtraArgs
            } else {
                & $PythonCmd -m pytest -v
            }
        } finally {
            Pop-Location
        }
    }

    { $_ -in "rag-ingest", "ingest" } {
        Show-Header "Executing Document Ingestion Pipeline" "Green"
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            # ingest.py requires at least one path; prompt when none were supplied
            if (-not $ExtraArgs -or $ExtraArgs.Count -eq 0) {
                $defaultPath = if (Test-Path "docs") { "docs" } else { "" }
                $promptText = "Enter file/directory path(s) to ingest (space-separated)"
                if ($defaultPath) { $promptText += " [default: $defaultPath]" }
                $pathInput = Read-Host $promptText
                if ([string]::IsNullOrWhiteSpace($pathInput)) { $pathInput = $defaultPath }
                if ([string]::IsNullOrWhiteSpace($pathInput)) {
                    Write-Host "No path provided. Usage: .\poc\run.ps1 ingest <paths...> [--force] [--roles r1 r2] [--batch-size N]" -ForegroundColor Red
                    return
                }
                $ExtraArgs = @($pathInput.Trim() -split '\s+')
                $roleInput = Read-Host "Allowed roles (space-separated) [default: engineer]"
                if (-not [string]::IsNullOrWhiteSpace($roleInput)) {
                    $ExtraArgs += @("--roles") + @($roleInput.Trim() -split '\s+')
                }
                $forceInput = Read-Host "Force re-ingestion? [y/N]"
                if ($forceInput -match '^(y|yes)$') { $ExtraArgs += "--force" }
            }
            & $PythonCmd scripts/ingest.py @ExtraArgs
        } finally {
            Pop-Location
        }
    }

    { $_ -in "docker-up", "db" } {
        Show-Header "Starting PostgreSQL 16 (pgvector) + Jaeger Badger" "Green"
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            docker compose up -d
            Write-Host "`nPostgres: localhost:5432 (enterprise_rag)" -ForegroundColor Cyan
            Write-Host "Jaeger UI: http://localhost:16686" -ForegroundColor Cyan
            Write-Host "Jaeger OTLP gRPC: localhost:4317" -ForegroundColor Cyan
        } finally {
            Pop-Location
        }
    }

    "docker-down" {
        Show-Header "Stopping Docker Compose Services" "Yellow"
        Push-Location "$WorkspaceRoot\enterprise-rag-pgvector-rbac"
        try {
            docker compose down
        } finally {
            Pop-Location
        }
    }

    # -------------------------------------------------------------
    # Abyssium Studio
    # -------------------------------------------------------------
    { $_ -in "studio-dev", "studio", "web" } {
        Show-Header "Starting Abyssium Studio (Port 5173)" "Magenta"
        Write-Host "URL: http://localhost:5173`n" -ForegroundColor Cyan
        Push-Location "$WorkspaceRoot\abyssium-studio"
        try {
            npm run dev
        } finally {
            Pop-Location
        }
    }

    { $_ -in "studio-build", "build" } {
        Show-Header "Building Abyssium Studio Production Bundle" "Magenta"
        Push-Location "$WorkspaceRoot\abyssium-studio"
        try {
            npm run build
        } finally {
            Pop-Location
        }
    }

    { $_ -in "studio-lint", "lint" } {
        Show-Header "Running Abyssium Studio Linter" "Magenta"
        Push-Location "$WorkspaceRoot\abyssium-studio"
        try {
            npm run lint
        } finally {
            Pop-Location
        }
    }

    # -------------------------------------------------------------
    # Ollama Local AI
    # -------------------------------------------------------------
    "ollama" {
        Show-Header "Starting Ollama Session (deepseek-r1:8b)" "Cyan"
        if ($ExtraArgs) {
            ollama run @ExtraArgs
        } else {
            $ollamaScript = Join-Path $ScriptDir "ollama.ps1"
            if (Test-Path $ollamaScript) {
                & $ollamaScript
            } else {
                ollama run deepseek-r1:8b --verbose
            }
        }
    }

    # -------------------------------------------------------------
    # Environment Activation Helper
    # -------------------------------------------------------------
    "activate" {
        $pocActivate = Join-Path $ScriptDir "activate.ps1"
        if (Test-Path $VenvActivate) {
            Write-Host "To activate the virtual environment in your current shell, execute:" -ForegroundColor Green
            Write-Host "  & `"$VenvActivate`"" -ForegroundColor Cyan
            Write-Host "Or invoke: . `"$pocActivate`"" -ForegroundColor Yellow
        } else {
            Write-Host "Virtual environment not found at $VenvActivate" -ForegroundColor Red
        }
    }

    # -------------------------------------------------------------
    # Cleanup Routine
    # -------------------------------------------------------------
    "clean" {
        Show-Header "Cleaning Workspace Artifacts" "Yellow"

        # 1. node_modules removal via poc script or fallback
        $removeNodeScript = Join-Path $ScriptDir "script\ps\_remove-node-modules.ps1"
        if (-not (Test-Path $removeNodeScript)) {
            $removeNodeScript = Join-Path $WorkspaceRoot "poc\script\ps\_remove-node-modules.ps1"
        }
        if (Test-Path $removeNodeScript) {
            Write-Host "Purging node_modules using $removeNodeScript..." -ForegroundColor Yellow
            & $removeNodeScript -Path $WorkspaceRoot -Confirm:$false
        } else {
            Write-Host "Pruning node_modules directories..." -ForegroundColor Yellow
            Get-ChildItem -Path $WorkspaceRoot -Recurse -Directory -Filter "node_modules" -ErrorAction SilentlyContinue |
                ForEach-Object {
                    Write-Host "Removing $($_.FullName)..." -ForegroundColor DarkGray
                    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                }
        }

        # 2. Python __pycache__ (strictly preserving .venv)
        Write-Host "Purging __pycache__ (excluding .venv)..." -ForegroundColor Yellow
        Get-ChildItem -Path $WorkspaceRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
            ForEach-Object {
                Write-Host "Removing $($_.FullName)..." -ForegroundColor DarkGray
                Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }

        # 3. Pytest cache (strictly preserving .venv)
        Write-Host "Purging .pytest_cache (excluding .venv)..." -ForegroundColor Yellow
        Get-ChildItem -Path $WorkspaceRoot -Recurse -Directory -Filter ".pytest_cache" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
            ForEach-Object {
                Write-Host "Removing $($_.FullName)..." -ForegroundColor DarkGray
                Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }

        # 4. Vite dist output
        $studioDist = Join-Path $WorkspaceRoot "abyssium-studio\dist"
        if (Test-Path $studioDist) {
            Write-Host "Removing $studioDist..." -ForegroundColor Yellow
            Remove-Item -Path $studioDist -Recurse -Force -ErrorAction SilentlyContinue
        }

        Write-Host "`nWorkspace cleanup complete!" -ForegroundColor Green
    }

    # -------------------------------------------------------------
    # Environment Setup
    # -------------------------------------------------------------
    "setup" {
        Show-Header "Setting up Workspace Environment" "Green"

        # 1. Python Venv Verification
        if (-not (Test-Path $VenvPython)) {
            Write-Host "Creating Python virtual environment in .venv..." -ForegroundColor Yellow
            python -m venv (Join-Path $WorkspaceRoot ".venv")
        }
        Write-Host "[OK] Python venv ready: $VenvPython" -ForegroundColor Green

        # 2. Enterprise RAG Dependencies
        $reqFile = Join-Path $WorkspaceRoot "enterprise-rag-pgvector-rbac\requirements.txt"
        if (Test-Path $reqFile) {
            Write-Host "Installing/updating Python dependencies from requirements.txt..." -ForegroundColor Cyan
            & $PythonCmd -m pip install --upgrade pip
            & $PythonCmd -m pip install -r $reqFile
            Write-Host "[OK] Python requirements installed." -ForegroundColor Green
        }

        # 3. Abyssium Studio Dependencies
        $studioPkg = Join-Path $WorkspaceRoot "abyssium-studio\package.json"
        $studioModules = Join-Path $WorkspaceRoot "abyssium-studio\node_modules"
        if ((Test-Path $studioPkg) -and (-not (Test-Path $studioModules))) {
            Write-Host "Installing Abyssium Studio npm packages..." -ForegroundColor Cyan
            npm --prefix (Join-Path $WorkspaceRoot "abyssium-studio") install
            Write-Host "[OK] Abyssium Studio packages installed." -ForegroundColor Green
        }

        # 4. Environment (.env) checks
        $ragEnv = Join-Path $WorkspaceRoot "enterprise-rag-pgvector-rbac\.env"
        if (Test-Path $ragEnv) {
            Write-Host "[OK] Enterprise RAG .env is configured." -ForegroundColor Green
        } else {
            Write-Host "[WARN] Enterprise RAG .env is missing: $ragEnv" -ForegroundColor Yellow
        }

        Write-Host "`nWorkspace environment setup finished!" -ForegroundColor Green
    }

    # -------------------------------------------------------------
    # Help / Fallback
    # -------------------------------------------------------------
    { $_ -in "help", "-h", "--help", "?" } {
        Show-Help
    }

    Default {
        Write-Host "Unknown action: '$TargetAction'" -ForegroundColor Red
        Show-Help
    }
}
}

# -----------------------------------------------------------------
# Entrypoint Execution
# -----------------------------------------------------------------
if ([string]::IsNullOrWhiteSpace($Action) -or ($Action -in "menu", "interactive")) {
    Start-MenuLoop
} else {
    Invoke-WorkspaceAction -TargetAction $Action -Arguments $ExtraArgs
}
