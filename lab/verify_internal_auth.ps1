param(
    [string]$AdminEmail = "admin@ycc.local",
    [string]$AdminPassword = "changeme-secure-password",
    [string]$BaseAuthUrl = "http://localhost:8001",
    [string]$BaseCrmUrl = "http://localhost:8010",
    [string]$AuthContainer = $env:LAB_AUTH_LOCAL_CONTAINER
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AuthContainer)) {
    $stackName = if ([string]::IsNullOrWhiteSpace($env:LAB_STACK_NAME)) { "microtv-crm-ycc" } else { $env:LAB_STACK_NAME }
    $AuthContainer = "$stackName-auth-local"
}

$candidateContainers = @($AuthContainer, "crm-auth-local") | Select-Object -Unique
$resolvedAuthContainer = $null
foreach ($candidate in $candidateContainers) {
    $runningName = docker ps --filter "name=^/$candidate$" --format "{{.Names}}"
    if ($runningName -eq $candidate) {
        $resolvedAuthContainer = $candidate
        break
    }
}
if ([string]::IsNullOrWhiteSpace($resolvedAuthContainer)) {
    throw "Auth container not found. Tried: $($candidateContainers -join ', ')"
}

$seedAccounts = @(
    @{ Email = $AdminEmail; Password = $AdminPassword; Role = "admin" },
    @{ Email = "operador.crm@yccbrothers.com"; Password = "Passw0rd!"; Role = "deposito" },
    @{ Email = "deposito.aux@yccbrothers.com"; Password = "Passw0rd!"; Role = "deposito" },
    @{ Email = "ejecutivo.crm@yccbrothers.com"; Password = "Passw0rd!"; Role = "ejecutivo" },
    @{ Email = "tecnico.campo@yccbrothers.com"; Password = "Passw0rd!"; Role = "tecnico" }
)

Write-Host "[1/6] Healthcheck auth interno..."
$authHealth = Invoke-RestMethod -Uri "$BaseAuthUrl/health" -Method Get
if ($authHealth.status -ne "ok") { throw "Auth healthcheck failed" }

Write-Host "[2/6] Healthcheck CRM backend..."
$crmHealth = Invoke-RestMethod -Uri "$BaseCrmUrl/health" -Method Get
if ($crmHealth.status -ne "ok") { throw "CRM healthcheck failed" }

Write-Host "[3/6] Login admin via CRM backend..."
$loginBody = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
if ($loginResponse.status -ne "authenticated") { throw "CRM login failed" }

$token = $loginResponse.tokens.access_token
if (-not $token) { throw "No access token received" }

$headers = @{ Authorization = "Bearer $token" }

Write-Host "[4/6] Token aceptado por backend CRM (/auth/me)..."
$me = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/me" -Method Get -Headers $headers
if ($me.status -ne "authenticated") { throw "CRM /auth/me rejected token" }

Write-Host "[5/6] Menu de gestion de usuarios (API settings/auth-users)..."
$users = Invoke-RestMethod -Uri "$BaseCrmUrl/settings/auth-users" -Method Get -Headers $headers
if ($null -eq $users) { throw "Auth users endpoint failed" }

Write-Host "[6/6] Logins seed y bootstrap idempotente..."
foreach ($account in $seedAccounts) {
    $body = @{ email = $account.Email; password = $account.Password } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "$BaseCrmUrl/auth/login" -Method Post -ContentType "application/json" -Body $body
    if ($response.status -ne "authenticated") { throw "Seed login failed for $($account.Email)" }
    if ($response.user.primary_role -ne $account.Role) {
        throw "Unexpected role for $($account.Email): expected $($account.Role), got $($response.user.primary_role)"
    }
    Write-Host "  OK $($account.Email) -> $($response.user.primary_role)"
}

$bootstrapResult = docker exec $resolvedAuthContainer python -m src.cli ensure_crm_bootstrap
if ($LASTEXITCODE -ne 0) { throw "Bootstrap command failed" }

Write-Host "OK - Verificacion interna completada"
