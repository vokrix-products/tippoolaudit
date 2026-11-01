import os
import io
import csv
import json
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
import pdfplumber
import openpyxl


VALID_STATUSES = {
    "missing:critical",
    "expired:critical",
    "valid:good",
    "flagged:critical",
    "needs_review:warning",
    "unmapped_employee:critical",
    "placeholder_employee:warning",
    "duplicate_pool:critical",
    "missing_rule_version:critical",
    "missing_approval:critical",
    "missing_signature:critical",
    "rule_conflict:critical",
    "manager_in_pool:critical",
    "service_charge_misclassified:critical",
    "catering_unpooled:warning",
    "employee_fee_detected:critical",
    "pay_card_required:critical",
    "vendor_wallet_risk:critical",
    "pos_integration_required:critical",
    "overtime_impact:warning",
    "fica_tip_credit_unsupported:warning",
    "quickbooks_desktop_mapping_missing:warning",
    "approval_pending:warning",
    "signed:good",
    "locked:good",
}

POS_SOURCE_MARKERS = {
    "tip_amount",
    "net_sales",
    "gross_sales",
    "food_sales",
    "alcohol_sales",
    "beverage_sales",
    "check_id",
    "ticket_id",
    "server_name",
    "service_charge_amount",
    "auto_gratuity",
    "cash_tip",
    "card_tip",
    "business_date",
}

TIMESHEET_SOURCE_MARKERS = {
    "clock_in",
    "clock_out",
    "hours_worked",
    "regular_hours",
    "overtime_hours",
    "double_time_hours",
    "shift_date",
    "break_minutes",
    "unpaid_break_minutes",
}

TITLE_FIELDS = (
    "employee_name",
    "server_name",
    "employee_id",
    "location_name",
)

DATE_FIELDS = (
    "pay_period_end",
    "business_date",
    "shift_date",
    "pay_period_start",
)


def _parse_iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan", ""}:
        return None

    try:
        return date_parser.parse(text, fuzzy=True).date().isoformat()
    except Exception:
        return None


def _parse_delimited_text(text: str) -> Optional[List[Dict[str, Any]]]:
    if not text:
        return None

    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except Exception:
        return None

    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        rows = [row for row in reader if row]
        if rows:
            return rows
    except Exception:
        return None

    return None


def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
    if not rows:
        return []

    raw_headers = list(rows[0])
    headers: List[str] = []
    seen: Dict[str, int] = {}

    for i, header in enumerate(raw_headers):
        base = str(header).strip() if header is not None else f"column_{i}"
        base = base or f"column_{i}"

        count = seen.get(base, 0)
        seen[base] = count + 1
        headers.append(base if count == 0 else f"{base}_{count}")

    result: List[Dict[str, Any]] = []

    for row in rows[1:]:
        if all(v is None or str(v).strip() == "" for v in row):
            continue

        row_dict: Dict[str, Any] = {}
        for i, header in enumerate(headers):
            value = row[i] if i < len(row) else None
            row_dict[header] = "" if value is None else str(value)

        result.append(row_dict)

    return result


def _source_type(headers: set) -> str:
    lowered = {str(h).lower().strip() for h in headers}

    if lowered & TIMESHEET_SOURCE_MARKERS:
        return "timesheet"

    if lowered & POS_SOURCE_MARKERS:
        return "pos"

    return "unknown"


def _pick_title(row: Dict[str, Any]) -> str:
    for field in TITLE_FIELDS:
        value = row.get(field)
        if value and str(value).strip():
            return str(value).strip()

    return "Unknown employee"


def _status_for_row(row: Dict[str, Any], source_type: str) -> str:
    employee_name = (row.get("employee_name") or row.get("server_name") or "").strip()
    employee_id = (row.get("employee_id") or "").strip()

    if source_type == "timesheet":
        if employee_name and row.get("shift_date"):
            return "valid:good"
        if not employee_name and not employee_id:
            return "unmapped_employee:critical"
        return "missing:critical"

    if source_type == "pos":
        if (
            employee_name
            and (row.get("business_date") or row.get("pay_period_end"))
            and row.get("tip_amount")
        ):
            return "valid:good"
        if not employee_name and not employee_id:
            return "unmapped_employee:critical"
        if not employee_name or not (row.get("business_date") or row.get("pay_period_end")):
            return "missing:critical"
        return "needs_review:warning"

    if employee_name or employee_id:
        return "needs_review:warning"

    return "missing:critical"


def _due_date_from_row(row: Dict[str, Any]) -> Optional[str]:
    for field in DATE_FIELDS:
        value = row.get(field)
        parsed = _parse_iso_date(value)
        if parsed:
            return parsed

    return None


