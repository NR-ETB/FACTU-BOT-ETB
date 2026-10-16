$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& '.\.venv\Scripts\python.exe' -m streamlit run src/videofacturacion/ui/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
