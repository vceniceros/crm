param(
    [string]$AdminEmail = "admin@ycc.local",
    [string]$AdminPassword = "changeme-secure-password",
    [string]$BaseAuthUrl = "http://localhost:8001",
    [string]$BaseCrmUrl = "http://localhost:8010"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/7] Healthcheck auth interno..."
$authHealth = Invoke-RestMethod -Uri "$BaseAuthUrl/health" -Method Get
if ($authHealth.status -ne "ok") { throw "Auth healthcheck failed" }

Write-Host "[2/7] Login vía CRM backend..."
$loginBody = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
if ($loginResponse.status -ne "authenticated") { throw "CRM login failed" }

$token = $loginResponse.tokens.access_token
if (-not $token) { throw "No access token received" }

$headers = @{ Authorization = "Bearer $token" }

Write-Host "[3/7] Token aceptado por backend CRM (/auth/me)..."
$me = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/me" -Method Get -Headers $headers
if ($me.status -ne "authenticated") { throw "CRM /auth/me rejected token" }

Write-Host "[4/7] Menú de gestión de usuarios (API settings/auth-users)..."
$users = Invoke-RestMethod -Uri "$BaseCrmUrl/settings/auth-users" -Method Get -Headers $headers
if ($null -eq $users) { throw "Auth users endpoint failed" }

Write-Host "[5/7] Crear usuario operativo de prueba..."
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$newEmail = "qa.user.$timestamp@ycc.local"
$newUserBody = @{
    email = $newEmail
    display_name = "QA User $timestamp"
    password = "Passw0rd!qa"
    is_active = $true
    roles = @("operador_deposito")
} | ConvertTo-Json
$newUser = Invoke-RestMethod -Uri "$BaseCrmUrl/settings/auth-users" -Method Post -Headers $headers -ContentType "application/json" -Body $newUserBody
if ($newUser.email -ne $newEmail) { throw "User create failed" }

Write-Host "[6/7] Login del usuario creado en auth interno..."
$newLoginBody = @{ email = $newEmail; password = "Passw0rd!qa" } | ConvertTo-Json
$newLogin = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $newLoginBody
if ($newLogin.status -ne "authenticated") { throw "New user login failed" }

Write-Host "[7/7] Re-ejecutar bootstrap idempotente dentro del contenedor auth..."
$bootstrapResult = docker exec crm-auth-local python -m src.cli ensure_crm_bootstrap
if ($LASTEXITCODE -ne 0) { throw "Bootstrap command failed" }

Write-Host "OK - Verificación interna completada"
Write-Host "Usuario creado: $newEmail"
