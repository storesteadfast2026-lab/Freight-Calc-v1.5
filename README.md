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
