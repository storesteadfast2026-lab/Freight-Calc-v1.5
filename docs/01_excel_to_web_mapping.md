# Excel to Web Mapping

| Excel | Django equivalent |
|---|---|
| `Calculator!C7` | request.to_suburb |
| `Calculator!D7` | request.to_state |
| `Calculator!E7` | resolved postcode from `Suburb` model |
| `Calculator!E11` | request.tailgate |
| `Calculator!C13` | request.preselect_sku |
| `Calculator!C15:D22` | selected product lines |
| `SKUs` | `Product` model |
| `SUBURBS` | `Suburb` model |
| `ZONES` | `FreightZone` model |
| `RATES` | `FreightRate` model |
| `FuelSurcharge` | `ClientCarrierConfig` model |
| `SettingFlags!C33:H52` | `CarrierTailgateCharge` model |
| `BrokerTotals!Z` | `FreightResult.estimate_ex_gst` |

## Tailgate

Excel does not assign a unique tailgate value per product. `Calculator!E15:E22` copies the global tailgate flag from `E11`. The cost is calculated at shipment/carrier level using total pallets.
