<#
.SYNOPSIS
    Renames every file sharing an extension into a zero-padded sequential series.

.DESCRIPTION
    Given a target directory, files are grouped by extension and renamed to
    001.ext, 002.ext, 003.ext, ... (width grows automatically for 1000+ files).
    Each extension group is numbered independently, so a folder containing
    25 JPGs and 3 PDFs becomes 001.jpg..025.jpg and 001.pdf..003.pdf.

    The rename is performed in two passes through unique temporary names
    ("__tmp_<guid>_<n>.ext"), which makes the operation safe even when the
    destination numbers already exist or when source and destination overlap.
    The script supports -WhatIf / -Confirm because it renames files in place.

.PARAMETER Path
    Directory containing the files to rename. Mandatory.

.PARAMETER Recurse
    Process subdirectories as well. Each directory is numbered independently.

.PARAMETER Extension
    Optional extension filter(s), with or without the leading dot (e.g. jpg, .pdf).
    When omitted, every file in the directory is processed.

.PARAMETER DigitWidth
    Minimum number of digits in the sequence number. Defaults to 3 (001).

.EXAMPLE
    PS> .\_rename_by_extension_sequential.ps1 -Path "C:\Photos"

    Renames files in C:\Photos to 001.<ext>, 002.<ext>, ...

.EXAMPLE
    PS> .\_rename_by_extension_sequential.ps1 -Path "C:\Photos" -Extension jpg,png -WhatIf

    Shows which files would be renamed, restricted to .jpg and .png.

.EXAMPLE
    PS> .\_rename_by_extension_sequential.ps1 -Path "C:\Photos" -Recurse -Confirm:$false

    Renames files in C:\Photos and every subdirectory without prompting.

.NOTES
    - Hidden/system files are skipped.
    - Files already matching the target pattern (e.g. 001.jpg) are renumbered too,
      so the result is a clean, gap-free sequence.
    - A preview of the temporary-name pass is written to the Verbose stream.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [Parameter(Mandatory = $false)]
    [switch]$Recurse,

    [Parameter(Mandatory = $false)]
    [string[]]$Extension,

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 10)]
    [int]$DigitWidth = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Normalise the requested extensions to lower-case ".ext" form.
$ExtensionFilter = $null
if ($Extension) {
    $ExtensionFilter = @(
        $Extension |
            ForEach-Object { $_.Trim().ToLowerInvariant() } |
            Where-Object { $_ -ne '' } |
            ForEach-Object { if ($_.StartsWith('.')) { $_ } else { ".$_" } } |
            Select-Object -Unique
    )
}

function Get-TargetFiles {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $false)][string[]]$Filter
    )

    $items = @(Get-ChildItem -LiteralPath $Directory -File -Force -ErrorAction Stop |
        Where-Object { -not ($_.Attributes -band [System.IO.FileAttributes]::System) })

    if ($Filter) {
        $items = @($items | Where-Object { $Filter -contains $_.Extension.ToLowerInvariant() })
    }

    return $items
}

function Rename-ExtensionGroup {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]]$Files,
        [Parameter(Mandatory = $true)][string]$Directory
    )

    # Group by extension so numbering restarts at 001 for each type.
    $groups = $Files | Group-Object -Property { $_.Extension.ToLowerInvariant() }
    if (-not $groups) { return 0 }

    $renamed = 0

    foreach ($group in $groups) {
        $files = @($group.Group | Sort-Object -Property Name)
        $count = $files.Count
        if ($count -eq 0) { continue }

        # Grow the width for large folders so sorting stays correct (e.g. 0001).
        $width = [Math]::Max($DigitWidth, ([string]$count).Length)
        $runId = [guid]::NewGuid().ToString('N')

        $tempMap = [System.Collections.Generic.List[object]]::new()
        $index = 0

        foreach ($file in $files) {
            $index++
            $finalName = $index.ToString(('D' + $width)) + $file.Extension.ToLowerInvariant()
            $tempName = "__tmp_${runId}_$index$($file.Extension.ToLowerInvariant())"
            $tempPath = Join-Path -Path $Directory -ChildPath $tempName

            # Pass 1: move the original out of the way to a guaranteed-unique name.
            if ($PSCmdlet.ShouldProcess($file.FullName, "Rename to temporary name '$tempName'")) {
                try {
                    Rename-Item -LiteralPath $file.FullName -NewName $tempName -ErrorAction Stop
                    $tempMap.Add([pscustomobject]@{
                        TempPath  = $tempPath
                        FinalName = $finalName
                    })
                }
                catch {
                    Write-Warning "Failed to stage '$($file.FullName)': $($_.Exception.Message)"
                }
            }
        }

        # Pass 2: promote temporary names to the final sequential names.
        foreach ($entry in $tempMap) {
            if (-not (Test-Path -LiteralPath $entry.TempPath)) {
                Write-Warning "Temporary file disappeared before final rename: $($entry.TempPath)"
                continue
            }

            $destination = Join-Path -Path $Directory -ChildPath $entry.FinalName
            if ($PSCmdlet.ShouldProcess($entry.TempPath, "Rename to final name '$($entry.FinalName)'")) {
                try {
                    if (Test-Path -LiteralPath $destination) {
                        # Only reachable if an unexpected collision slipped through.
                        Remove-Item -LiteralPath $destination -Force -ErrorAction Stop
                    }
                    Rename-Item -LiteralPath $entry.TempPath -NewName $entry.FinalName -ErrorAction Stop
                    $renamed++
                }
                catch {
                    Write-Warning "Failed to rename '$($entry.TempPath)' to '$($entry.FinalName)': $($_.Exception.Message)"
                }
            }
        }
    }

    return $renamed
}

# --- Validate the target path -------------------------------------------------
$resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
if (-not $resolved) {
    Write-Error "The specified path does not exist: $Path"
    exit 1
}
$root = $resolved.ProviderPath
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    Write-Error "The specified path is not a directory: $root"
    exit 1
}

# --- Collect the directories to process --------------------------------------
$directories = [System.Collections.Generic.List[string]]::new()
$directories.Add($root)

if ($Recurse) {
    Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        ForEach-Object { $directories.Add($_.FullName) }
}

Write-Host "Processing $($directories.Count) director$(if ($directories.Count -eq 1) { 'y' } else { 'ies' }) under: $root" -ForegroundColor Cyan
if ($ExtensionFilter) {
    Write-Host "Extension filter: $($ExtensionFilter -join ', ')" -ForegroundColor DarkGray
}

$totalRenamed = 0
foreach ($directory in $directories) {
    try {
        $files = @(Get-TargetFiles -Directory $directory -Filter $ExtensionFilter)
    }
    catch {
        Write-Warning "Cannot enumerate '$directory': $($_.Exception.Message)"
        continue
    }

    if (-not $files -or $files.Count -eq 0) {
        Write-Verbose "No matching files in $directory"
        continue
    }

    Write-Verbose "Processing $($files.Count) file(s) in $directory"
    $totalRenamed += Rename-ExtensionGroup -Files $files -Directory $directory
}

Write-Host "`nSequential rename complete. Files renamed: $totalRenamed" -ForegroundColor Green
