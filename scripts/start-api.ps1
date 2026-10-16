$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
& '.\.venv\Scripts\python.exe' -m uvicorn videofacturacion.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
