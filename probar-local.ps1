<#
.SINOPSIS
  Levanta el backend y el frontend de ESTE ambiente apuntando solo a localhost, sin crear
  ningún túnel de Cloudflare. Úsalo cuando quieras probar en tu propia PC (o en el navegador
  del celular conectado a la MISMA red WiFi, usando la IP local en vez de "localhost") sin
  depender de que trycloudflare.com esté disponible.

.USO
  Desde la raíz del repo, en una terminal de PowerShell:
    .\probar-local.ps1

  Si vas a correr Dev/QA/PRD en paralelo (cada worktree en su carpeta), usa puertos distintos:
    .\probar-local.ps1 -BackendPort 8001 -FrontendPort 5174
#>

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot

Write-Host "1) Deteniendo procesos anteriores de ESTA carpeta (puertos $BackendPort / $FrontendPort)..." -ForegroundColor Cyan
& (Join-Path $repoRoot "detener-tunel.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort

Write-Host "2) Apuntando el frontend a localhost (sin túnel)..." -ForegroundColor Cyan
$envDevPath = Join-Path $repoRoot "web\.env.development"
$envDevContent = Get-Content $envDevPath -Raw
$envDevContent = $envDevContent -replace "(?m)^VITE_API_URL=\S+", "VITE_API_URL=http://localhost:$BackendPort"
Set-Content -Path $envDevPath -Value $envDevContent -NoNewline

Write-Host "3) Asegurando que CORS_ORIGINS incluya el origin local del frontend..." -ForegroundColor Cyan
$envPath = Join-Path $repoRoot ".env"
$envLines = Get-Content $envPath
$localOrigin = "http://localhost:$FrontendPort"
$newLines = @()
foreach ($line in $envLines) {
    if ($line -like "CORS_ORIGINS=*") {
        # Se quitan entradas viejas de trycloudflare.com (de una corrida anterior con túnel) —
        # para pruebas locales no hacen falta y solo ensucian la lista.
        $origins = @($line.Substring(13) -split "," | Where-Object { $_ -and ($_ -notlike "*trycloudflare.com*") })
        if ($origins -notcontains $localOrigin) { $origins += $localOrigin }
        $newLines += "CORS_ORIGINS=" + ($origins -join ",")
    } else {
        $newLines += $line
    }
}
Set-Content -Path $envPath -Value $newLines

Write-Host "4) Levantando backend y frontend (sin cloudflared)..." -ForegroundColor Cyan
Start-Process -WindowStyle Hidden -FilePath "$repoRoot\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "$BackendPort" `
    -WorkingDirectory $repoRoot
Start-Process -WindowStyle Hidden -FilePath "node" `
    -ArgumentList "node_modules/vite/bin/vite.js", "--port", "$FrontendPort", "--host" `
    -WorkingDirectory (Join-Path $repoRoot "web")

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " Abre esto en tu navegador:"
Write-Host " http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host ""
Write-Host " (Si quieres probarlo desde el celular SIN túnel, debe estar en la MISMA WiFi que"
Write-Host " esta PC — usa la IP local de esta máquina en vez de 'localhost', ej. http://192.168.1.4:$FrontendPort)"
Write-Host "===========================================" -ForegroundColor Cyan
