<#
.SYNOPSIS
    Export Mermaid diagrams in project_summary/ to SVG & PNG.
.DESCRIPTION
    Uses @mermaid-js/mermaid-cli (mmdc). Installs locally if not found (optional flag).
.PARAMETER Install
    If provided, will attempt: npm install -g @mermaid-js/mermaid-cli
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/export-diagrams.ps1 -Install
#>
param(
    [switch]$Install,
    [string]$OutDir = "project_summary"
)

$ErrorActionPreference = 'Stop'

if ($Install) {
    Write-Host "Installing mermaid-cli globally..." -ForegroundColor Cyan
    npm install -g @mermaid-js/mermaid-cli
}

if (-not (Get-Command mmdc -ErrorAction SilentlyContinue)) {
    Write-Error "mmdc (Mermaid CLI) not found. Run with -Install or install manually: npm install -g @mermaid-js/mermaid-cli"
    exit 1
}

$diagramFiles = Get-ChildItem project_summary -Filter *.mmd
if (-not $diagramFiles) {
    Write-Warning "No .mmd files found in project_summary/."
    exit 0
}

foreach ($f in $diagramFiles) {
    $svg = Join-Path $OutDir ($f.BaseName + '.svg')
    $png = Join-Path $OutDir ($f.BaseName + '.png')
    Write-Host "Exporting $($f.Name) -> $(Split-Path $svg -Leaf), $(Split-Path $png -Leaf)" -ForegroundColor Green
    mmdc -i $f.FullName -o $svg
    mmdc -i $f.FullName -o $png
}

Write-Host "Done." -ForegroundColor Yellow
