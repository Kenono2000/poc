<#
.SYNOPSIS
    Export Firestore data from a Google Cloud project, download it locally, and
    boot the Firebase emulators from that export.

.DESCRIPTION
    End-to-end helper for refreshing local emulator data:

      1. Validates parameters and the Firebase project directory.
      2. Verifies node, npm, gcloud, gsutil, and the firebase CLI are available.
      3. Installs firebase-tools globally only when the firebase CLI is missing.
      4. Checks Google Cloud authentication (runs gcloud auth login when needed).
      5. Clears the previous remote and local export folders.
      6. Runs `gcloud firestore export` and downloads the result with `gsutil cp`.
      7. Starts `firebase emulators:start --import <dir> --export-on-exit`.

    All paths default relative to this script, so no machine-specific absolute
    paths are required.

.PARAMETER ProjectId
    Google Cloud / Firebase project ID. Defaults to $env:FIREBASE_PROJECT_ID,
    then $env:GCLOUD_PROJECT.

.PARAMETER Bucket
    Cloud Storage bucket that receives the export. Accepts a bare bucket name
    or a gs:// URI. Defaults to "<ProjectId>.firebasestorage.app".

.PARAMETER LocalDir
    Local folder that receives the downloaded export. Defaults to
    "firestore-export" next to this script. It is cleared before downloading.

.PARAMETER FunctionsDir
    Folder that contains firebase.json (the Firebase project root used for
    `firebase emulators:start`). Defaults to this script's folder.

.PARAMETER SkipAuth
    Skip the `gcloud auth login` check. Useful in CI or when already
    authenticated in another session.

.PARAMETER WhatIf
    Show the commands that would run without changing anything.

.EXAMPLE
    .\_start.ps1 -ProjectId my-firebase-project

.EXAMPLE
    .\_start.ps1 -ProjectId my-firebase-project -FunctionsDir ..\..\firebase-project -SkipAuth

.EXAMPLE
    .\_start.ps1 -ProjectId my-firebase-project -WhatIf

.NOTES
    Requires PowerShell 5.1+, Node.js 18+, Google Cloud SDK (gcloud + gsutil),
    and (or allows install of) firebase-tools.
#>
[CmdletBinding()]
param(
    [string]$ProjectId = '',
    [string]$Bucket = '',
    [string]$LocalDir = '',
    [string]$FunctionsDir = '',
    [switch]$SkipAuth,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
$script:StepNumber = 0

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    $script:StepNumber += 1
    Write-Host ''
    Write-Host ("[{0}] {1}" -f $script:StepNumber, $Message) -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    OK: $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    WARN: $Message" -ForegroundColor Yellow
}

function Get-ToolPath {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }
    if ($command.Source) {
        return $command.Source
    }
    return $command.Name
}

function Invoke-Native {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory)][string]$Description
    )

    $display = "$FilePath $($Arguments -join ' ')"

    if ($WhatIf) {
        Write-Host "    [WhatIf] $Description" -ForegroundColor Yellow
        Write-Host "    [WhatIf] $display" -ForegroundColor DarkGray
        return
    }

    Write-Host "    > $display" -ForegroundColor DarkGray
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $display"
    }
}

