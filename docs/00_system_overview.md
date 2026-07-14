# 00 - System Overview

## Propósito

Migrar la calculadora STH / Steadfast Freight Calculator desde Excel a Django/PostgreSQL manteniendo equivalencia funcional verificable.

El objetivo no es reescribir la lógica de memoria. El objetivo es construir una plataforma web cuya salida pueda comprobarse contra Excel cuando sea necesario.

## Fuente de verdad

La fuente de verdad funcional es el workbook:

```text
V2026.R2_Unlocked_STH_Freight_Calculator.xlsx
```

La hoja principal de validación visual es:

```text
Calculator
```

Los outputs visibles que se comparan son:

| Excel | Uso |
|---|---|
| `Calculator!O6:O9` | Carrier/rank visible |
| `Calculator!P6:P9` | Service visible |
| `Calculator!Q6:Q9` | Estimate ex GST visible |
| `Calculator!J23` | Total weight visible |
| `Calculator!J24` | Total cubic visible |

## Hojas relevantes del Excel

| Hoja | Rol |
|---|---|
| `Calculator` | Input visible y resultados visibles finales |
| `CalcLines` | Consolidación interna, validaciones y cubic/peso de rating |
| `BrokerTotals` | Motor de cálculo por carrier/service |
| `FuelSurcharge` | Configuración carrier/service, fuel, flags y estados |
| `SUBURBS` | Suburb/state/postcode |
| `SKUs` | Productos, dimensiones, peso, cubic y freight type |
| `ZONES` | Mapeo carrier/service hacia zone/subzone/area |
| `RATES` | Tabla de tarifas |
| `SettingFlags` | Flags, tailgate, listas y textos auxiliares |

## Límite importante

`CalcLines` puede usarse para diagnóstico interno, pero **no reemplaza** a `Calculator` como expected output visual.

Ejemplo confirmado:

```text
Calculator!J24 = cubic visible
CalcLines!P29 = rating cubic, incluye pallet cubic
```

Por eso la batería visual compara contra `Calculator!J24` y descuenta el pallet cubic cuando toma datos internos de Django.

## Arquitectura Django

Aplicaciones principales:

- `apps.clients`
- `apps.carriers`
- `apps.locations`
- `apps.products`
- `apps.rates`
- `apps.freight`
- `apps.imports`
- `apps.audit`

Servicios clave:

- `apps.freight.services.calculator.FreightCalculatorService`
- `apps.freight.services.consolidator.consolidate_lines`
- `apps.freight.management.commands.validate_excel_battery`
- `tools/excel/generate_excel_expected_outputs.py`

## Principio de desarrollo

Todo cambio de cálculo debe tener evidencia:

1. caso Excel;
2. resultado esperado visible;
3. resultado Django;
4. diferencia;
5. diagnóstico;
6. corrección;
7. rerun de batería.
