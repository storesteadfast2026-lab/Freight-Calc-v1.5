# 01 - Excel to Web Mapping

| Excel | Django / CSV equivalent |
|---|---|
| `Calculator!C7` | `suburb` / `request.suburb` |
| `Calculator!D7` | `state` / `request.state` |
| `Calculator!E7` | `postcode` / `request.postcode` |
| `Calculator!E11` | `tailgate` |
| `Calculator!C13` | `preselect_sku_mode` |
| `Calculator!C15:C22` | `sku_1..sku_8` |
| `Calculator!D15:D22` | `qty_1..qty_8` |
| `Calculator!O6:O9` | expected carrier ranks |
| `Calculator!P6:P9` | expected services |
| `Calculator!Q6:Q9` | expected estimate ex GST |
| `Calculator!J23` | expected total weight |
| `Calculator!J24` | expected visible total cubic |
| `SKUs` | `Product` model |
| `SUBURBS` | `Suburb` model |
| `ZONES` | `FreightZone` model |
| `RATES` | `FreightRate` model |
| `FuelSurcharge` | `ClientCarrierConfig` model |
| `SettingFlags!C33:H52` | `CarrierTailgateCharge` model |
| `BrokerTotals!AF` | chargeable weight calculation |
| `BrokerTotals!AI:AO` | carrier-specific `WeightBrk` selector |
| `BrokerTotals!Z` | `FreightResult.estimate_ex_gst` |

## Postcode

El generador Excel debe escribir explícitamente:

```text
Calculator!E7 = postcode
```

Bug ya encontrado: el script escribía suburb y state, pero no postcode. Excel quedaba usando un postcode viejo (`3023`) para múltiples casos random. Eso invalidaba comparaciones de carrier/precio. La corrección es escribir `args.postcode_cell` antes de refrescar/calcular Excel.

## Tailgate

Excel no asigna un tailgate único por producto. `Calculator!E15:E22` copia el flag global desde `Calculator!E11`. El costo se calcula a nivel shipment/carrier usando total pallets.

## Peso y cubic

Regla de comparación visual:

```text
expected_weight = Calculator!J23
expected_cubic  = Calculator!J24
```

Regla interna de rating:

```text
rating_cubic = product_cubic + pallets × 0.02
```

Para comparar Django contra `Calculator!J24`:

```text
visible_cubic = rating_cubic - pallets × 0.02
```

## Resolución de zona

Django debe resolver zona priorizando:

```text
suburb + state
```

antes que:

```text
postcode
```

Motivo: un postcode puede aparecer en muchos suburbs. Si se usa el primer match por postcode, Django puede tomar una zona que pertenece a otro suburb.

Casos confirmados:

- `YARROWYCK NSW 2358`: Excel usa suburb real y zona `BNE5`; Django tomaba por postcode otro suburb y zona `BNE4`.
- `BALL BAY QLD 4740`: Excel usa suburb real y zona `MYK2`; Django tomaba por postcode otro suburb y zona `MYK1`.

## WeightBrk / rate lookup

Django no debe usar una sola fórmula global de `WeightBrk`. Excel calcula el break por carrier/service en `BrokerTotals!AI:AO`.

| Carrier | Service | Selector |
|---|---|---|
| `TEAMEX` | `ROAD`, `GENERAL` | selector propio TEAMEX |
| `TFMX` | `ROAD` | selector propio TFMX |
| `TEAMTAS` | `GENERAL` | selector propio TEAMTAS |
| `MACHIPE`, `MIPEC` | `ROAD` | selector propio |
| Otros | Any | blank `WeightBrk` si Excel no tiene fórmula activa |
