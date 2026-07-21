[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $false)]
    [string]$UpdateZip = ".\Create_Files-Review_0721.1308_CubicMargin_0-20.zip",

    [Parameter(Mandatory = $false)]
    [string]$BackupRoot = "",

    [Parameter(Mandatory = $false)]
    [switch]$BackupDatabase,

    [Parameter(Mandatory = $false)]
    [string]$DbService = "db",

    [Parameter(Mandatory = $false)]
    [string]$DbName = "",

    [Parameter(Mandatory = $false)]
    [string]$DbUser = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-FullPath([string]$PathValue) {
    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathValue).Path)
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontró el comando requerido: $Name"
    }
}

$ProjectRoot = Resolve-FullPath $ProjectRoot
$UpdateZip = Resolve-FullPath $UpdateZip

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "app\manage.py"))) {
    throw "ProjectRoot no parece ser la raíz del proyecto: falta app\manage.py"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "docker-compose.yml"))) {
    Write-Warning "No se encontró docker-compose.yml. El reemplazo continuará, pero las pruebas Docker pueden no funcionar."
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    $BackupRoot = Join-Path (Split-Path $ProjectRoot -Parent) "project_backups"
}
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

$backupDir = Join-Path $BackupRoot "before_cubicmargin_$timestamp"
$filesBackupDir = Join-Path $backupDir "replaced_files"
$extractDir = Join-Path $env:TEMP "cubicmargin_update_$timestamp"
$stagingDir = Join-Path $env:TEMP "project_snapshot_$timestamp"
$fullBackupZip = Join-Path $backupDir "project_before_cubicmargin_$timestamp.zip"

New-Item -ItemType Directory -Force -Path $filesBackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null

$relativeFiles = @(
    "app\templates\freight\calculator.html",
    "app\apps\freight\services\calculator.py",
    "app\apps\freight\tests\test_cubic_margin.py"
)

Write-Host "1/6 Creando copia de los archivos que serán reemplazados..."
foreach ($relative in $relativeFiles) {
    $source = Join-Path $ProjectRoot $relative
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $filesBackupDir $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

Write-Host "2/6 Creando respaldo comprimido completo del proyecto..."
# Se excluyen carpetas regenerables o que pueden ser enormes.
$excludedDirs = @(".git", ".venv", "venv", "__pycache__", "node_modules", "project_backups")
$robocopyArgs = @(
    $ProjectRoot,
    $stagingDir,
    "/E",
    "/R:1",
    "/W:1",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/NP",
    "/XD"
) + ($excludedDirs | ForEach-Object { Join-Path $ProjectRoot $_ })

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "Robocopy falló al preparar el respaldo. Código: $LASTEXITCODE"
}

Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $fullBackupZip -CompressionLevel Optimal -Force

if ($BackupDatabase) {
    Write-Host "3/6 Creando respaldo de PostgreSQL..."
    Assert-Command "docker"

    if ([string]::IsNullOrWhiteSpace($DbName)) {
        $DbName = Read-Host "Nombre de la base de datos PostgreSQL"
    }
    if ([string]::IsNullOrWhiteSpace($DbUser)) {
        $DbUser = Read-Host "Usuario PostgreSQL"
    }

    Push-Location $ProjectRoot
    try {
        $dbBackup = Join-Path $backupDir "database_before_cubicmargin_$timestamp.sql"
        cmd /c "docker compose exec -T $DbService pg_dump -U $DbUser $DbName > `"$dbBackup`""
        if ($LASTEXITCODE -ne 0) {
            throw "pg_dump falló. El código del proyecto todavía no fue reemplazado."
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "3/6 Respaldo de base omitido. Usa -BackupDatabase para incluirlo."
}

Write-Host "4/6 Extrayendo el paquete de actualización..."
Expand-Archive -LiteralPath $UpdateZip -DestinationPath $extractDir -Force

foreach ($relative in $relativeFiles) {
    $packageFile = Join-Path $extractDir $relative
    if (-not (Test-Path -LiteralPath $packageFile)) {
        throw "El paquete no contiene el archivo requerido: $relative"
    }
}

Write-Host "5/6 Reemplazando únicamente los archivos de CubicMargin..."
foreach ($relative in $relativeFiles) {
    $source = Join-Path $extractDir $relative
    $destination = Join-Path $ProjectRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

# Corrige la importación de la excepción en la prueba entregada.
$testFile = Join-Path $ProjectRoot "app\apps\freight\tests\test_cubic_margin.py"
$testText = Get-Content -LiteralPath $testFile -Raw
$testText = $testText.Replace(
    "from django.core.exceptions import ValidationError",
    "from apps.freight.services.validators import ValidationError"
)
Set-Content -LiteralPath $testFile -Value $testText -Encoding UTF8

Write-Host "6/6 Verificando que los cambios esperados estén presentes..."
$template = Get-Content -LiteralPath (Join-Path $ProjectRoot "app\templates\freight\calculator.html") -Raw
$calculator = Get-Content -LiteralPath (Join-Path $ProjectRoot "app\apps\freight\services\calculator.py") -Raw

if ($template -notmatch 'max\s*=\s*["'']20["'']') {
    throw "No se encontró max=20 en calculator.html."
}
if ($calculator -notmatch "MAX_CUBIC_MARGIN_PERCENT\s*=\s*Decimal\(['""]20['""]\)") {
    throw "No se encontró MAX_CUBIC_MARGIN_PERCENT = Decimal('20') en calculator.py."
}
if ((Get-Content -LiteralPath $testFile -Raw) -notmatch "apps\.freight\.services\.validators import ValidationError") {
    throw "La importación correcta de ValidationError no quedó aplicada."
}

$manifest = @"
Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Proyecto: $ProjectRoot
Paquete: $UpdateZip
Respaldo completo: $fullBackupZip
Archivos sustituidos:
$($relativeFiles -join "`r`n")
"@
Set-Content -LiteralPath (Join-Path $backupDir "BACKUP_AND_UPDATE_MANIFEST.txt") -Value $manifest -Encoding UTF8

Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $stagingDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "ACTUALIZACIÓN APLICADA CORRECTAMENTE" -ForegroundColor Green
Write-Host "Respaldo: $backupDir"
Write-Host "ZIP completo: $fullBackupZip"
Write-Host ""
Write-Host "Siguiente paso:"
Write-Host ".\02_test_cubicmargin.ps1 -ProjectRoot `"$ProjectRoot`""
