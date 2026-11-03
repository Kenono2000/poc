<#
.SYNOPSIS
    Recursively removes all Git metadata (.git folders and .git* files) below a path.

.DESCRIPTION
    Use this to detach a directory tree from Git when archiving, copying, or
    flattening projects. The script scans for:

      * every ".git" directory (repository metadata, worktrees, submodules)
      * every file whose name starts with ".git" (.gitignore, .gitattributes,
        .gitmodules, .gitkeep, .gitconfig, ...)

    Both sets are collected before deletion, deepest paths first, so removing a
    repository does not invalidate the enumeration of its own subdirectories.
    Because this is destructive it supports -WhatIf and -Confirm.

.PARAMETER Path
    Root directory to clean. Mandatory.

.PARAMETER KeepFiles
    Remove only the ".git" directories and leave .gitignore/.gitattributes-style
    files in place.

.EXAMPLE
    PS> .\_remove-git-files.ps1 -Path "C:\archive\project" -WhatIf

    Lists every Git artifact that would be removed.

.EXAMPLE
    PS> .\_remove-git-files.ps1 -Path "C:\archive\project" -Confirm:$false -Verbose

    Deletes all Git metadata without prompting.

.EXAMPLE
    PS> .\_remove-git-files.ps1 -Path "C:\archive\project" -KeepFiles

    Deletes only .git repositories, preserving .gitignore and friends.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [Parameter(Mandatory = $false)]
    [switch]$KeepFiles
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

    Write-Verbose "Starting Git cleanup on path: $resolved"

    # --- Collect repositories first (descending depth) -----------------------
    $gitDirs = @(
        Get-ChildItem -LiteralPath $resolved -Directory -Filter '.git' -Recurse -Force -ErrorAction SilentlyContinue |
            Sort-Object -Property { $_.FullName.Length } -Descending
    )

    $removedDirs = 0
    foreach ($dir in $gitDirs) {
        if ($PSCmdlet.ShouldProcess($dir.FullName, 'Remove .git directory')) {
            try {
                Write-Verbose "Removing directory $($dir.FullName)..."
                Remove-Item -LiteralPath $dir.FullName -Recurse -Force -ErrorAction Stop
                $removedDirs++
            }
            catch {
                Write-Warning "Failed to remove '$($dir.FullName)': $($_.Exception.Message)"
            }
        }
    }

    # --- Then remove .git* files (unless -KeepFiles was requested) -----------
    $removedFiles = 0
    if (-not $KeepFiles) {
        $gitFiles = @(
            Get-ChildItem -LiteralPath $resolved -File -Filter '.git*' -Recurse -Force -ErrorAction SilentlyContinue
        )

        foreach ($file in $gitFiles) {
            if ($PSCmdlet.ShouldProcess($file.FullName, 'Remove Git file')) {
                try {
                    Write-Verbose "Removing file $($file.FullName)..."
                    Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
                    $removedFiles++
                }
                catch {
                    Write-Warning "Failed to remove '$($file.FullName)': $($_.Exception.Message)"
                }
            }
        }
    }

    Write-Host "`nGit cleanup complete for path: $resolved" -ForegroundColor Cyan
    Write-Host ("  Repositories removed : {0}" -f $removedDirs) -ForegroundColor DarkGray
    Write-Host ("  Git files removed    : {0}" -f $(if ($KeepFiles) { 'skipped (-KeepFiles)' } else { $removedFiles })) -ForegroundColor DarkGray
}
