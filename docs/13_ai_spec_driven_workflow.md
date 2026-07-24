# AI Spec-Driven Workflow

## Purpose

This project is developed with AI assistance, but no AI-generated statement becomes a business rule merely because a draft labels it “Approved”, “Accepted” or “Confirmed”.

## Source-of-truth hierarchy

Use this order:

1. Explicitly approved files in `business_rules/`.
2. Accepted entries in `decisions/`.
3. Accepted ADRs in `docs/adr/`.
4. Current code and migrations.
5. Automated tests and runtime evidence.
6. Excel workbook and Excel-vs-Django reports for calculation behavior.
7. Other explanatory Markdown.

For calculation logic, Excel remains the functional source of truth. For web-only features such as users and permissions, approved business rules and decisions are the source of truth.

## Required statuses

New rules and decisions must use:

```text
CONFIRMED / ACCEPTED
PROPOSED
PENDING
REJECTED
```

Do not silently convert a proposal into an accepted requirement.

## Rules for AI-assisted changes

Before changing calculation logic:

1. Identify the Excel source sheet/cells or imported data.
2. Create or identify a failing Excel-vs-Django case.
3. Explain Django behavior and Excel behavior.
4. Patch the smallest reasonable code area.
5. Run the relevant battery with the matching baseline.
6. Update Markdown documentation.

Before changing web-only behavior such as users/access:

1. Update `business_rules/` with confirmed/proposed rules.
2. Record the decision in `decisions/` or a proposed ADR.
3. Inspect current models, middleware, views and permissions.
4. Identify security and migration effects.
5. Implement one phase at a time.
6. Add backend authorization tests before UI-only tests.
7. Update operational and troubleshooting documentation.

## Required explanation for each change

```text
File changed:
Reason:
Source evidence:
Behavior before:
Behavior after:
Validation command:
Validation result:
Docs updated:
```

## Documentation update policy

After meaningful changes, update the relevant files among:

- `business_rules/`;
- `decisions/`;
- `docs/02_calculation_flow.md`;
- `docs/04_imports.md`;
- `docs/05_authentication_integration.md`;
- `docs/07_testing_strategy.md`;
- `docs/09_troubleshooting.md`;
- `docs/11_validation_runbook.md`;
- `docs/12_validation_findings_log.md`;
- `docs/14_excel_django_traceability_matrix.md`;
- `docs/15_admin_configuration_dictionary.md`;
- `docs/adr/`.

## Review ZIP rule

Future AI review ZIPs must include:

```text
app/
tools/
docs/
business_rules/
decisions/
tests/
reports/ when requested
controlled reference files
runtime diagnostics
```

## Do not rely on chat memory only

Important project decisions must be stored in the repository so a future review can continue from the files without reconstructing prior conversations.
