# 12 - Validation Findings Log

Registro de hallazgos importantes descubiertos por baterías Excel vs Django.

## F001 - Postcode no se escribía en Excel

**Síntoma**

```text
postcode_readback = 3023 para todos los casos random
```

**Causa**

`generate_excel_expected_outputs.py` escribía `suburb` y `state`, pero no escribía `postcode` en `Calculator!E7`.

**Fix**

```python
set_cell(ws, args.postcode_cell, clean_text(row.get("postcode")))
```

**Resultado**

`postcode_written` y `postcode_readback` coinciden.

## F002 - Django resolvía zona por postcode antes que suburb

**Síntoma**

`rank_output FAIL` por carrier/precio incorrecto.

**Casos**

- `YARROWYCK NSW 2358`: Django tomó zona de otro suburb con el mismo postcode.
- `BALL BAY QLD 4740`: Django tomó zona `MYK1`; Excel usó `MYK2`.

**Causa**

Django buscaba `FreightZone` primero por postcode.

**Fix**

Resolver primero:

```text
suburb + state
```

y solo después fallback por postcode si corresponde.

**Resultado**

Los `rank_output` de la corrida random corregida pasaron a OK.

## F003 - component_totals fallaba cuando Excel no generaba carrier

**Síntoma**

```text
Excel generated_output_count = 0
expected_total_weight_kg existe
actual_total_weight_kg vacío
```

**Causa**

La batería obtenía componentes desde el primer resultado/rank de Django. Si no había rank, no había `actual_first`.

**Fix**

Fallback a `consolidate_lines()` dentro de `_compare_components()`.

**Detalle importante**

El fallback debe usar cubic visible:

```text
visible_cubic = rating_cubic - pallets × 0.02
```

no `rating_cubic` completo.

**Resultado**

Caso `RANDOM_001` con Excel sin carrier pasó de FAIL a OK.

## F004 - KTI diferencias pequeñas por precisión de rates

**Síntoma**

Diferencias pequeñas de centavos en KTI, por ejemplo `0.26` o `0.05`.

**Causa**

Rates importados con 4 decimales. Excel usaba mayor precisión.

**Fix**

`FreightRate` aumentado a 6 decimales y reimportación del workbook.

**Resultado**

Batería fija de 20 casos llegó a 97 OK / 0 FAIL antes de cambios posteriores.

## F005 - TEAMTAS GENERAL extremadamente alto

**Estado**: abierto.

**Caso**

```text
case_id: RANDOM_004
suburb: WEEGENA
state: TAS
postcode: 7304
tailgate: NO
sku_1: BRH4443
qty_1: 2
```

**Excel**

```text
TEAMTAS GENERAL = 828.03
```

**Django observado**

```text
TEAMTAS GENERAL = 663983.07
rate_lookup_key = TEAMTASGENERALLZ25STHP
rate_source_row = 4154
chargeable_weight = 3565
freight_base = 663983.07
```

**Rate row 4154**

```text
carrier = TEAMTAS
service = GENERAL
zone = LZ2
weight_break = 5
freight_type = P
minimum_charge = 140.000000
basic_charge = 1.820000
per_kg = 186.250000
fuel = 0
```

**Diagnóstico parcial**

```text
Generic formula: basic + per_kg × kg = 663983.07
Per-tonne candidate: basic + per_kg × kg / 1000 = 665.81
Excel expected: 828.03
Difference remaining: 162.22
```

**Descartado**

No hay `CarrierTailgateCharge` para `TEAMTAS` y la config muestra:

```text
tailgate_enabled = False
hand_unload_enabled = False
overlength_enabled = False
fuel_levy = 0
uprate = 0
```

**Próximo paso**

Buscar en el workbook generado dónde aparece `162.22`, `828.03`, `665.81` o una fórmula especial en `BrokerTotals` / `SettingFlags` / `RATES` para TEAMTAS.

No aplicar un parche incompleto solo con `/1000`, porque dejaría Django en `665.81` y seguiría fallando contra Excel `828.03`.
