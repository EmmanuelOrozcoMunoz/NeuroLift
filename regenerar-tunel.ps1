<#
.SINOPSIS
  Regenera los túneles de Cloudflare (backend + frontend) para probar NeuroLift desde el
  celular con una URL pública, y reinicia el backend y el dev server de Vite ya apuntando
  a esa URL nueva.

.USO
  Desde la raíz del repo, en una terminal de PowerShell:
    .\regenerar-tunel.ps1

  Si Windows se queja de la política de ejecución de scripts, corre en vez esto:
    powershell -ExecutionPolicy Bypass -File .\regenerar-tunel.ps1

  Puertos por defecto: 8000 (backend) y 5173 (frontend) — los mismos de siempre. Si vas a
  correr este mismo repo en más de una carpeta a la vez (Dev/QA/PRD como worktrees de git,
  cada uno en su propia carpeta), cada uno necesita puertos DISTINTOS para no pisarse:
    .\regenerar-tunel.ps1 -BackendPort 8001 -FrontendPort 5174

.NOTA
  Los links de trycloudflare.com son gratuitos y no requieren cuenta, pero son ALEATORIOS
  cada vez que se relanza el túnel — es justo lo que este script hace, así que después de
  correrlo tendrás links NUEVOS. Compártele al celular los que imprima al final.
#>

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    # algunas instalaciones de winget lo dejan en Program Files (sin x86)
    $cloudflared = "C:\Program Files\cloudflared\cloudflared.exe"
}
if (-not (Test-Path $cloudflared)) {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { $cloudflared = $cmd.Source }
}
if (-not (Test-Path $cloudflared)) {
    Write-Host "No se encontró cloudflared.exe. Instálalo con: winget install --id Cloudflare.cloudflared" -ForegroundColor Red
    exit 1
}

$logsDir = Join-Path $repoRoot ".tunnels"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$backendLog = Join-Path $logsDir "backend.log"
$frontendLog = Join-Path $logsDir "frontend.log"

# Lanza un túnel rápido y espera su URL, reintentando si Cloudflare falla al provisionarlo
# ("failed to request quick Tunnel: ... context deadline exceeded" — timeout de red contra
# Cloudflare, no un error de este script; el servicio gratis de túneles rápidos a veces se
# satura). Antes, un fallo así dejaba en el log el mensaje de error con la URL de la API de
# Cloudflare (https://api.trycloudflare.com) y el script la confundía con la URL real del
# túnel — por eso el regex de éxito EXCLUYE explícitamente el subdominio "api.".
function Start-QuickTunnel {
    param(
        [string]$LocalUrl,
        [string]$LogPath,
        [string]$Label
    )
    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        Remove-Item $LogPath -ErrorAction SilentlyContinue
        Start-Process -WindowStyle Hidden -FilePath $cloudflared `
            -ArgumentList "tunnel", "--url", $LocalUrl `
            -RedirectStandardError $LogPath

        for ($i = 0; $i -lt 15; $i++) {
            Start-Sleep -Seconds 1
            if (-not (Test-Path $LogPath)) { continue }
            $contenido = Get-Content $LogPath -Raw -ErrorAction SilentlyContinue
            if ($contenido -match "https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com") {
                return $Matches[0]
            }
            if ($contenido -match "failed to request quick Tunnel") {
                break  # corta la espera interna para reintentar con un proceso nuevo
            }
        }

        Write-Host "   $Label : intento $attempt de $maxAttempts fallo (Cloudflare no respondio a tiempo), reintentando..." -ForegroundColor Yellow
        Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    return $null
}

Write-Host "1) Deteniendo túneles y servidores anteriores de ESTA carpeta..." -ForegroundColor Cyan

