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
8. Resolve rate using `RATES` equivalent.
9. Calculate chargeable weight: `max(actual weight, cubic * cubic conversion)`.
10. Calculate base freight.
11. Calculate tailgate or hand unload.
12. Calculate fuel surcharge.
13. Calculate final estimate ex GST.
14. Sort results from cheapest to most expensive.

## Regression warning

`BrokerTotals` contains complex carrier-specific formulas. The scaffold includes the core calculation path and must be locked against Excel regression cases before production use.
