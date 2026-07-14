# 09 - Troubleshooting

## relation "clients_client" does not exist

Causa: PostgreSQL partió sin migraciones para las apps del proyecto.

Solución destructiva para entorno local:

```powershell
docker compose down -v
docker compose build --no-cache
docker compose up
```

Solución no destructiva:

```powershell
docker compose exec web python manage.py migrate --noinput
```

## Invalid HTTP_HOST header

Agregar la IP local a `ALLOWED_HOSTS`, por ejemplo:

```text
192.168.1.106
```

## Excel random muestra postcode viejo `3023`

Síntoma:

```text
suburb_written cambia
state_written cambia
postcode_readback = 3023 para todos los casos
```

Causa: `generate_excel_expected_outputs.py` escribía `suburb` y `state`, pero no escribía `postcode` en `Calculator!E7`.

Fix:

```python
set_cell(ws, args.postcode_cell, clean_text(row.get("postcode")))
```

Validación:

```powershell
Import-Csv .\generated_excel_baselinesandom_current\sth_excel_generation_debug.csv |
  Select-Object case_id,suburb_written,state_written,postcode_written,postcode_readback |
  Format-Table -Auto
```

## rank_output falla por zona incorrecta

Síntoma:

- Excel usa el suburb real.
- Django usa la primera fila del mismo postcode.

Ejemplos observados:

- `YARROWYCK NSW 2358`: Django tomaba otra localidad por postcode y zona `BNE4`; Excel usa `YARROWYCK` y zona `BNE5`.
- `BALL BAY QLD 4740`: Django tomaba zona `MYK1`; Excel usa `BALL BAY` y zona `MYK2`.

Fix: resolver primero `suburb + state`, luego fallback por postcode solo si corresponde.

## component_totals falla con actual vacío

Síntoma:

```text
expected_total_weight_kg tiene valor
actual_total_weight_kg vacío
Excel generated_output_count = 0
```

Causa: Excel generó componentes pero ningún carrier visible. La batería intentaba tomar componentes desde el primer rank de Django.

Fix: usar fallback de `consolidate_lines()` para `component_totals` aunque no haya carrier/rank.

## component_totals falla por cubic 0.02 × pallets

Síntoma:

```text
expected_total_cubic_m3 = Calculator!J24
actual_total_cubic_m3 = CalcLines!P29 o rating cubic
```

Causa: se compara cubic visible contra cubic de rating.

Fix:

```text
visible_cubic = rating_cubic - pallets × 0.02
```

## KTI diferencias pequeñas de centavos

Causa: `FreightRate` guardaba tarifas con 4 decimales y Excel usaba más precisión.

Fix: migración `0002_increase_freightrate_precision.py` para 6 decimales y reimportar workbook.

## TEAMTAS GENERAL extremadamente alto

Síntoma observado:

```text
WEEGENA TAS 7304
SKU BRH4443 qty 2
Excel TEAMTAS GENERAL = 828.03
Django TEAMTAS GENERAL = 663983.07
rate_source_row = 4154
lookup_key = TEAMTASGENERALLZ25STHP
```

Diagnóstico parcial:

```text
basic_charge = 1.82
per_kg = 186.25
weight = 3565 kg
generic per_kg × kg = 663983.07
per tonne candidate = 665.81
Excel expected = 828.03
```

Estado: abierto. No aplicar parche incompleto hasta identificar el cargo faltante `162.22` o fórmula exacta en Excel.
