# ==============================================================================
# Cloudflare Quick Tunnel Helper for Decentralized AI Cloud
# Exposes your local Coordinator API or Web Dashboard to the public internet for free.
# ==============================================================================
param(
    [ValidateSet("dashboard", "coordinator")]
    [string]$Target = "dashboard"
)

$cloudflared = Join-Path $PSScriptRoot "tools\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
    Write-Error "cloudflared binary not found at $cloudflared"
    exit 1
}

if ($Target -eq "dashboard") {
    $port = 3000
    Write-Host "[*] Exposing Next.js Web Dashboard on port $port via Cloudflare Tunnel..." -ForegroundColor Cyan
} else {
    $port = 8000
    Write-Host "[*] Exposing FastAPI Coordinator & WebSocket Gateway on port $port via Cloudflare Tunnel..." -ForegroundColor Cyan
}

Write-Host "[*] Starting tunnel... Look for the 'https://*.trycloudflare.com' URL below:`n" -ForegroundColor Green

& $cloudflared tunnel --url "http://localhost:$port"

