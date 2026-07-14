# Troubleshooting

## relation "clients_client" does not exist

This error means the PostgreSQL database was started without Django migrations for the project apps.

Fix:

```bash
docker compose down -v
docker compose build --no-cache
docker compose up
```

If you do not want to remove the database volume, run:

```bash
docker compose exec web python manage.py migrate --noinput
```

The project now includes initial migrations for all custom apps.

## TEAMEX does not match Excel while STEA, COCHRN, and KTI match

Symptom example:

- Excel shows `TEAMEX ROAD` around `$216.76`.
- The application shows `TEAMEX ROAD` around `$197.29`.
- `STEA`, `COCHRN`, and `KTI` match Excel.

Cause:

The issue is not the fuel table if the other carriers match. The previous application logic used a single global weight-break function for all carriers. Excel uses carrier-specific formulas in `BrokerTotals!AI:AO`.

For the Blair Athol test case with SKU 20772 quantity 5 and SKU 20985 quantity 5, the chargeable weight is 2075 kg. Excel resolves `TEAMEX ROAD` to `WeightBrk = 3`; the old global function resolved it to `WeightBrk = 4`.

Fix included in this version:

- `TEAMEX` now uses the `BrokerTotals` TEAMEX break logic only for `TEAMEX`.
- `TFMX`, `TEAMTAS`, `MACHIPE`, and `MIPEC` have separate selectors.
- Carriers without a break formula, such as `STEA`, `COCHRN`, and `KTI`, use blank `WeightBrk`.

After deploying the code change, rebuild/restart the web container:

```bash
docker compose up -d --build web
```

Reimporting the Excel workbook is not required for this specific code fix, as long as the current `RATES` data is already imported correctly.
