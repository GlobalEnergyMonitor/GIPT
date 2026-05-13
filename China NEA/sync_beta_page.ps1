$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root "public\beta"
$mirror = Join-Path $root "beta page"

if (-not (Test-Path -LiteralPath $source)) {
    throw "Source folder not found: $source"
}

New-Item -ItemType Directory -Path $mirror -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $source "index.html") -Destination (Join-Path $mirror "index.html") -Force
Copy-Item -LiteralPath (Join-Path $source "app.js") -Destination (Join-Path $mirror "app.js") -Force
Copy-Item -LiteralPath (Join-Path $source "style.css") -Destination (Join-Path $mirror "style.css") -Force

Write-Host "Synced public\beta -> beta page"
