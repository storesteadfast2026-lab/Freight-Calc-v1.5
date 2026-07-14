# STH Freight Platform

Aplicación Django/PostgreSQL para migrar la lógica de la planilla `V2026.R2_Unlocked_STH_Freight_Calculator.xlsx` hacia una plataforma web multi-cliente.

## Estado

Este entregable es un scaffold funcional inicial, preparado para importar datos desde Excel, administrar clientes/productos/carriers/rates desde Django Admin y ejecutar el cálculo mediante servicios desacoplados.

## Ejecutar con Docker en Windows

```bash
copy .env.example .env
docker compose up --build
```

Luego abrir:

```text
http://localhost:8000/
http://localhost:8000/admin/
```

## Crear superusuario

```bash
docker compose exec web python manage.py createsuperuser
```

## Importar el Excel de STH

Coloca el archivo en `sample_data/V2026.R2_Unlocked_STH_Freight_Calculator.xlsx` o súbelo desde admin cuando se agregue la UI de carga.

```bash
docker compose exec web python manage.py import_sth_excel /app/sample_data/V2026.R2_Unlocked_STH_Freight_Calculator.xlsx --client STH
```

## Documentación

Ver carpeta `docs/`.

## Autocomplete data

English: The suburb and product autocomplete fields read from PostgreSQL. On a clean Docker volume, the container now imports the sample workbook automatically after migrations if no suburbs exist. If you already had an old database volume, run `docker compose down -v` once so the database is recreated and the import can run.

Español: Los campos de autocompletado de suburbios y productos leen datos desde PostgreSQL. En un volumen Docker limpio, el contenedor importa automáticamente la planilla de ejemplo después de las migraciones si no existen suburbios cargados. Si ya tenías un volumen anterior, ejecuta `docker compose down -v` una vez para recrear la base de datos y permitir la importación.
