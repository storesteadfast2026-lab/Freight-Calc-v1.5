# Freight Calculator - Backup, schema versionado y recuperación

## Objetivo

Este paquete separa tres cosas que no deben confundirse:

1. **Código**: Git / Git bundle.
2. **Estructura de PostgreSQL**: `database/schema.sql`, versionable junto al código.
3. **Datos reales**: `.dump` PostgreSQL fuera del repositorio.

Ningún script de este paquete ejecuta `git push`.

---

## Archivos

### `01_Full_Backup.ps1`

Crea un recovery point completo fuera del repositorio:

- PostgreSQL `.dump` formato custom.
- PostgreSQL globals/roles.
- PostgreSQL schema-only.
- inventario básico de la BD.
- Git bundle con ramas y tags locales.
- comparación de la rama local contra GitHub en modo **solo lectura**.
- SHA256.
- manifest que relaciona commit Git y backup PostgreSQL.
- copia secundaria opcional.

Uso:

```powershell
.\01_Full_Backup.ps1
```

Con una segunda copia independiente:

```powershell
.\01_Full_Backup.ps1 -SecondaryCopyPath "E:\FreightCalc_Backups"
```

Salida típica:

```text
C:\Docker-Backups\Freight-Calc\
└── backup_YYYYMMDD_HHMMSS\
    ├── BACKUP_MANIFEST.txt
    ├── SHA256SUMS.txt
    ├── postgresql\
    │   ├── freight_platform_....dump
    │   ├── freight_platform_globals_....sql
    │   ├── freight_platform_schema_....sql
    │   └── database_inventory_....txt
    ├── git\
    │   └── Freight-Calc-v1.5_....bundle
    └── logs\
        └── 01_Full_Backup_....log
```

---

### `02_Test_PostgreSQL_Restore.ps1`

Prueba un dump sin tocar producción:

1. valida el catálogo del dump;
2. crea una base temporal;
3. restaura;
4. valida tablas/conteos;
5. vuelve a generar y leer un dump;
6. elimina la DB temporal salvo que se use `-KeepTestDatabase`.

Uso:

```powershell
.\02_Test_PostgreSQL_Restore.ps1 `
  -DumpPath "C:\Docker-Backups\Freight-Calc\backup_...\postgresql\freight_platform_....dump"
```

---

### `03_Restore_PostgreSQL_Production.ps1`

Único script que modifica la base operacional.

Protecciones:

- confirmación escrita exacta;
- valida primero el dump;
- crea backup de emergencia de la producción actual;
- restaura primero en una DB aislada;
- valida la DB restaurada;
- detiene Django;
- conserva la DB anterior mediante rename;
- promueve la nueva DB;
- reinicia Django;
- ejecuta `manage.py check --database default`;
- intenta rollback automático del swap si el check posterior falla.

Uso:

```powershell
.\03_Restore_PostgreSQL_Production.ps1 `
  -DumpPath "C:\...\freight_platform_....dump"
```

Confirmación requerida:

```text
RESTORE freight_platform
```

No usar este script para pruebas. Para pruebas usar `02_Test_PostgreSQL_Restore.ps1`.

---

### `04_Update_Database_Schema.ps1`

Genera la estructura canónica que debe vivir en Git:

```text
database\schema.sql
```

El archivo contiene estructura, no datos.

El script:

- ejecuta `pg_dump --schema-only`;
- elimina owner/privileges/tablespaces para mejorar portabilidad;
- reconstruye una DB temporal desde el SQL para comprobar que funciona;
- reemplaza `database/schema.sql`;
- muestra `git status` y `git diff`;
- **no hace `git add`, commit ni push**.

Uso:

```powershell
.\04_Update_Database_Schema.ps1
```

Flujo recomendado al versionar:

```text
cambio de código/modelos
        ↓
migrations/tests
        ↓
04_Update_Database_Schema.ps1
        ↓
revisar git diff
        ↓
commit local incluyendo database/schema.sql
        ↓
GitHub solamente si el usuario lo autoriza expresamente
```

Django migrations siguen siendo el mecanismo principal de evolución. `schema.sql` es la fotografía resultante de PostgreSQL para auditoría y reconstrucción.

---

### `05_Install_Daily_Backup_Task.ps1`

Instala una tarea de Windows Task Scheduler para ejecutar automáticamente `01_Full_Backup.ps1`.

Por defecto:

```text
19:00 todos los días
```

Uso:

```powershell
.\05_Install_Daily_Backup_Task.ps1
```

Otro horario:

```powershell
.\05_Install_Daily_Backup_Task.ps1 -DailyTime "18:30"
```

Con segunda copia:

```powershell
.\05_Install_Daily_Backup_Task.ps1 `
  -DailyTime "19:00" `
  -SecondaryCopyPath "E:\FreightCalc_Backups"
```

### Limitación local importante

El proyecto usa Docker Desktop en Windows. La tarea queda asociada al usuario de Windows actual. Docker debe estar disponible cuando se ejecute.

Cuando Freight Calculator se despliegue posteriormente en un servidor Linux, el equivalente recomendado será systemd timer/cron o el sistema de backup de la infraestructura, no Windows Task Scheduler.

---

# Política recomendada

## Diario

`01_Full_Backup.ps1` automático.

## Antes de un cambio de datos importante

Ejecutar manualmente `01_Full_Backup.ps1`.

Ejemplos:

- antes de activar Products;
- antes de activar Zones;
- antes de una migración significativa.

## Al versionar código

Ejecutar:

```powershell
.\04_Update_Database_Schema.ps1
```

Revisar cambios antes del commit.

## Periódicamente

Probar un backup reciente con:

```powershell
.\02_Test_PostgreSQL_Restore.ps1 -DumpPath "..."
```

Un backup no debe considerarse plenamente probado hasta demostrar que puede restaurarse.

## Restore producción

Solamente cuando exista una necesidad real y después de seleccionar/verificar el recovery point.

---

# GitHub

Todos los scripts están diseñados bajo esta regla:

> GitHub nunca se modifica automáticamente.

`01_Full_Backup.ps1` usa `git ls-remote` únicamente para comparación.

No contiene:

- `git push`
- `git push --force`
- eliminación de ramas remotas
- creación/eliminación de tags remotos

La actualización de GitHub debe ser un procedimiento independiente y requerir autorización explícita.

---

# 3-2-1

Para protección real:

- mantener la base operacional;
- mantener el recovery point local;
- mantener una segunda copia en almacenamiento distinto;
- idealmente conservar una copia off-site.

`-SecondaryCopyPath` ayuda con la segunda copia, pero no sustituye una política off-site.

---

# Qué NO cubre todavía

Este paquete no respalda automáticamente:

- `uploaded_data`;
- `media`;
- archivos FTP fuera de PostgreSQL;
- secretos externos;
- imágenes Docker.

Si alguno de estos elementos es necesario para reconstrucción total del sistema, debe incorporarse en una política separada.
