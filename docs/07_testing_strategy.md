# 07 - Testing Strategy

## Principio central

Las pruebas de equivalencia son independientes:

```text
Casos input -> Excel -> expected outputs visibles
Casos input -> Django -> actual outputs
Comparación -> validate_excel_battery
```

Excel es la fuente de verdad funcional. Django nunca debe generar sus propios expected outputs.

## Tipos de prueba

### 1. Unit tests Django

Cubren piezas internas:

- consolidación de pallets/cartons;
- pallet weight y pallet cubic;
- tailgate;
- weight breaks;
- funciones pequeñas del cálculo.

Comando típico:

```powershell
docker compose exec web python manage.py test apps.freight.tests -v 2
```

### 2. Batería fija `live_latest`

Casos reales conocidos. No debe sobrescribirse sin decisión explícita.

Archivos:

```text
app/apps/freight/fixtures/live_latest/sth_excel_generated_cases.csv
app/apps/freight/fixtures/live_latest/sth_excel_generated_outputs.csv
app/apps/freight/fixtures/live_latest/sth_excel_generated_components.csv
```

Último estado conocido antes de cambios posteriores:

```text
Cases run: 20
Report rows: 97
OK rows: 97
FAIL rows: 0
```

Después de cambios en cálculo, debe volver a ejecutarse.

### 3. Batería random `random_current`

Carpeta fija reutilizable. Se sobrescribe en cada corrida.

Archivos:

```text
app/apps/freight/fixtures/random_current/sth_excel_random_cases.csv
app/apps/freight/fixtures/random_current/sth_excel_random_outputs.csv
app/apps/freight/fixtures/random_current/sth_excel_random_components.csv
reports/random_current/sth_excel_random_comparison_report.csv
```

No crear carpetas nuevas por cantidad de casos (`random_5`, `random_20`, etc.) salvo que se quiera archivar evidencia específica. Para trabajo diario, usar siempre `random_current`.

## Qué se compara

| Row type | Qué valida |
|---|---|
| `rank_output` | carrier, service, estimate ex GST por rank |
| `component_totals` | total weight y total cubic visible |

## Regla de cubic

La batería compara contra cubic visible:

```text
Calculator!J24
```

Si Django entrega rating cubic interno, la batería debe convertirlo:

```text
visible_cubic = rating_cubic - pallets × 0.02
```

## Casos sin carrier

Excel puede generar componentes pero ningún rank visible. En ese caso la batería debe comparar componentes usando `consolidate_lines()` aunque no exista `actual_first` de Django.

Este comportamiento fue corregido con fallback en `validate_excel_battery.py`.

## Definition of Done para un fix de cálculo

Un cambio de cálculo se considera terminado solo si:

1. existe un caso Excel reproducible;
2. se identifica el expected visible desde `Calculator`;
3. Django reproduce carrier/service/estimate o se documenta una excepción;
4. `component_totals` queda OK;
5. la batería afectada queda con `FAIL rows: 0` o se registra un bug abierto;
6. se actualizan los Markdown relevantes.