# Cloudflared no tiene una carpeta de trabajo propia del repo, así que se identifica por el
# puerto que túnel — así, si tienes Dev/QA/PRD corriendo en paralelo (cada uno en su propia
# carpeta vía git worktree, con -BackendPort/-FrontendPort distintos), correr esto en una
# carpeta nunca mata el túnel de las otras.
Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*localhost:$BackendPort*" -or $_.CommandLine -like "*localhost:$FrontendPort*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Matar solo por el PID que tiene el puerto en este instante NO basta: uvicorn --reload separa
# un proceso "padre" (vigila archivos) de un "hijo" (el que de verdad sirve peticiones, vía
# multiprocessing en Windows). Si solo se mata al hijo, el padre queda vivo sin nada escuchando
# y en la siguiente corrida vuelve a competir por el puerto — o peor, un hijo viejo con el
# .env de ANTES queda huérfano reteniendo el puerto con la config vieja (CORS desactualizado).
# Se filtra por la ruta del ejecutable de ESTE repo (cada worktree de Dev/QA/PRD tiene su
# propio venv), para no tocar el uvicorn de otra carpeta corriendo en paralelo.
Get-CimInstance Win32_Process -Filter "name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -like "$repoRoot*" -and
        ($_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*multiprocessing.spawn*")
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Reintenta varias veces en vez de matar una sola vez y seguir a ciegas: un hijo de
# uvicorn --reload puede tardar un instante en morir, o (si sigue vivo) el próximo backend
# ni siquiera logra levantar en el puerto y queda un proceso viejo respondiendo con el .env
# de ANTES (CORS desactualizado) sin que nada lo avise. Se verifica de verdad que el puerto
# haya quedado libre antes de continuar.
foreach ($port in $BackendPort, $FrontendPort) {
    $intentos = 0
    do {
        $conns = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        foreach ($c in $conns) {
            $ownerPid = $c.OwningProcess
            Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
            # taskkill /T mata también al árbol de hijos (por si Stop-Process solo alcanzó al padre)
            & taskkill /F /T /PID $ownerPid 2>$null | Out-Null

            # uvicorn --reload en Windows separa un "padre" de un hijo real (nacido por
            # multiprocessing) que es quien de verdad tiene el socket — pero Windows a veces
            # sigue atribuyéndole el puerto al PID del padre aunque ya esté muerto (entrada
            # "fantasma" en la tabla TCP). Ese hijo real se identifica por llevar su propio
            # "parent_pid=<pid>" en el commandline, así que se busca y mata por ahí también.
            Get-CimInstance Win32_Process -Filter "name='python.exe'" -ErrorAction SilentlyContinue |
                Where-Object { $_.CommandLine -match "parent_pid=$ownerPid\D" } |
                ForEach-Object {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                    & taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null
                }
        }
        if ($conns.Count -gt 0) {
            Start-Sleep -Seconds 1
            $intentos++
        }
    } while ($conns.Count -gt 0 -and $intentos -lt 8)

    $siguenVivos = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($siguenVivos.Count -gt 0) {
        Write-Host "   AVISO: el puerto $port sigue ocupado (PID $($siguenVivos[0].OwningProcess)) tras $intentos intentos - ciérralo manualmente desde el Administrador de tareas y vuelve a correr el script." -ForegroundColor Red
        exit 1
    }
}
Start-Sleep -Seconds 1

Write-Host "2) Abriendo túneles de Cloudflare (todavía sin backend/frontend corriendo, es normal)..." -ForegroundColor Cyan
Write-Host "   Esperando a que Cloudflare asigne las URLs (reintenta solo si hace falta)..." -ForegroundColor DarkGray
$backendUrl = Start-QuickTunnel -LocalUrl "http://localhost:$BackendPort" -LogPath $backendLog -Label "Backend"
$frontendUrl = Start-QuickTunnel -LocalUrl "http://localhost:$FrontendPort" -LogPath $frontendLog -Label "Frontend"

if (-not $backendUrl -or -not $frontendUrl) {
    Write-Host "No se pudo levantar el tunel tras varios intentos (Cloudflare puede estar saturado en este momento). Revisa los logs en $logsDir o intenta de nuevo en un minuto." -ForegroundColor Red
    exit 1
}

Write-Host "   Backend:  $backendUrl" -ForegroundColor Green
Write-Host "   Frontend: $frontendUrl" -ForegroundColor Green

Write-Host "3) Actualizando configuración (.env y web\.env.development)..." -ForegroundColor Cyan

$envDevPath = Join-Path $repoRoot "web\.env.development"
$envDevContent = Get-Content $envDevPath -Raw
# (?m)^ ancla al INICIO de línea: así no toca la línea comentada de ejemplo más abajo
# (que también contiene el texto "VITE_API_URL=..." pero precedido de "# ").
$envDevContent = $envDevContent -replace "(?m)^VITE_API_URL=\S+", "VITE_API_URL=$backendUrl"
Set-Content -Path $envDevPath -Value $envDevContent -NoNewline

$envPath = Join-Path $repoRoot ".env"
$envLines = Get-Content $envPath
$newLines = @()
foreach ($line in $envLines) {
    if ($line -like "CORS_ORIGINS=*") {
        $origins = $line.Substring(13) -split "," | Where-Object { $_ -and ($_ -notlike "*trycloudflare.com*") }
        $origins = @($origins) + $frontendUrl
        $newLines += "CORS_ORIGINS=" + ($origins -join ",")
    }
    else {
        $newLines += $line
    }
}
Set-Content -Path $envPath -Value $newLines

Write-Host "4) Levantando backend y frontend con la configuración nueva..." -ForegroundColor Cyan
Start-Process -WindowStyle Hidden -FilePath "$repoRoot\venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "$BackendPort" `
    -WorkingDirectory $repoRoot
Start-Process -WindowStyle Hidden -FilePath "node" `
    -ArgumentList "node_modules/vite/bin/vite.js", "--port", "$FrontendPort", "--host" `
    -WorkingDirectory (Join-Path $repoRoot "web")

Start-Sleep -Seconds 5

Write-Host "5) Verificando..." -ForegroundColor Cyan
try {
    $r1 = Invoke-WebRequest -Uri $backendUrl -UseBasicParsing -TimeoutSec 10
    Write-Host "   Backend  -> $($r1.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   Backend  -> todavía no responde, dale unos segundos más y reintenta en el navegador" -ForegroundColor Yellow
}
try {
    $r2 = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 10
    Write-Host "   Frontend -> $($r2.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   Frontend -> todavía no responde, dale unos segundos más y reintenta en el navegador" -ForegroundColor Yellow
}

# Si por lo que sea quedó más de un proceso escuchando el mismo puerto, uno de los dos tiene
# el .env viejo (típicamente el CORS desactualizado) — mejor avisar que fallar en silencio.
$backendOwners = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
if ($backendOwners.Count -gt 1) {
    Write-Host "   AVISO: hay $($backendOwners.Count) procesos escuchando en el puerto $BackendPort - corre el script de nuevo." -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " Abre esto en el celular:"
Write-Host " $frontendUrl" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan
