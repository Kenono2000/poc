[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
<#
.SYNOPSIS
    Removes all Git-related files and directories from a specified path.
.DESCRIPTION
    This script recursively searches for and removes the .git directory, as well as common
    Git-related files (.gitignore, .gitattributes, .gitmodules, .gitkeep) from the target path.
    Because this is a destructive operation, it supports -WhatIf and -Confirm.
.PARAMETER Path
    The target path to clean of Git files and directories. This parameter is mandatory.
.EXAMPLE
    PS C:\> .\_remove-git-files.ps1 -Path "C:\my-project"
    This command will remove all Git artifacts from "C:\my-project" and its subdirectories,
    prompting for confirmation before each deletion.
.EXAMPLE
    PS C:\> .\_remove-git-files.ps1 -Path "C:\my-project" -WhatIf
    This command will show what items would be removed without actually deleting them.
.EXAMPLE
    PS C:\> .\_remove-git-files.ps1 -Path "C:\my-project" -Confirm:$false -Verbose
    This command will remove all Git artifacts without prompting for confirmation and show verbose output.
#>
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true, Position = 0)]
    [string]$Path
)

process {
    # Verify the target path exists
    if (-not (Test-Path -Path $Path)) {
        Write-Error "The specified path does not exist: $Path"
        return
    }

    Write-Verbose "Starting Git cleanup on path: $Path"

    # Find and remove all .git directories
    Get-ChildItem -Path $Path -Directory -Filter ".git" -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
        if ($PSCmdlet.ShouldProcess($_.FullName, "Remove .git directory")) {
            Write-Verbose "Removing directory $($_.FullName)..."
            Remove-Item -Path $_.FullName -Recurse -Force
        }
    }

    # Find and remove individual Git-related files
    $gitFiles = @(".gitignore", ".gitattributes", ".gitmodules", ".gitkeep")
    Get-ChildItem -Path $Path -Include $gitFiles -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
        if ($PSCmdlet.ShouldProcess($_.FullName, "Remove Git file")) {
            Write-Verbose "Removing file $($_.FullName)..."
            Remove-Item -Path $_.FullName -Force
        }
    }

    Write-Host "`nGit cleanup complete for path: $Path" -ForegroundColor Cyan
}