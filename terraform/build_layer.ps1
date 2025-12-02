# Build Lambda layer with dependencies (Windows PowerShell)
# Run this before terraform apply

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Building Lambda layer..."

# Clean up
if (Test-Path "python") { Remove-Item -Recurse -Force "python" }
if (Test-Path "layer.zip") { Remove-Item -Force "layer.zip" }

# Create directory structure
New-Item -ItemType Directory -Path "python" -Force | Out-Null

# Install dependencies
pip install -r ../requirements.txt -t python/ --quiet

# Create zip
Compress-Archive -Path "python" -DestinationPath "layer.zip" -Force

# Clean up
Remove-Item -Recurse -Force "python"

Write-Host "Layer built: $ScriptDir\layer.zip"