function Test-PathInside {
    param(
        [Parameter(Mandatory)][string]$Candidate,
        [Parameter(Mandatory)][string]$Parent
    )

    $separator = [System.IO.Path]::DirectorySeparatorChar
    $parentWithSeparator = $Parent.TrimEnd('\', '/') + $separator
    return ($Candidate + $separator).StartsWith(
        $parentWithSeparator,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------
try {
    # --- Step 1: resolve and validate configuration ------------------------
    Write-Step 'Resolving configuration'

    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        $ProjectId = if ($env:FIREBASE_PROJECT_ID) {
            $env:FIREBASE_PROJECT_ID
        } elseif ($env:GCLOUD_PROJECT) {
            $env:GCLOUD_PROJECT
        } else {
            ''
        }
    }
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        throw 'ProjectId is required. Pass -ProjectId <project-id> or set FIREBASE_PROJECT_ID / GCLOUD_PROJECT.'
    }
    $ProjectId = $ProjectId.Trim()

    if ([string]::IsNullOrWhiteSpace($Bucket)) {
        $Bucket = "$ProjectId.firebasestorage.app"
        Write-Info "Bucket not specified; using default bucket '$Bucket'."
    }
    else {
        $Bucket = ($Bucket.Trim() -replace '^gs://', '' -replace '/+$', '')
        if ([string]::IsNullOrWhiteSpace($Bucket)) {
            throw 'Bucket resolves to an empty name. Pass -Bucket <bucket-name>.'
        }
    }

    if ([string]::IsNullOrWhiteSpace($LocalDir)) {
        $LocalDir = Join-Path $PSScriptRoot 'firestore-export'
    }
    elseif (-not [System.IO.Path]::IsPathRooted($LocalDir)) {
        $LocalDir = Join-Path $PSScriptRoot $LocalDir
    }
    $LocalDir = [System.IO.Path]::GetFullPath($LocalDir)

    if ([string]::IsNullOrWhiteSpace($FunctionsDir)) {
        $FunctionsDir = $PSScriptRoot
    }
    elseif (-not [System.IO.Path]::IsPathRooted($FunctionsDir)) {
        $FunctionsDir = Join-Path $PSScriptRoot $FunctionsDir
    }
    $FunctionsDir = [System.IO.Path]::GetFullPath($FunctionsDir)

    # Safety checks before any folder is cleared.
    $filesystemRoot = [System.IO.Path]::GetPathRoot($LocalDir)
    if ($LocalDir.TrimEnd('\', '/') -eq $filesystemRoot.TrimEnd('\', '/')) {
        throw "Refusing to use a filesystem root as -LocalDir: '$LocalDir'."
    }
    if (Test-PathInside -Candidate $PSScriptRoot -Parent $LocalDir) {
        throw "Refusing to clear -LocalDir '$LocalDir' because it contains this script. Choose a dedicated export folder."
    }

    $exportPrefix = "$ProjectId-export-from-gcloud"
    $exportUri = "gs://$Bucket/$exportPrefix"

    Write-Ok "ProjectId:    $ProjectId"
    Write-Ok "Bucket:       $Bucket"
    Write-Ok "Export URI:   $exportUri"
    Write-Ok "LocalDir:     $LocalDir"
    Write-Ok "FunctionsDir: $FunctionsDir"
    Write-Ok "SkipAuth:     $($SkipAuth.IsPresent)"
    if ($WhatIf) {
        Write-Host '    Dry run: no commands will be executed and no files will change.' -ForegroundColor Yellow
    }

    # --- Step 2: validate the Firebase project folder ----------------------
    Write-Step 'Validating Firebase project directory'

    if (-not (Test-Path -LiteralPath $FunctionsDir -PathType Container)) {
        throw "FunctionsDir '$FunctionsDir' does not exist. Pass -FunctionsDir pointing at the folder that contains firebase.json."
    }

    $firebaseJsonPath = Join-Path $FunctionsDir 'firebase.json'
    if (-not (Test-Path -LiteralPath $firebaseJsonPath -PathType Leaf)) {
        $firebaseJsonMessage = "No firebase.json found in '$FunctionsDir'. Pass -FunctionsDir pointing at the Firebase project folder that contains firebase.json."
        if ($WhatIf) {
            Write-Warn $firebaseJsonMessage
        }
        else {
            throw $firebaseJsonMessage
        }
    }
    else {
        Write-Ok "Found $firebaseJsonPath"
    }

    # --- Step 3: verify required tools ------------------------------------
    Write-Step 'Checking required tools'

    $nodePath = Get-ToolPath 'node'
    if ($null -eq $nodePath) {
        throw 'Node.js is not installed or not on PATH. Install Node.js 18+ and retry.'
    }
    Write-Ok "node: $nodePath"

    $npmPath = Get-ToolPath 'npm'
    if ($null -eq $npmPath) {
        throw 'npm is not installed or not on PATH. npm is required to install firebase-tools.'
    }
    Write-Ok "npm: $npmPath"

    $gcloudPath = Get-ToolPath 'gcloud'
    if ($null -eq $gcloudPath) {
        throw 'gcloud is not installed or not on PATH. Install the Google Cloud SDK and retry.'
    }
    Write-Ok "gcloud: $gcloudPath"

    $gsutilPath = Get-ToolPath 'gsutil'
    if ($null -eq $gsutilPath) {
        throw 'gsutil is not installed or not on PATH. Install the Google Cloud SDK (gsutil component) and retry.'
    }
    Write-Ok "gsutil: $gsutilPath"

    $firebasePath = Get-ToolPath 'firebase'
    if ($null -eq $firebasePath) {
        Write-Warn 'firebase CLI not found; installing firebase-tools globally.'
        Invoke-Native -FilePath $npmPath -Arguments @('install', '-g', 'firebase-tools') -Description 'Install firebase-tools globally'
        $firebasePath = Get-ToolPath 'firebase'
        if ($null -eq $firebasePath) {
            if ($WhatIf) {
                Write-Warn 'firebase-tools would be installed here; continuing dry run.'
            }
            else {
                throw 'firebase is still not on PATH after installing firebase-tools. Restart the shell so PATH updates, then retry.'
            }
        }
    }
    if ($null -ne $firebasePath) {
        Write-Ok "firebase: $firebasePath"
    }

    # --- Step 4: authenticate with Google Cloud ---------------------------
    Write-Step 'Checking Google Cloud authentication'

    if ($SkipAuth) {
        Write-Info 'Skipping gcloud auth login because -SkipAuth was supplied.'
    }
    elseif ($WhatIf) {
        Write-Info '[WhatIf] Would run "gcloud auth login" when no active account is found.'
    }
    else {
        $activeAccount = & $gcloudPath auth list --filter=status:ACTIVE --format='value(account)' 2>$null
        if ([string]::IsNullOrWhiteSpace($activeAccount)) {
            Write-Info 'No active gcloud account found; starting gcloud auth login.'
            Invoke-Native -FilePath $gcloudPath -Arguments @('auth', 'login') -Description 'Authenticate with Google Cloud'
        }
        else {
            Write-Ok "Authenticated as $($activeAccount.Trim())"
        }
    }

    Invoke-Native -FilePath $gcloudPath -Arguments @('config', 'set', 'project', $ProjectId) -Description "Set gcloud project to $ProjectId"

    # --- Step 5: clear previous export data -------------------------------
    Write-Step 'Clearing previous export data'

    Write-Info "Remote prefix: $exportUri"
    try {
        Invoke-Native -FilePath $gsutilPath -Arguments @('-m', '-q', 'rm', '-r', $exportUri) -Description 'Remove previous remote Firestore export'
    }
    catch {
        Write-Warn "Could not remove the previous remote export: $($_.Exception.Message)"
    }

    if (Test-Path -LiteralPath $LocalDir) {
        if ($WhatIf) {
            Write-Host "    [WhatIf] Remove existing directory $LocalDir" -ForegroundColor Yellow
        }
        else {
            Remove-Item -LiteralPath $LocalDir -Recurse -Force
            Write-Ok "Removed previous local export directory: $LocalDir"
        }
    }
    else {
        Write-Info "No previous local export directory at $LocalDir."
    }

    if (-not $WhatIf) {
        New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null
        Write-Ok "Created empty local export directory: $LocalDir"
    }

    # --- Step 6: export Firestore data to Cloud Storage -------------------
    Write-Step "Exporting Firestore data to $exportUri"
    Invoke-Native -FilePath $gcloudPath -Arguments @('firestore', 'export', $exportUri) -Description 'Export Firestore data to Cloud Storage'

    # --- Step 7: download the export --------------------------------------
    Write-Step "Downloading export to $LocalDir"
    Invoke-Native -FilePath $gsutilPath -Arguments @('-m', 'cp', '-r', "$exportUri/*", $LocalDir) -Description 'Copy export files from Cloud Storage'

    # --- Step 8: locate the export metadata -------------------------------
    Write-Step 'Locating export metadata'

    if ($WhatIf) {
        $importDir = $LocalDir
        Write-Info "[WhatIf] Would search '$LocalDir' recursively for *overall_export_metadata."
    }
    else {
        $metadata = Get-ChildItem -LiteralPath $LocalDir -Recurse -File -Filter '*overall_export_metadata' -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $metadata) {
            throw "Could not find an *overall_export_metadata file under '$LocalDir'. Confirm that the gsutil copy succeeded and that the export contains Firestore data."
        }
        $importDir = $metadata.Directory.FullName
        Write-Ok "Found export metadata: $($metadata.FullName)"
    }
    Write-Ok "Emulator import path: $importDir"

    # --- Step 9: start the emulator from the export -----------------------
    Write-Step 'Starting Firestore emulator'

    $emulatorArguments = @(
        'emulators:start',
        '--project', $ProjectId,
        '--import', $importDir,
        '--export-on-exit'
    )

    if ($WhatIf) {
        Write-Host "    [WhatIf] Push-Location '$FunctionsDir'" -ForegroundColor Yellow
        Write-Host "    [WhatIf] firebase $($emulatorArguments -join ' ')" -ForegroundColor Yellow
    }
    else {
        Push-Location -LiteralPath $FunctionsDir
        try {
            Write-Host "    > firebase $($emulatorArguments -join ' ')" -ForegroundColor DarkGray
            & $firebasePath @emulatorArguments
            $emulatorExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        if ($emulatorExitCode -ne 0) {
            throw "firebase emulators:start exited with code $emulatorExitCode."
        }
    }

    Write-Host ''
    if ($WhatIf) {
        Write-Host 'Dry run complete: no changes were made.' -ForegroundColor Green
    }
    else {
        Write-Host 'Firestore emulator stopped; export/import workflow complete.' -ForegroundColor Green
    }
    exit 0
}
catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'See the step output above to find where the workflow stopped.' -ForegroundColor DarkGray
    exit 1
}
