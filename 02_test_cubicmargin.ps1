[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [Parameter(Mandatory = $false)]
    [string]$WebService = "web",

    [Parameter(Mandatory = $false)]
    [switch]$RunFullSuite
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $ProjectRoot).Path)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportDir = Join-Path $ProjectRoot "test_reports"
$reportFile = Join-Path $reportDir "cubicmargin_test_$timestamp.log"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Write-Report([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $reportFile -Value $line -Encoding UTF8
}

function Invoke-Checked([string]$Description, [scriptblock]$Command) {
    Write-Report "INICIO: $Description"
    & $Command 2>&1 | Tee-Object -FilePath $reportFile -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Report "FALLO: $Description (código $LASTEXITCODE)"
        throw "La prueba falló: $Description. Revisa $reportFile"
    }
    Write-Report "OK: $Description"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker no está disponible en PATH."
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "docker-compose.yml"))) {
    throw "No se encontró docker-compose.yml en ProjectRoot."
}

Push-Location $ProjectRoot
try {
    Write-Report "Proyecto: $ProjectRoot"
    Write-Report "Servicio web: $WebService"

    Invoke-Checked "Validar configuración de Docker Compose" {
        docker compose config --quiet
    }

    Invoke-Checked "Comprobar que el servicio web está disponible" {
        docker compose ps $WebService
    }

    # Si el servicio no está iniciado, lo construye y levanta.
    $running = docker compose ps --status running --services
    if ($running -notcontains $WebService) {
        Write-Report "El servicio $WebService no está activo. Construyendo e iniciando..."
        Invoke-Checked "Construir e iniciar servicio web" {
            docker compose up -d --build $WebService
        }
    }

    Invoke-Checked "Consultar versión de Django" {
        docker compose exec -T $WebService python -m django --version
    }

    Invoke-Checked "Compilar sintácticamente los archivos modificados" {
        docker compose exec -T $WebService python -m py_compile `
            /app/apps/freight/services/calculator.py `
            /app/apps/freight/tests/test_cubic_margin.py
    }

    Invoke-Checked "Django system check" {
        docker compose exec -T $WebService python /app/manage.py check
    }

    Invoke-Checked "Comprobar migraciones pendientes" {
        docker compose exec -T $WebService python /app/manage.py makemigrations --check --dry-run
    }

    Invoke-Checked "Ejecutar pruebas específicas de CubicMargin" {
        docker compose exec -T $WebService python /app/manage.py test `
            apps.freight.tests.test_cubic_margin -v 2
    }

    Invoke-Checked "Ejecutar pruebas del módulo freight" {
        docker compose exec -T $WebService python /app/manage.py test `
            apps.freight.tests -v 2
    }

    if ($RunFullSuite) {
        Invoke-Checked "Ejecutar suite completa del proyecto" {
            docker compose exec -T $WebService python /app/manage.py test -v 2
        }
    }
    else {
        Write-Report "Suite completa omitida. Usa -RunFullSuite para ejecutarla."
    }

    # Validación estática final de los límites y del campo HTML.
    $templateFile = Join-Path $ProjectRoot "app\templates\freight\calculator.html"
    $calculatorFile = Join-Path $ProjectRoot "app\apps\freight\services\calculator.py"
    $testFile = Join-Path $ProjectRoot "app\apps\freight\tests\test_cubic_margin.py"

    $template = Get-Content -LiteralPath $templateFile -Raw
    $calculator = Get-Content -LiteralPath $calculatorFile -Raw
    $tests = Get-Content -LiteralPath $testFile -Raw

    if ($template -notmatch 'type\s*=\s*["'']number["'']') {
        throw "calculator.html no contiene el input numérico esperado."
    }
    if ($template -notmatch 'min\s*=\s*["'']0["'']' -or $template -notmatch 'max\s*=\s*["'']20["'']') {
        throw "calculator.html no contiene los límites 0–20."
    }
    if ($calculator -notmatch "MAX_CUBIC_MARGIN_PERCENT\s*=\s*Decimal\(['""]20['""]\)") {
        throw "calculator.py no contiene el límite 20."
    }
    if ($tests -notmatch "test_rejects_fractional_margin") {
        throw "No se encontró la prueba para margen decimal."
    }

    Write-Report "OK: validación estática final"
    Write-Report "TODAS LAS PRUEBAS SOLICITADAS TERMINARON CORRECTAMENTE"
    Write-Host ""
    Write-Host "INSTALACIÓN VERIFICADA" -ForegroundColor Green
    Write-Host "Informe: $reportFile"
}
catch {
    Write-Report "RESULTADO FINAL: ERROR - $($_.Exception.Message)"
    Write-Host ""
    Write-Host "LA VERIFICACIÓN FALLÓ" -ForegroundColor Red
    Write-Host "Informe: $reportFile"
    exit 1
}
finally {
    Pop-Location
}