def _records_from_struct(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for row in rows:
        cleaned = {
            str(k).strip(): v
            for k, v in row.items()
            if v is not None and str(v).strip() != ""
        }

        source_type = _source_type(set(cleaned.keys()))
        title = _pick_title(cleaned)
        status = _status_for_row(cleaned, source_type)
        due_date = _due_date_from_row(cleaned)
        details = {str(k): v for k, v in row.items()}

        records.append(
            {
                "title": title,
                "status": status,
                "details": details,
                "due_date": due_date,
            }
        )

    return records


def _extract_with_llm(text: str) -> List[Dict[str, Any]]:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
    except Exception:
        return []

    prompt = """
You are a restaurant tip pool audit extraction engine.
Extract all line-item records from the document into a JSON array.

Each record MUST be an object with exactly these top-level keys:
- title: string. The primary entity the buyer tracks. For TipPoolAudit this is the employee name or server name. NEVER use document type/category.
- status: string. MUST be one of these exact values:
missing:critical,expired:critical,valid:good,flagged:critical,needs_review:warning,unmapped_employee:critical,placeholder_employee:warning,duplicate_pool:critical,missing_rule_version:critical,missing_approval:critical,missing_signature:critical,rule_conflict:critical,manager_in_pool:critical,service_charge_misclassified:critical,catering_unpooled:warning,employee_fee_detected:critical,pay_card_required:critical,vendor_wallet_risk:critical,pos_integration_required:critical,overtime_impact:warning,fica_tip_credit_unsupported:warning,quickbooks_desktop_mapping_missing:warning,approval_pending:warning,signed:good,locked:good
- details: object. Contains all document fields found for that record, such as location_id, location_name, employee_id, employee_name, business_date, tip_amount, sales amounts, role, shift_id, clock_in, clock_out, hours_worked, etc. Use null for unknown fields, but include all fields relevant to TipPoolAudit.
- due_date: ISO-8601 date string or null. Prefer pay_period_end, then business_date, then shift_date.

Return ONLY the JSON array, no markdown.
""".strip()

    try:
        completion = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:12000]},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            return []

        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]

        parsed = json.loads(content)

        if isinstance(parsed, dict):
            parsed = parsed.get("records", parsed.get("data", []))

        if not isinstance(parsed, list):
            return []

        return [item for item in parsed if isinstance(item, dict)]
    except Exception:
        return []


def _records_from_unstructured(text: str) -> List[Dict[str, Any]]:
    if os.environ.get("DEEPSEEK_API_KEY"):
        extracted = _extract_with_llm(text)

        if extracted:
            records: List[Dict[str, Any]] = []

            for item in extracted:
                if not isinstance(item, dict):
                    continue

                title = item.get("title") or "Unknown employee"
                status = (
                    item.get("status")
                    if item.get("status") in VALID_STATUSES
                    else "needs_review:warning"
                )
                details = (
                    item.get("details")
                    if isinstance(item.get("details"), dict)
                    else {"raw_text": text[:2000]}
                )
                due_date = (
                    item.get("due_date")
                    if isinstance(item.get("due_date"), str)
                    else None
                )

                records.append(
                    {
                        "title": title,
                        "status": status,
                        "details": details,
                        "due_date": due_date,
                    }
                )

            if records:
                return records

    return [
        {
            "title": "Unknown employee",
            "status": "needs_review:warning",
            "details": {"raw_text": text[:2000]},
            "due_date": None,
        }
    ]


def _unprocessable_reason(reason: str) -> List[Dict[str, Any]]:
    return [
        {
            "title": "Unknown employee",
            "status": "missing:critical",
            "details": {"error": reason},
            "due_date": None,
        }
    ]


def process_file(file_bytes: bytes) -> List[Dict[str, Any]]:
    if not isinstance(file_bytes, bytes):
        raise TypeError("file_bytes must be bytes")

    if not file_bytes:
        return _unprocessable_reason("Empty file")

    # 1. Try PDF first
    try:
        if file_bytes[:4] == b"%PDF":
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]

            text = "\n".join(page for page in pages if page.strip())

            if text.strip():
                structured = _parse_delimited_text(text)
                if structured:
                    return _records_from_struct(structured)
                return _records_from_unstructured(text)

            return _unprocessable_reason("PDF contained no extractable text")
    except Exception:
        pass

    # 2. Try Excel
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(file_bytes),
            data_only=True,
            read_only=True,
        )
        sheet = workbook.active
        rows = [row for row in sheet.iter_rows(values_only=True)]

        if rows:
            return _records_from_struct(_rows_to_dicts(rows))
    except Exception:
        pass

    # 3. Fallback to UTF-8 text/CSV
    try:
        text = file_bytes.decode("utf-8", errors="ignore")

        if text.strip():
            structured = _parse_delimited_text(text)
            if structured:
                return _records_from_struct(structured)
            return _records_from_unstructured(text)
    except Exception:
        pass

    return _unprocessable_reason("Could not parse file")
