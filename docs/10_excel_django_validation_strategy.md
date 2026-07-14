# 10 - Excel vs Django Validation Strategy

## Objetivo

Tener una forma repetible de probar Django contra Excel sin depender de pruebas manuales caso por caso.

La estrategia separa responsabilidades:

| Etapa | Responsable | Resultado |
|---|---|---|
| Generar inputs | Django / CSV | casos de prueba |
| Calcular expected | Excel automatizado | outputs esperados visibles |
| Calcular actual | Django service | outputs reales |
| Comparar | `validate_excel_battery` | reporte OK/FAIL |

## Regla de independencia

Django puede generar inputs random, pero no puede generar expected outputs. Los expected outputs vienen desde Excel.

## Source of Truth

La comparación de salida usa la hoja `Calculator`:

```text
O6:Q9 = ranked outputs
J23   = total weight
J24   = visible cubic
```

`CalcLines` se usa solo para diagnóstico. No se debe usar `CalcLines` para reemplazar expected visual.

## Artefactos principales

### Generador Excel

```text
tools/excel/generate_excel_expected_outputs.py
```

Responsabilidades:

- abrir una copia del workbook;
- escribir inputs en `Calculator`;
- refrescar/calcular;
- leer outputs visibles;
- escribir CSVs expected;
- generar `manifest.json`;
- generar `sth_excel_generation_debug.csv`.

### Batería Django

```text
app/apps/freight/management/commands/validate_excel_battery.py
```

Responsabilidades:

- leer cases, expected outputs y components;
- construir `FreightRequest`;
- ejecutar `FreightCalculatorService`;
- comparar rank outputs;
- comparar component totals;
- generar reporte CSV.

## Carpetas estándar

### Batería fija real

```text
app/apps/freight/fixtures/live_latest
reports/sth_excel_live_comparison_report.csv
```

### Batería random actual

```text
app/apps/freight/fixtures/random_current
generated_excel_baselines/random_current
sample_data/live_baselines/random_current
reports/random_current
```

`random_current` se sobrescribe. Para evidencia histórica, copiar el reporte a un nombre terminado en `_OK.csv` o con fecha.

## Estados aceptados

| Estado | Significado |
|---|---|
| `OK rows = total rows`, `FAIL rows = 0` | Equivalencia validada para esa batería |
| `rank_output FAIL` | carrier/rank/service/precio no coincide |
| `component_totals FAIL` | peso/cubic no coincide o batería no pudo calcular actual |
| Excel `generated_output_count = 0` | Excel no mostró carrier/rank para ese caso |

## Buenas prácticas

- Guardar siempre `manifest.json` junto al reporte OK.
- No mezclar baselines: importar a PostgreSQL la misma baseline `.xlsx` usada para generar expected outputs.
- Si se corrige cálculo, rerun de random y live_latest.
- Si una prueba random descubre un bug real, convertirla en caso fijo o documentarla en findings.
