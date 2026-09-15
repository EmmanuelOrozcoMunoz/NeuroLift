<#
.SINOPSIS
  Detiene el túnel de Cloudflare, el backend y el frontend de ESTE ambiente (identificados por
  puerto), sin tocar los procesos de otro ambiente (Dev/QA/PRD) que esté corriendo en paralelo
  en otra carpeta.

.USO
  Desde la raíz del repo, en una terminal de PowerShell:
    .\detener-tunel.ps1

  Si este ambiente usa puertos distintos a los de siempre (8000/5173), pásalos explícitos:
    .\detener-tunel.ps1 -BackendPort 8001 -FrontendPort 5174
#>

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

Write-Host "Deteniendo túnel y servidores en los puertos $BackendPort (backend) y $FrontendPort (frontend)..." -ForegroundColor Cyan

Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*localhost:$BackendPort*" -or $_.CommandLine -like "*localhost:$FrontendPort*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

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
        Write-Host "   AVISO: el puerto $port sigue ocupado (PID $($siguenVivos[0].OwningProcess)) - ciérralo manualmente desde el Administrador de tareas." -ForegroundColor Red
    } else {
        Write-Host "   Puerto $port liberado." -ForegroundColor Green
    }
}

Write-Host "Listo." -ForegroundColor Cyan
