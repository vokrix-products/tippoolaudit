import json

from processor import process_file


def main() -> int:
    test_bytes = (
        b"employee_name,business_date,tip_amount,location_name,server_name\n"
        b"Jane Doe,2025-01-03,120.00,Main Diner,Jane Doe"
    )

    results = process_file(test_bytes)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Jane Doe"
    assert results[0]["status"] == "valid:good"
    assert results[0]["details"]["tip_amount"] == "120.00"

    print(json.dumps(results, indent=2, default=str))
    print("run_demo passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
