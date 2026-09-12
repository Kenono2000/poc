# Requires PowerShell 5+ / PowerShell Core

# The folder(s) containing files to be renamed/converted.
# Update this path for the directory/directories you want to process.
$SourceDirs = @( 
    'D:\projects\Reference'
    #,'D:\projects\Eclipse Vein'
    #,'D:\projects\SeaArt'
    #,'C:\Users\Ken Wong\Downloads'
)

# File type groups. Image files are converted to JPEG when needed.
$imageExts = '.jpg','.jpeg','.png','.gif','.bmp','.tiff','.tif','.webp','.svg','.heic'
$videoExts = '.mp4','.mov','.mkv','.avi','.wmv','.flv','.webm','.mpeg','.mpg'

# Run-specific prefix to ensure temporary names never collide with existing files.
$runId = [guid]::NewGuid().ToString('N')
# Stores mapping from temporary file paths to their final names for the second pass.
$tempMap = [System.Collections.Generic.List[PSObject]]::new()
$tempCounter = 1
$totalFilesProcessed = 0

# Ensure System.Drawing is loaded only once.
function Load-SystemDrawing {
    if (-not ([AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.GetName().Name -eq 'System.Drawing' })) {
        Add-Type -AssemblyName System.Drawing | Out-Null
    }
}

# Convert an image file to JPEG, preserving dimensions and using a standard 24-bit pixel format.
function Convert-ImageToJpeg {
    param(
        [Parameter(Mandatory = $true)] [string] $SourcePath,
        [Parameter(Mandatory = $true)] [string] $DestPath
    )

    # Unsupported extensions that require an external tool like ImageMagick.
    $unsupportedExts = '.webp', '.svg', '.heic'
    $sourceExt = ([System.IO.Path]::GetExtension($SourcePath)).ToLowerInvariant()

    if ($unsupportedExts -contains $sourceExt) {
        if (-not (Get-Command magick -ErrorAction SilentlyContinue)) {
            throw "ImageMagick is required to convert '$SourcePath', but the 'magick' command was not found. Please install ImageMagick and ensure it is in your PATH."
        }
        try {
            # Use ImageMagick for formats not supported by System.Drawing.
            & magick "$SourcePath" -background white -flatten -quality 90 "$DestPath"
        } catch {
            throw "ImageMagick conversion for '$SourcePath' failed. Original error: $_"
        }
        return
    }

    try {
        Load-SystemDrawing
        $img = [System.Drawing.Image]::FromFile($SourcePath)
        try {
            $pixelFormat = [System.Drawing.Imaging.PixelFormat]::Format24bppRgb
            $bmp = New-Object System.Drawing.Bitmap -ArgumentList $img.Width, $img.Height, $pixelFormat
            $graphics = [System.Drawing.Graphics]::FromImage($bmp)

            # White background ensures transparent images are flattened cleanly.
            $graphics.Clear([System.Drawing.Color]::White)
            $graphics.DrawImage($img, 0, 0, $img.Width, $img.Height)
            $graphics.Dispose()

            # Configure JPEG encoder to save with 90% quality.
            $encoder = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
            $encParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
            $encParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, 90L)
            $bmp.Save($DestPath, $encoder, $encParams)
        } finally {
            $img.Dispose()
            if ($bmp) { $bmp.Dispose() }
        }
    } catch {
        throw "Image conversion failed for '$SourcePath': $_"
    }
}

# Create a temporary name and move or convert the file into that temporary location.
function Add-TempRename($file, $finalName) {
    $origExt = $file.Extension.ToLowerInvariant()

    # Convert non-JPEG images to JPEG and use .jpeg for the temp file.
    $isJpeg = $origExt -in ('.jpg', '.jpeg')
    $tempExt = if ($imageExts -contains $origExt -and -not $isJpeg) { '.jpeg' } else { $origExt }
    $tempName = "__tmp_${runId}_$tempCounter$tempExt"
    $tempPath = Join-Path $file.DirectoryName $tempName

    if ($imageExts -contains $origExt -and -not $isJpeg) { # This is a conversion
        try {
            Convert-ImageToJpeg -SourcePath $file.FullName -DestPath $tempPath -ErrorAction Stop
            # If conversion is successful, remove the original file.
            Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
        }
        catch {
            Write-Warning "Failed to convert and replace '$($file.FullName)'. It will be skipped. Reason: $($_.Exception.Message)"
            # Clean up the partially created temp file if it exists to prevent further errors.
            if (Test-Path -LiteralPath $tempPath) {
                Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
            }
            return
        }
    } else { # This is a simple rename
        try {
            Rename-Item -LiteralPath $file.FullName -NewName $tempName -ErrorAction Stop
        }
        catch {
            Write-Warning "Failed to rename '$($file.FullName)'. It will be skipped. Reason: $($_.Exception.Message)"
            return
        }
    }

    # Record the temporary path and final desired name for the second pass.
    $tempMap.Add([PSCustomObject]@{
        TempFullPath = $tempPath
        FinalName    = $finalName
        Directory    = $file.DirectoryName
    }) | Out-Null

    $script:tempCounter++
}

