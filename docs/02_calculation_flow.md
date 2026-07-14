# Freight Calculation Flow

1. Receive request.
2. Resolve `suburb + state` to postcode, equivalent to `Calculator!E7`.
3. Build freight lines from SKU mode or manual mode.
4. Consolidate totals like `CalcLines`:
   - total quantity
   - pallets
   - cartons
   - total weight
   - total cubic
5. Apply validation equivalent to `CalcLines!D3:L3`.
6. Iterate over configured carrier/service rows.
7. Resolve zone using `ZONES` equivalent.
8. Calculate chargeable weight, equivalent to `BrokerTotals!AF`. Most carriers use kg: `max(actual weight, cubic * cubic conversion)`. `TEAMTAS GENERAL` uses whole tonne/cubic units: `ROUNDUP(MAX(CalcLines!P29 * cubic_conversion, CalcLines!O29 / 1000), 0)`.
9. Resolve the `WeightBrk` value using the carrier-specific formulas from `BrokerTotals!AI:AO`.
10. Resolve rate using `RATES` equivalent and the Excel-like key components: carrier, service, zone, subzone, area, `WeightBrk`, customer, and freight type.
11. Calculate base freight.
12. Calculate tailgate or hand unload.
13. Calculate fuel surcharge.
14. Calculate final estimate ex GST.
15. Sort results from cheapest to most expensive.

## Carrier-specific WeightBrk logic

Excel does not use one global weight-break rule for every carrier. `BrokerTotals` defines the break result per carrier row in columns `AI:AO`, and the result is consumed in the rate lookup key.

Implemented carrier-specific selectors:

| Carrier | Service | Excel source | Implemented behavior |
|---|---|---|---|
| `TEAMEX` | `ROAD`, `GENERAL` | `BrokerTotals` rows 13 and 19 | `<751 = 1`, `>751.001 and <1501 = 2`, `>1501.001 and <3001 = 3`, `>3001.001 and <5001 = 4`, `>5000.001 = 5` |
| `TFMX` | `ROAD` | `BrokerTotals` row 15 | `<251 = 1`, `>251.001 and <751 = 2`, `>751.001 and <1501 = 3`, `>1501.001 and <3001 = 4`, `>3001.001 and <5000 = 5`, `>5000.001 = 6` |
| `TEAMTAS` | `GENERAL` | `BrokerTotals` row 20 | `<7.99 = 1`, `>=8 and <12.99 = 2`, `>=13 and <15.99 = 3`, `>=16 and <17.99 = 3`, `>=18 = 5` |
| `MACHIPE` / `MIPEC` | `ROAD` | `BrokerTotals` rows 17 and 21 | `>30 = 2`; otherwise blank |
| Other carriers | Any | no active `BrokerTotals` break formula found for the current rows | blank `WeightBrk` |

This correction fixes the observed TEAMEX mismatch for Blair Athol / SA 5084 with SKU 20772 quantity 5 and SKU 20985 quantity 5. The shipment chargeable weight is 2075 kg; Excel selects TEAMEX break `3`, while the previous global function selected break `4`.

## TEAMTAS GENERAL special formula

`TEAMTAS GENERAL` does not use the generic `per_kg * kg` calculation. Excel `BrokerTotals` row 20 uses a tonne/cubic-unit formula:

1. `AG20 = CalcLines!P29 * cubic_conversion`
2. `AH20 = CalcLines!O29 / 1000`
3. `AF20 = ROUNDUP(MAX(AG20, AH20), 0)`
4. `H20 = Basic * AG20`
5. `L20 = ROUNDUP(MAX(Minimum, H20 + Subsequent + Rate * AF20), 2)`
6. `AW20 = (pallet_count * 2) + (visible_cubic * 0.6)`
7. Final estimate includes `AW20` before the final display amount.

This was confirmed with random case `RANDOM_004`: `WEEGENA TAS 7304`, SKU `BRH4443`, qty `2`. Excel expected `TEAMTAS GENERAL = 828.03`; the old Django generic formula returned `663983.07` because it multiplied `186.25 * 3565 kg`.

## Regression warning

`BrokerTotals` contains complex carrier-specific formulas. Each carrier-specific branch must be locked against Excel regression cases before production use.
