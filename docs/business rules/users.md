# Business Rules - Users

Status: Approved (Version 1)

## Calculator Roles

- Customer User
- Internal User

## Django Admin

- Django Administrator

These are separate concepts. Calculator roles must never be mixed with Django administrative access.

## Customer User

- Belongs to exactly one client.
- Can create quotations.
- Can view all quotations belonging to the assigned client.
- Cannot view another client's quotations.

## Internal User

- Uses the calculator.
- Client scope is configured:
  - All clients
  - Selected clients
- Does not imply Django Admin access.

## Django Administrator

Administrative platform user.

Responsible for:
- Users
- Clients
- Products
- Rates
- Configuration

## Confirmed Rules

USR-001 Customer User can view all quotations for its client.
USR-002 Customer Admin is not included in V1.
USR-003 Internal User scope is configurable.
USR-004 Login by email.
USR-005 Invitation-based password creation.
USR-006 Only Customer User and Internal User exist in calculator V1.
