# 04 - External File Imports

## Objetivo

`import_sth_excel` importa el workbook Excel a PostgreSQL para que Django pueda calcular sin depender del archivo en runtime.

```powershell
docker compose exec web python manage.py import_sth_excel `
  /app/sample_data/V2026.R2_Unlocked_STH_Freight_Calculator.xlsx `
  --client STH `
  --replace
```

## Tablas importadas

| Excel | Django |
|---|---|
| `SKUs` | `Product` |
| `SUBURBS` | `Suburb` |
| `FuelSurcharge` | `Carrier`, `CarrierService`, `ClientCarrierConfig` |
| `ZONES` | `FreightZone` |
| `RATES` | `FreightRate` |
| `SettingFlags` | `CarrierTailgateCharge` |

## Precisión de rates

`FreightRate` debe mantener 6 decimales en campos monetarios/tarifas relevantes. Se corrigió un caso donde PostgreSQL guardaba, por ejemplo:

```text
0.101559 -> 0.1016
```

y eso generaba diferencias pequeñas en KTI.

## Baselines Excel importadas

Para pruebas comparativas se puede importar una copia de Excel generada por la automatización:

```powershell
docker compose exec web python manage.py import_sth_excel `
  /app/sample_data/live_baselines/random_current/<STH_LIVE_BASELINE_YYYYMMDD_HHMMSS.xlsx> `
  --client STH `
  --replace
```

El archivo `.xlsx` de baseline se usa para importar los mismos datos sobre los que Excel generó expected outputs.

## Regla de control

Cuando se genera una nueva baseline Excel, se debe importar esa misma baseline antes de correr `validate_excel_battery`. Así se evita comparar expected outputs generados con una versión de datos distinta a la cargada en PostgreSQL.
