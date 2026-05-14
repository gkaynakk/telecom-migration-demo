import pandas as pd
import random
import os
from faker import Faker
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient

fake = Faker()

# -----------------------------
# CONFIGURATION
# -----------------------------
NUM_CUSTOMERS = 10000
NUM_USAGE_RECORDS = 10000
NUM_BILLING_RECORDS = 3000

RUN_DATE = os.getenv("RUN_DATE") or datetime.utcnow().strftime("%Y-%m-%d")
RUN_DATE_DT = datetime.strptime(RUN_DATE, "%Y-%m-%d")

OUTPUT_DIR = f"./telecom_data/incremental/{RUN_DATE}"

AZURE_STORAGE_ACCOUNT = "telelcomhuaweidemo"
AZURE_CONTAINER = "telecom-data"
AZURE_SAS_TOKEN = os.getenv("AZURE_STORAGE_SAS_TOKEN")
AZURE_BLOB_URL = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"

if not AZURE_SAS_TOKEN:
    raise ValueError("AZURE_STORAGE_SAS_TOKEN environment variable is missing.")

plan_keys = [1, 2, 3]
payment_methods = ["Credit Card", "Bank Transfer", "Mobile Payment"]
payment_statuses = ["PAID", "PENDING", "FAILED"]

def upload_to_adls(local_file_path: str, blob_name: str) -> None:
    blob_service_client = BlobServiceClient(
        account_url=AZURE_BLOB_URL,
        credential=AZURE_SAS_TOKEN,
    )
    blob_client = blob_service_client.get_blob_client(
        container=AZURE_CONTAINER,
        blob=blob_name,
    )

    with open(local_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    print(f"Uploaded to ADLS: {blob_name}")

# -----------------------------
# GENERATE incremental fact_usage_daily
# -----------------------------
usage_rows = []

for i in range(1, NUM_USAGE_RECORDS + 1):
    customer_key = random.randint(1, NUM_CUSTOMERS)
    plan_key = random.choice(plan_keys)

    created_at = RUN_DATE_DT + timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )

    updated_at = created_at + timedelta(hours=random.randint(0, 3))

    usage_rows.append({
        "usage_id": int(f"{RUN_DATE_DT.strftime('%Y%m%d')}{i:06}"),
        "customer_key": customer_key,
        "plan_key": plan_key,
        "date_key": int(RUN_DATE_DT.strftime("%Y%m%d")),
        "usage_date": RUN_DATE_DT.date(),
        "data_usage_gb": round(random.uniform(0.1, 20.0), 3),
        "voice_minutes": random.randint(0, 500),
        "sms_count": random.randint(0, 300),
        "roaming_usage_gb": round(random.uniform(0, 5.0), 3),
        "created_at": created_at,
        "updated_at": updated_at,
    })

fact_usage_df = pd.DataFrame(usage_rows)

# -----------------------------
# GENERATE incremental fact_billing
# -----------------------------
billing_rows = []

for i in range(1, NUM_BILLING_RECORDS + 1):
    customer_key = random.randint(1, NUM_CUSTOMERS)
    plan_key = random.choice(plan_keys)

    billing_amount = round(random.uniform(20, 300), 2)
    tax_amount = round(billing_amount * 0.18, 2)

    created_at = RUN_DATE_DT + timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )

    updated_at = created_at + timedelta(hours=random.randint(0, 3))

    billing_rows.append({
        "billing_id": int(f"{RUN_DATE_DT.strftime('%Y%m%d')}{i:06}"),
        "customer_key": customer_key,
        "plan_key": plan_key,
        "date_key": int(RUN_DATE_DT.strftime("%Y%m%d")),
        "billing_date": RUN_DATE_DT.date(),
        "billing_amount": billing_amount,
        "tax_amount": tax_amount,
        "total_amount": round(billing_amount + tax_amount, 2),
        "payment_status": random.choice(payment_statuses),
        "payment_method": random.choice(payment_methods),
        "created_at": created_at,
        "updated_at": updated_at,
    })

fact_billing_df = pd.DataFrame(billing_rows)

# -----------------------------
# EXPORT + UPLOAD
# -----------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

csv_files = {
    "fact_usage_daily.csv": fact_usage_df,
    "fact_billing.csv": fact_billing_df,
}

for file_name, df in csv_files.items():
    local_path = f"{OUTPUT_DIR}/{file_name}"
    df.to_csv(local_path, index=False)

    blob_path = f"incremental/date={RUN_DATE}/{file_name}"
    upload_to_adls(local_path, blob_path)

print("Incremental CSV files generated and uploaded successfully!")
print(f"Run date: {RUN_DATE}")
print(f"fact_usage_daily rows: {len(fact_usage_df)}")
print(f"fact_billing rows: {len(fact_billing_df)}")