# Generic group processor. It sorts files by creation time and builds final names using a callback.
function Process-Group($filesToProcess, [ScriptBlock]$nameBuilder) {
    $index = 1
    foreach ($file in ($filesToProcess | Sort-Object CreationTime)) {
        # Format sequence number with leading zeros (e.g., 001, 002).
        $seq = "{0:D3}" -f $index
        $finalName = $nameBuilder.Invoke($file, $seq)
        Add-TempRename -file $file -finalName $finalName
        $index++
    }
}

# Build standard names for each category.
function New-ImageName($file, $seq) { "ref-image-$seq.jpeg" }
function New-VideoName($file, $seq) { "ref-video-$seq$($file.Extension.ToLowerInvariant())" }
function New-OtherName($file, $seq) {
    $baseName = [IO.Path]::GetFileNameWithoutExtension($file.Name)
    $ext = $file.Extension.ToLowerInvariant()
    "${baseName}_$seq$ext"
}

# Get all directories to process, including subdirectories.
$dirsToProcess = foreach ($dir in $SourceDirs) {
    if (Test-Path -LiteralPath $dir -PathType Container) {
        # Output the directory itself
        $dir
        # And its subdirectories
        Get-ChildItem -Path $dir -Recurse -Directory | Select-Object -ExpandProperty FullName
    } else {
        Write-Warning "Source directory not found or is not a directory: $dir. Skipping."
    }
}

foreach ($SourceDir in $dirsToProcess) {
    # Gather candidate files from the source directory (non-recursive).
    $files = Get-ChildItem -LiteralPath $SourceDir -File
    if (-not $files) {
        Write-Host "No files found in $SourceDir"
        continue
    }

    $script:totalFilesProcessed += $files.Count

    # Process image, video, and other file groups for the current directory.
    Process-Group ($files | Where-Object { $imageExts -contains $_.Extension.ToLowerInvariant() }) ${function:New-ImageName}
    Process-Group ($files | Where-Object { $videoExts -contains $_.Extension.ToLowerInvariant() }) ${function:New-VideoName}
    # Group remaining files by extension and process each group separately.
    foreach ($group in ($files | Where-Object { -not ($imageExts + $videoExts) -contains $_.Extension.ToLowerInvariant() } | Group-Object { $_.Extension.ToLowerInvariant() })) {
        Process-Group $group.Group ${function:New-OtherName}
    }
}

# Final pass: rename temporary files to their intended final names.
foreach ($entry in $tempMap) {
    $tempPath = $entry.TempFullPath
    $finalName = $entry.FinalName
    $dir = $entry.Directory

    if (-not (Test-Path -LiteralPath $tempPath)) {
        Write-Error "Temporary file missing: $tempPath"
        exit 1
    }

    $destPath = Join-Path $dir $finalName

    # If temp and dest point to the same path, skip to avoid replacing file with itself.
    if ($tempPath -ieq $destPath) {
        Write-Host "Skipping rename; temporary file equals destination: $destPath"
        continue
    }

    # If a target file already exists, remove it first to avoid rename collisions.
    if (Test-Path -LiteralPath $destPath) {
        try {
            # If the destination file already exists, check if it's the same file as our
            # temporary file. This can happen if the script is re-run on an already
            # processed directory where the final name matches a temporary name pattern.
            if ((Get-Item -LiteralPath $destPath).FullName -ieq (Get-Item -LiteralPath $tempPath).FullName) {
                Write-Host "Destination already matches temporary file; skipping: $destPath"
                continue
            }
            Remove-Item -LiteralPath $destPath -Force -ErrorAction Stop
        } catch {
            Write-Error "Failed to remove existing destination '$destPath' before renaming '$tempPath': $_"
            exit 1
        }
    }

    try {
        Move-Item -LiteralPath $tempPath -Destination $destPath -Force -ErrorAction Stop
    } catch {
        Write-Error "Failed to rename temporary '$tempPath' to final name '$finalName': $_"
        exit 1
    }
}

Write-Host "Renaming complete. Processed $totalFilesProcessed files in $($SourceDirs.Count) folder(s)."
