$ErrorActionPreference = "Stop"

$targetDir = Join-Path $HOME ".codex\skills"
$finalDir = Join-Path $targetDir "meteor-image"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
$zipPath = Join-Path $tempRoot "meteor-image.zip"
$extractDir = Join-Path $tempRoot "extract"

try {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

    Invoke-WebRequest `
        -Uri "https://github.com/meteor041/meteor-image/archive/refs/heads/main.zip" `
        -OutFile $zipPath

    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

    $sourceDir = Join-Path $extractDir "meteor-image-main"
    if (-not (Test-Path -LiteralPath $sourceDir)) {
        throw "Expected extracted directory not found: $sourceDir"
    }

    if (Test-Path -LiteralPath $finalDir) {
        Remove-Item -LiteralPath $finalDir -Recurse -Force
    }

    Move-Item -LiteralPath $sourceDir -Destination $finalDir
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
