<#
.SYNOPSIS
    Recursively removes every node_modules directory below a target path.

.DESCRIPTION
    node_modules trees are large, deeply nested and full of symlinks, so this
    script collects all matches first and deletes them from the deepest path
    outwards. That order prevents "directory is not empty" failures caused by
    deleting a parent before its nested node_modules children.

    Because this is a high-impact, destructive operation it supports -WhatIf
    and -Confirm, prints reclaimed space, and never follows reparse points
    (junctions/symlinks) while enumerating.

.PARAMETER Path
    Root directory to clean. Mandatory.

.PARAMETER KeepLockfile
    Accepted for symmetry with other tooling; lockfiles are never touched by
    this script, so the switch is a no-op and only kept for readability.

.EXAMPLE
    PS> .\_remove-node-modules.ps1 -Path "C:\work\monorepo" -WhatIf

    Lists every node_modules directory that would be deleted.

.EXAMPLE
    PS> .\_remove-node-modules.ps1 -Path "C:\work\monorepo" -Confirm:$false -Verbose

    Deletes all node_modules directories without prompting.

.NOTES
    Requires the caller to have write access to the target folders. Locked files
    (e.g. a running dev server) are reported as warnings and skipped.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [Parameter(Mandatory = $false)]
    [switch]$KeepLockfile
)

process {
    # Verify the target path exists.
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Error "The specified path does not exist: $Path"
        return
    }

    $resolved = (Resolve-Path -LiteralPath $Path).ProviderPath
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        Write-Error "The specified path is not a directory: $resolved"
        return
    }

    Write-Verbose "Starting node_modules cleanup on path: $resolved"

    # Collect once; deleting while enumerating a tree is unreliable.
    $targets = @(
        Get-ChildItem -LiteralPath $resolved -Directory -Filter 'node_modules' -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { -not ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) } |
            Sort-Object -Property { $_.FullName.Length } -Descending
    )

    if ($targets.Count -eq 0) {
        Write-Host "No node_modules directories found under: $resolved" -ForegroundColor Yellow
        return
    }

    Write-Verbose "Found $($targets.Count) node_modules director$(if ($targets.Count -eq 1) { 'y' } else { 'ies' })"

    $removed = 0
    $reclaimedBytes = 0

    foreach ($target in $targets) {
        if (-not $PSCmdlet.ShouldProcess($target.FullName, 'Remove node_modules directory')) {
            continue
        }

        try {
            # Measure before deleting so the summary can report reclaimed space.
            $size = 0
            Get-ChildItem -LiteralPath $target.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
                ForEach-Object { $size += $_.Length }

            Remove-Item -LiteralPath $target.FullName -Recurse -Force -ErrorAction Stop
            $removed++
            $reclaimedBytes += $size
            Write-Verbose "Removed $($target.FullName)"
        }
        catch {
            Write-Warning "Failed to remove '$($target.FullName)': $($_.Exception.Message)"
        }
    }

    $reclaimedMB = [math]::Round($reclaimedBytes / 1MB, 2)

    Write-Host "`nnode_modules cleanup complete for path: $resolved" -ForegroundColor Cyan
    Write-Host ("  Directories removed : {0}" -f $removed) -ForegroundColor DarkGray
    Write-Host ("  Space reclaimed     : {0} MB" -f $reclaimedMB) -ForegroundColor DarkGray
}
