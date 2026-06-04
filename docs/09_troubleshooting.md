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
