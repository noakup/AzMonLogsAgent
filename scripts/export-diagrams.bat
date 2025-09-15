@echo off
REM Export Mermaid diagrams to SVG & PNG using mermaid-cli (mmdc)
REM Requires Node.js and global install: npm install -g @mermaid-js/mermaid-cli

where mmdc >nul 2>&1
IF ERRORLEVEL 1 (
  echo mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli
  exit /b 1
)

for %%F in (project_summary\*.mmd) do (
  echo Exporting %%~nxF
  mmdc -i %%F -o project_summary\%%~nF.svg
  mmdc -i %%F -o project_summary\%%~nF.png
)

echo Done.
