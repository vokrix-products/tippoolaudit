# TipPoolAudit

TipPoolAudit is a tip-pool and payroll-audit product for restaurants and hospitality groups. It ingests POS exports, timesheets, tip-pool policy documents, and pay-period reports, then flags every record that is missing a rule version, missing approval or signature, has a manager in the pool, misclassifies service charges, contains employee fees, or requires pay-card / vendor-wallet action before payroll can be locked.

## Archetype

Audit/monitoring product. The unit the buyer tracks is an **employee / server record per pay period** — not the document itself. Each extracted record is one employee line item with a status the operator must clear before payroll sign-off.

## Backend files

- `processor.py` — core processing module. Exposes `process_file(file_bytes: bytes) -> list[dict]`. Handles PDF, then Excel, then CSV/plain text. Normalizes POS and timesheet tabular data, detects source type, extracts the employee title, sets status and due date, and only uses DeepSeek for unstructured text.
- `run_demo.py` — hardcoded CSV demo, asserts output shape, exits 0 in under 10 seconds.
- `run_tests.py` — plain-python smoke tests (CSV parsing, empty bytes, unstructured fallback).
- `requirements.txt` — `openai`, `requests`, `pdfplumber`, `openpyxl`, `python-dateutil`.

## What the poller expects as input

- **Input:** raw file bytes of a POS export, timesheet, tip-pool policy, or pay-period report (`.pdf`, `.xlsx`/`.xls`, `.csv`, `.txt`).
- **Call:** `process_file(file_bytes)` — synchronous, no args, no network unless the input is unstructured text.
- **Output:** `list[dict]`, one dict per employee line item:
  - `title` (str) — employee or server name, never the document type.
  - `status` (str) — one of the valid status codes, e.g. `valid:good`, `missing:critical`, `needs_review:warning`, `unmapped_employee:critical`, `manager_in_pool:critical`, `missing_rule_version:critical`, `missing_approval:critical`, `missing_signature:critical`, `approval_pending:warning`, `locked:good`.
  - `details` (dict) — all fields found for that record (`employee_id`, `employee_name`, `business_date`, `tip_amount`, sales amounts, `role`, `shift_id`, `clock_in`, `clock_out`, `hours_worked`, etc.).
  - `due_date` (str|null) — ISO-8601 date, preferring `pay_period_end`, then `business_date`, then `shift_date`.
- **Failure mode:** unprocessable input still returns a one-element list with `status: missing:critical` and the reason in `details.error` — it never raises and never returns an empty list.

Dashboard: https://tippoolaudit.vokrix.co
Vercel: tippoolaudit
