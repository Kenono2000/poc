[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
<#
.SYNOPSIS
    Removes all node_modules directories from a specified path.
.DESCRIPTION
    This script recursively searches for and removes all node_modules directories from the target path.
    Because this is a destructive operation, it supports -WhatIf and -Confirm.
.PARAMETER Path
    The target path to clean of node_modules directories. This parameter is mandatory.
.EXAMPLE
    PS C:\> .\_remove-node-modules.ps1 -Path "C:\my-project"
    This command will remove all node_modules directories from "C:\my-project" and its subdirectories,
    prompting for confirmation before each deletion.
.EXAMPLE
    PS C:\> .\_remove-node-modules.ps1 -Path "C:\my-project" -WhatIf
    This command will show what items would be removed without actually deleting them.
.EXAMPLE
    PS C:\> .\_remove-node-modules.ps1 -Path "C:\my-project" -Confirm:$false -Verbose
    This command will remove all node_modules directories without prompting for confirmation and show verbose output.
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

    Write-Verbose "Starting node_modules cleanup on path: $Path"

    # Find and remove all node_modules directories
    Get-ChildItem -Path $Path -Directory -Filter "node_modules" -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
        if ($PSCmdlet.ShouldProcess($_.FullName, "Remove node_modules directory")) {
            Write-Verbose "Removing directory $($_.FullName)..."
            Remove-Item -Path $_.FullName -Recurse -Force
        }
    }

    Write-Host "`nnode_modules cleanup complete for path: $Path" -ForegroundColor Cyan
}
