$VenvActivate = Join-Path (Split-Path -Parent $PSScriptRoot) ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
} else {
    Write-Error "Virtual environment not found at $VenvActivate"
}
