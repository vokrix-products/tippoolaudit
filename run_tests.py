from processor import VALID_STATUSES, process_file


def test_process_file_csv():
    test_bytes = (
        b"employee_name,business_date,tip_amount,location_name\n"
        b"Jane Doe,2025-01-03,120.00,Main Diner"
    )

    results = process_file(test_bytes)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Jane Doe"
    assert results[0]["status"] == "valid:good"
    assert results[0]["status"] in VALID_STATUSES
    assert results[0]["due_date"] == "2025-01-03"
    assert isinstance(results[0]["details"], dict)
    assert "tip_amount" in results[0]["details"]
    assert "due_date" not in results[0]["details"]


def test_process_file_empty_bytes():
    results = process_file(b"")

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["status"] == "missing:critical"


def test_process_file_unknown_text():
    results = process_file(b"Plain text with no delimiters")

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["status"] == "needs_review:warning"


if __name__ == "__main__":
    test_process_file_csv()
    test_process_file_empty_bytes()
    test_process_file_unknown_text()
    print("run_tests passed")
