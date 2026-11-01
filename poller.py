import os
import time
import json
import requests
import processor

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PRODUCT_ID = os.environ["PRODUCT_ID"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

REST_URL = f"{SUPABASE_URL}/rest/v1"
SB_HEADERS = {
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "apikey": SUPABASE_SERVICE_KEY,
}

def download_file(bucket, file_path):
    if file_path.startswith(bucket + "/"):
        file_path = file_path[len(bucket) + 1:]
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "apikey": SUPABASE_SERVICE_KEY})
    resp.raise_for_status()
    return resp.content

def notify(customer_id, title, body, type):
    try:
        resp = requests.post(
            f"{REST_URL}/notifications",
            headers={**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={
                "product_id": PRODUCT_ID,
                "customer_id": customer_id,
                "title": title,
                "body": body,
                "type": type,
                "read": False,
            },
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"Notification failed: {e}")

def update_job(job_id, status, output_file_path=None, result_summary=None):
    payload = {
        "status": status,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if output_file_path is not None:
        payload["output_file_path"] = output_file_path
    if result_summary is not None:
        payload["result_summary"] = result_summary
    resp = requests.patch(
        f"{REST_URL}/jobs",
        headers={**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
        params={"id": f"eq.{job_id}"},
        json=payload,
    )
    resp.raise_for_status()

def process_job(job):
    job_id = job["id"]
    customer_id = job["customer_id"]
    input_file_path = job["input_file_path"]
    try:
        file_bytes = download_file("uploads", input_file_path)
        result = processor.process_file(file_bytes)
        if isinstance(result, dict):
            records = result.get("records", [])
            if not isinstance(records, list):
                records = []
        elif isinstance(result, list):
            records = result
        else:
            records = []

        for r in records:
            title = r.get("title", "Untitled")
            status = r.get("status", "needs_review:warning")
            details = r.get("details", {})
            due_date = r.get("due_date")
            # Ensure details is JSON serializable
            try:
                json.dumps(details)
            except TypeError:
                details = json.loads(json.dumps(details, default=str))
            insert_resp = requests.post(
                f"{REST_URL}/records",
                headers={**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"},
                json={
                    "product_id": PRODUCT_ID,
                    "customer_id": customer_id,
                    "title": title,
                    "status": status,
                    "details": details,
                    "source_file_path": input_file_path,
                    "due_date": due_date,
                },
            )
            insert_resp.raise_for_status()

        output_filename = f"{job_id}.json"
        result_json = json.dumps({"success": True, "records": records}, default=str)
        upload_resp = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/results/{output_filename}",
            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "apikey": SUPABASE_SERVICE_KEY, "Content-Type": "application/json"},
            data=result_json,
        )
        upload_resp.raise_for_status()
        output_path = f"results/{output_filename}"

        update_job(job_id, "completed", output_file_path=output_path, result_summary=f"Processed {len(records)} records")
        notify(customer_id, "Processing complete", "Your upload has been processed successfully.", "success")
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        try:
            update_job(job_id, "failed", result_summary=str(e))
            notify(customer_id, "Processing failed", "There was an error processing your upload.", "error")
        except Exception as update_error:
            print(f"Failed to update job {job_id}: {update_error}")

def poll():
    while True:
        try:
            resp = requests.get(
                f"{REST_URL}/jobs",
                headers=SB_HEADERS,
                params={
                    "status": "eq.pending",
                    "job_type": "eq.process_upload",
                    "product_id": f"eq.{PRODUCT_ID}",
                    "select": "*",
                },
            )
            resp.raise_for_status()
            jobs = resp.json()
            for job in jobs:
                process_job(job)
        except Exception as e:
            print(f"Polling error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    print("Poller started")
    poll()
