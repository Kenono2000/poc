#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [Parameter(Mandatory = $false)]
    [string[]]$Drives = @('C:', 'D:', 'E:'),

    [Parameter(Mandatory = $false)]
    [string]$OutputCsvPath = (Join-Path -Path $PSScriptRoot -ChildPath "ObsoleteFilesReport.csv")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

$Now               = Get-Date
$Cutoff90Days      = $Now.AddDays(-90)
$Cutoff60Days      = $Now.AddDays(-60)
$Results           = [System.Collections.Generic.List[PSCustomObject]]::new()
$VisitedFilePaths  = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

# System directories to exclude during general recursive traversal
$ExcludedRootRegex = '(?i)^[A-Z]:\\(Windows|Program Files|Program Files \(x86\)|System Volume Information|\$Recycle\.Bin|Recovery)(\\|$)'

function Add-ReportItem {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$File,
        [Parameter(Mandatory = $true)]
        [string]$Category
    )
    if ($VisitedFilePaths.Add($File.FullName)) {
        $DriveRoot = $File.FullName.Substring(0, 2).ToUpperInvariant()
        $Results.Add([PSCustomObject]@{
            Drive            = $DriveRoot
            Category         = $Category
            FullName         = $File.FullName
            Directory        = $File.DirectoryName
            Extension        = $File.Extension
            SizeBytes        = $File.Length
            SizeMB           = [math]::Round($File.Length / 1MB, 4)
            SizeGB           = [math]::Round($File.Length / 1GB, 6)
            LastWriteTime    = $File.LastWriteTime
            AgeDays          = [int]($Now - $File.LastWriteTime).TotalDays
        })
    }
}

