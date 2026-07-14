# 13 - AI / Spec Driven Development Workflow

## Objetivo

Mantener el proyecto entendible para humanos y para asistentes de IA. Cada cambio debe dejar una huella verificable en documentación, tests y reportes.

## Estructura recomendada en GitHub

```text
README.md
.env.example
docker-compose.yml
requirements.txt
app/
tools/
docs/
  00_system_overview.md
  01_excel_to_web_mapping.md
  02_calculation_flow.md
  03_data_model.md
  04_imports.md
  05_authentication_integration.md
  06_multi_client_strategy.md
  07_testing_strategy.md
  08_windows_docker_deployment.md
  09_troubleshooting.md
  10_excel_django_validation_strategy.md
  11_validation_runbook.md
  12_validation_findings_log.md
  13_ai_spec_driven_workflow.md
  adr/
    0001_excel_source_of_truth.md
    0002_random_current_fixture.md
reports/
```

## Por qué esta estructura

- `README.md`: entrada rápida del proyecto.
- `docs/00..09`: documentación base y arquitectura.
- `docs/10..12`: validación Excel/Django, comandos y hallazgos.
- `docs/13`: reglas de trabajo con IA y spec-driven development.
- `docs/adr`: decisiones técnicas permanentes.
- `reports`: evidencia generada, no lógica.

## Regla para trabajar con IA

Antes de pedir un cambio de código, entregar o apuntar a:

1. caso input;
2. expected Excel;
3. actual Django;
4. reporte FAIL;
5. diagnóstico si existe;
6. archivo de código sospechoso;
7. decisión esperada.

## Plantilla para un bug de cálculo

```markdown
## BUG - <carrier/service/caso>

### Caso
- case_id:
- suburb/state/postcode:
- tailgate:
- SKUs/qty:

### Excel expected
- carrier:
- service:
- estimate:
- weight:
- cubic visible:

### Django actual
- carrier:
- service:
- estimate:
- details:

### Diferencia

### Hipótesis

### Evidencia

### Fix aplicado

### Resultado batería
```

## Definition of Done documental

Un cambio no está terminado si solo cambia código. Debe actualizar:

- test o batería correspondiente;
- `docs/12_validation_findings_log.md` si fue bug;
- `docs/11_validation_runbook.md` si cambió el comando;
- `docs/02_calculation_flow.md` si cambió la lógica de cálculo;
- ADR si fue una decisión de arquitectura o regla permanente.

## Reglas para `random_current`

- Usar una carpeta fija para la prueba random actual.
- No crear `random_5`, `random_10`, `random_30` para trabajo diario.
- Guardar evidencia histórica solo cuando la corrida aporta valor:

```text
reports/random_current/sth_excel_random_comparison_report_OK.csv
reports/random_current/manifest_random_current_OK.json
```

## Reglas para Markdown

- Preferir documentos cortos y enfocados.
- No esconder decisiones importantes en chats.
- No mezclar runbook, arquitectura y findings en un solo archivo grande.
- Los comandos deben ser copiables en PowerShell.
- Los hallazgos deben incluir números concretos de Excel y Django.
