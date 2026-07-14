# 11 - Validation Runbook

Comandos operativos para correr las baterías Excel y Django.

## 1. Ubicarse en el proyecto

```powershell
cd C:\Docker-Projects\Freight-Calc-05jun
```

## 2. Activar ambiente Excel

```powershell
.\.venv-excel\Scriptsctivate
```

Debe verse así:

```text
(.venv-excel) PS C:\Docker-Projects\Freight-Calc-05jun>
```

## 3. Generar expected outputs con Excel para `random_current`

```powershell
python .	ools\excel\generate_excel_expected_outputs.py `
  --workbook .\sample_data\V2026.R2_Unlocked_STH_Freight_Calculator.xlsx `
  --cases .ppppsreightixturesandom_current\sth_excel_random_cases.csv `
  --output-dir .\generated_excel_baselinesandom_current `
  --refresh `
  --save-workbook
```

## 4. Verificar debug Excel

```powershell
Import-Csv .\generated_excel_baselinesandom_current\sth_excel_generation_debug.csv |
  Select-Object `
    case_id,
    suburb_written,
    state_written,
    postcode_written,
    postcode_readback,
    calclines_l3_status,
    generated_output_count,
    rank1_carrier_readback,
    rank1_service_readback,
    rank1_estimate_readback |
  Format-Table -Auto
```

No seguir si `postcode_written` y `postcode_readback` no coinciden.

## 5. Copiar outputs a fixtures

```powershell
Copy-Item .\generated_excel_baselinesandom_current\sth_excel_generated_cases.csv `
  .ppppsreightixturesandom_current\sth_excel_random_cases.csv `
  -Force

Copy-Item .\generated_excel_baselinesandom_current\sth_excel_generated_outputs.csv `
  .ppppsreightixturesandom_current\sth_excel_random_outputs.csv `
  -Force

Copy-Item .\generated_excel_baselinesandom_current\sth_excel_generated_components.csv `
  .ppppsreightixturesandom_current\sth_excel_random_components.csv `
  -Force
```

## 6. Copiar baseline Excel

```powershell
$baseline = Get-ChildItem .\generated_excel_baselinesandom_current -Filter "STH_LIVE_BASELINE_*.xlsx" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Copy-Item $baseline.FullName .\sample_data\live_baselinesandom_current\ -Force

$baselineName = $baseline.Name
$baselineName
```

## 7. Importar baseline a PostgreSQL

```powershell
docker compose exec web python manage.py import_sth_excel `
  /app/sample_data/live_baselines/random_current/$baselineName `
  --client STH `
  --replace
```

## 8. Ejecutar batería random

```powershell
docker compose exec web python manage.py validate_excel_battery `
  --cases /app/apps/freight/fixtures/random_current/sth_excel_random_cases.csv `
  --expected /app/apps/freight/fixtures/random_current/sth_excel_random_outputs.csv `
  --components /app/apps/freight/fixtures/random_current/sth_excel_random_components.csv `
  --report /app/reports/random_current/sth_excel_random_comparison_report.csv
```

## 9. Revisar resumen

```powershell
Import-Csv .eportsandom_current\sth_excel_random_comparison_report.csv |
  Group-Object row_type,overall_status |
  Format-Table Count, Name
```

## 10. Ver fallas completas

```powershell
Import-Csv .eportsandom_current\sth_excel_random_comparison_report.csv |
  Where-Object { $_.overall_status -eq "FAIL" } |
  Format-List *
```

## 11. Guardar evidencia OK

```powershell
Copy-Item .eportsandom_current\sth_excel_random_comparison_report.csv `
  .eportsandom_current\sth_excel_random_comparison_report_OK.csv `
  -Force

Copy-Item .\generated_excel_baselinesandom_current\manifest.json `
  .eportsandom_current\manifest_random_current_OK.json `
  -Force
```

## 12. Ejecutar batería fija de 20 casos reales

```powershell
docker compose exec web python manage.py import_sth_excel `
  /app/sample_data/live_baselines/STH_LIVE_BASELINE_20260706_145623.xlsx `
  --client STH `
  --replace


docker compose exec web python manage.py validate_excel_battery `
  --cases /app/apps/freight/fixtures/live_latest/sth_excel_generated_cases.csv `
  --expected /app/apps/freight/fixtures/live_latest/sth_excel_generated_outputs.csv `
  --components /app/apps/freight/fixtures/live_latest/sth_excel_generated_components.csv `
  --report /app/reports/sth_excel_live_comparison_report.csv
```

Resumen:

```powershell
Import-Csv .eports\sth_excel_live_comparison_report.csv |
  Group-Object row_type,overall_status |
  Format-Table Count, Name
```

## 13. Abrir archivos manualmente

```powershell
Start-Process excel.exe ".ppppsreightixturesandom_current\sth_excel_random_cases.csv"
Start-Process excel.exe ".ppppsreightixturesandom_current\sth_excel_random_outputs.csv"
Start-Process excel.exe ".eportsandom_current\sth_excel_random_comparison_report.csv"
```

Abrir último workbook generado:

```powershell
$generatedExcel = Get-ChildItem .\generated_excel_baselinesandom_current -Filter "STH_LIVE_BASELINE_*.xlsx" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Start-Process excel.exe $generatedExcel.FullName
```