function Get-SafeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath,
        [Parameter(Mandatory = $false)]
        [string]$Filter = '*',
        [Parameter(Mandatory = $false)]
        [switch]$AllowWindowsTemp
    )
    if (-not (Test-Path -LiteralPath $RootPath)) { return }

    $DirStack = [System.Collections.Generic.Stack[string]]::new()
    $DirStack.Push($RootPath)

    while ($DirStack.Count -gt 0) {
        $CurrentDir = $DirStack.Pop()

        if (-not $AllowWindowsTemp -and ($CurrentDir -match $ExcludedRootRegex)) {
            continue
        }

        try {
            foreach ($FilePath in [System.IO.Directory]::EnumerateFiles($CurrentDir, $Filter)) {
                $FileInfo = [System.IO.FileInfo]::new($FilePath)
                if ($null -ne $FileInfo -and -not ($FileInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
                    $FileInfo
                }
            }
        } catch { }

        try {
            foreach ($SubDir in [System.IO.Directory]::EnumerateDirectories($CurrentDir)) {
                if (-not $AllowWindowsTemp -and ($SubDir -match $ExcludedRootRegex)) {
                    continue
                }
                $DirInfo = [System.IO.DirectoryInfo]::new($SubDir)
                if (-not ($DirInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
                    $DirStack.Push($SubDir)
                }
            }
        } catch { }
    }
}

foreach ($Drive in $Drives) {
    $NormalizedDrive = ($Drive.TrimEnd('\').TrimEnd(':') + ':').ToUpperInvariant()
    $DriveRootPath   = "$NormalizedDrive\"

    if (-not (Test-Path -LiteralPath $DriveRootPath)) {
        Write-Warning "Drive $NormalizedDrive is not available or does not exist. Skipping."
        continue
    }

    if (-not $PSCmdlet.ShouldProcess("Drive $NormalizedDrive", "Read-only scan for obsolete files")) {
        continue
    }

    Write-Verbose "Scanning $NormalizedDrive ..."

    # 1. Temporary files (.tmp, ~*) in User Temp folders and C:\Windows\Temp
    $TempTargets = [System.Collections.Generic.List[string]]::new()
    if ($NormalizedDrive -eq 'C:' -and (Test-Path -LiteralPath 'C:\Windows\Temp')) {
        $TempTargets.Add('C:\Windows\Temp')
    }
    $UsersRoot = Join-Path -Path $DriveRootPath -ChildPath 'Users'
    if (Test-Path -LiteralPath $UsersRoot) {
        Get-ChildItem -LiteralPath $UsersRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $UserTemp = Join-Path -Path $_.FullName -ChildPath 'AppData\Local\Temp'
            if (Test-Path -LiteralPath $UserTemp) {
                $TempTargets.Add($UserTemp)
            }
        }
    }

    foreach ($TempDir in $TempTargets) {
        Get-SafeFiles -RootPath $TempDir -AllowWindowsTemp | Where-Object {
            $_.Extension -ieq '.tmp' -or $_.Name -like '~*'
        } | ForEach-Object {
            Add-ReportItem -File $_ -Category 'TempFile (.tmp / ~*)'
        }
    }

    # 2. Browser caches and Downloads folders older than 90 days
    if (Test-Path -LiteralPath $UsersRoot) {
        Get-ChildItem -LiteralPath $UsersRoot -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $UserProfile = $_.FullName

            $DownloadsDir = Join-Path -Path $UserProfile -ChildPath 'Downloads'
            if (Test-Path -LiteralPath $DownloadsDir) {
                Get-SafeFiles -RootPath $DownloadsDir | Where-Object {
                    $_.LastWriteTime -lt $Cutoff90Days
                } | ForEach-Object {
                    Add-ReportItem -File $_ -Category 'Downloads (>90 Days)'
                }
            }

            $BrowserCachePaths = @(
                (Join-Path $UserProfile 'AppData\Local\Google\Chrome\User Data'),
                (Join-Path $UserProfile 'AppData\Local\Microsoft\Edge\User Data'),
                (Join-Path $UserProfile 'AppData\Local\BraveSoftware\Brave-Browser\User Data'),
                (Join-Path $UserProfile 'AppData\Local\Mozilla\Firefox\Profiles')
            )
            foreach ($BrowserRoot in $BrowserCachePaths) {
                if (Test-Path -LiteralPath $BrowserRoot) {
                    Get-SafeFiles -RootPath $BrowserRoot | Where-Object {
                        $_.DirectoryName -match '(?i)\\(Cache|Code Cache|GPUCache|ShaderCache|Service Worker\\CacheStorage|cache2)(\\|$)' -and
                        $_.LastWriteTime -lt $Cutoff90Days
                    } | ForEach-Object {
                        Add-ReportItem -File $_ -Category 'BrowserCache (>90 Days)'
                    }
                }
            }
        }
    }

    # 3. Log files (.log) older than 60 days (excluding system folders)
    Get-SafeFiles -RootPath $DriveRootPath -Filter '*.log' | Where-Object {
        $_.Extension -ieq '.log' -and $_.LastWriteTime -lt $Cutoff60Days
    } | ForEach-Object {
        Add-ReportItem -File $_ -Category 'LogFile (>60 Days)'
    }

    # 4. Orphaned installer packages (.msi, .msp) in cache directories
    foreach ($InstallerFilter in @('*.msi', '*.msp')) {
        Get-SafeFiles -RootPath $DriveRootPath -Filter $InstallerFilter | Where-Object {
            ($_.Extension -ieq '.msi' -or $_.Extension -ieq '.msp') -and
            ($_.DirectoryName -match '(?i)\\(Package Cache|Installer|Downloaded Installations|Cache|Temp)(\\|$)')
        } | ForEach-Object {
            Add-ReportItem -File $_ -Category 'CachedInstaller (.msi/.msp)'
        }
    }
}

$SummaryTable = foreach ($Drive in $Drives) {
    $NormalizedDrive = ($Drive.TrimEnd('\').TrimEnd(':') + ':').ToUpperInvariant()
    $DriveItems      = @($Results | Where-Object { $_.Drive -eq $NormalizedDrive })
    $TotalBytes      = if ($DriveItems.Count -gt 0) { ($DriveItems | Measure-Object -Property SizeBytes -Sum).Sum } else { 0 }

    [PSCustomObject]@{
        Drive              = $NormalizedDrive
        FileCount          = $DriveItems.Count
        ReclaimableMB      = [math]::Round($TotalBytes / 1MB, 2)
        ReclaimableGB      = [math]::Round($TotalBytes / 1GB, 3)
    }
}

$GrandTotalBytes = ($Results | Measure-Object -Property SizeBytes -Sum).Sum
if ($null -eq $GrandTotalBytes) { $GrandTotalBytes = 0 }

$SummaryWithTotal = @($SummaryTable) + @([PSCustomObject]@{
    Drive              = 'TOTAL'
    FileCount          = $Results.Count
    ReclaimableMB      = [math]::Round($GrandTotalBytes / 1MB, 2)
    ReclaimableGB      = [math]::Round($GrandTotalBytes / 1GB, 3)
})

Write-Host "`n=== Potential Space Savings Summary ===" -ForegroundColor Cyan
$SummaryWithTotal | Format-Table -AutoSize

if ($Results.Count -gt 0) {
    $CategorySummary = $Results | Group-Object Category | ForEach-Object {
        $CatBytes = ($_.Group | Measure-Object -Property SizeBytes -Sum).Sum
        [PSCustomObject]@{
            Category      = $_.Name
            FileCount     = $_.Count
            ReclaimableMB = [math]::Round($CatBytes / 1MB, 2)
            ReclaimableGB = [math]::Round($CatBytes / 1GB, 3)
        }
    }
    Write-Host "=== Breakdown by Category ===" -ForegroundColor Cyan
    $CategorySummary | Format-Table -AutoSize

    if ($PSCmdlet.ShouldProcess($OutputCsvPath, "Export $($Results.Count) obsolete file records to CSV")) {
        $Results | Sort-Object -Property SizeBytes -Descending | Export-Csv -LiteralPath $OutputCsvPath -NoTypeInformation -Encoding UTF8
        Write-Host "CSV report exported to: $OutputCsvPath" -ForegroundColor Green
    }
} else {
    Write-Host "No matching obsolete files found (or execution ran in -WhatIf mode)." -ForegroundColor Yellow
}
