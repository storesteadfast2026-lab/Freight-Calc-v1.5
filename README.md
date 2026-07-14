# STH Freight Platform

Aplicación Django/PostgreSQL para migrar la lógica de la planilla `V2026.R2_Unlocked_STH_Freight_Calculator.xlsx` hacia una plataforma web multi-cliente.

## Estado actual del proyecto

Este proyecto usa Excel como fuente de verdad funcional. La estrategia actual es:

1. generar casos de prueba independientes;
2. ejecutar esos casos en Excel con automatización COM;
3. leer los resultados visibles desde la hoja `Calculator`;
4. ejecutar los mismos casos en Django;
5. comparar Django vs Excel con `validate_excel_battery`.

La regla principal es: **Excel no se valida contra Django; Django se valida contra Excel**.

## Estado de validación conocido

- `live_latest`: batería fija de 20 casos reales generada desde Excel. Último resultado conocido antes de los cambios posteriores: 97 filas OK, 0 FAIL.
- `random_current`: carpeta fija reutilizable para pruebas random. Se sobrescribe en cada nueva corrida.
- Correcciones ya incorporadas/documentadas:
  - escritura de postcode en `Calculator!E7` desde el generador Excel;
  - comparación visual de cubic contra `Calculator!J24`, no contra `CalcLines!P29`;
  - fallback de `component_totals` cuando Excel no genera carrier/rank;
  - resolución de zona priorizando `suburb + state` antes de postcode;
  - precisión de `FreightRate` a 6 decimales para evitar diferencias KTI;
  - uso de `random_current` como carpeta fija de pruebas random.
- Investigación abierta:
  - `TEAMTAS GENERAL` puede calcularse demasiado alto en Django para ciertos casos TAS. Caso observado: `WEEGENA TAS 7304`, SKU `BRH4443`, qty `2`, Excel `828.03`, Django `663983.07` antes de corregir la fórmula base. Ver `docs/12_validation_findings_log.md`.

## Ejecutar con Docker en Windows

```powershell
copy .env.example .env
docker compose up --build
```

Luego abrir:

```text
http://localhost:8000/
http://localhost:8000/admin/
```

## Crear superusuario

```powershell
docker compose exec web python manage.py createsuperuser
```

## Importar Excel de STH

```powershell
docker compose exec web python manage.py import_sth_excel `
  /app/sample_data/V2026.R2_Unlocked_STH_Freight_Calculator.xlsx `
  --client STH `
  --replace
```

## Validación rápida contra Excel

Batería real fija:

```powershell
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

## Documentación principal

Ver carpeta `docs/`.

Lectura recomendada:

1. `docs/00_system_overview.md`
2. `docs/07_testing_strategy.md`
3. `docs/10_excel_django_validation_strategy.md`
4. `docs/11_validation_runbook.md`
5. `docs/12_validation_findings_log.md`
6. `docs/13_ai_spec_driven_workflow.md`

## Autocomplete data

Los campos de suburbios y productos leen desde PostgreSQL. En un volumen Docker limpio, el contenedor importa la planilla de ejemplo después de migraciones si no existen suburbios cargados. Si ya había un volumen antiguo, ejecutar una vez:

```powershell
docker compose down -v
```

Luego volver a levantar el proyecto e importar la planilla.
