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
NUM_USAGE_RECORDS = 500000
NUM_BILLING_RECORDS = 200000

OUTPUT_DIR = "./telecom_data/historical"

HISTORICAL_START_DATE = datetime(2026, 1, 1)
HISTORICAL_END_DATE = datetime(2026, 4, 30)

# -----------------------------
# AZURE STORAGE CONFIGURATION
# -----------------------------
AZURE_STORAGE_ACCOUNT = "telelcomhuaweidemo"
AZURE_CONTAINER = "telecom-data"
AZURE_SAS_TOKEN = os.getenv("sv=2025-11-05&ss=bfqt&srt=sco&sp=rwdlacupyx&se=2027-03-18T19:02:25Z&st=2026-05-13T10:47:25Z&spr=https&sig=jBKNtvwDp60bHEqYrKJNiHMsdPWIemwbtNHgDf4ElSU%3D")

AZURE_BLOB_URL = f"https://telelcomhuaweidemo.blob.core.windows.net"

if not AZURE_SAS_TOKEN:
    raise ValueError("AZURE_STORAGE_SAS_TOKEN environment variable is missing.")

# -----------------------------
# HELPER DATA
# -----------------------------
cities = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Kocaeli", "Adana"]
countries = ["Turkey"]

plan_data = [
    ("PLAN001", "Basic", "Prepaid", 20, 10, 500, 1000),
    ("PLAN002", "Premium", "Postpaid", 50, 50, 2000, 5000),
    ("PLAN003", "Enterprise", "Corporate", 120, 200, 10000, 20000),
]

payment_methods = ["Credit Card", "Bank Transfer", "Mobile Payment"]
payment_statuses = ["PAID", "PENDING", "FAILED"]

# -----------------------------
# UPLOAD HELPER
# -----------------------------
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
# GENERATE dim_customer
# -----------------------------
customers = []

for i in range(1, NUM_CUSTOMERS + 1):
    created_at = fake.date_time_between(
        start_date=datetime(2025, 1, 1),
        end_date=HISTORICAL_END_DATE,
    )

    updated_at = created_at + timedelta(days=random.randint(0, 120))
    if updated_at > HISTORICAL_END_DATE:
        updated_at = HISTORICAL_END_DATE

    customers.append({
        "customer_key": i,
        "customer_id": f"CUST{i:06}",
        "msisdn": f"905{random.randint(100000000, 999999999)}",
        "customer_name": fake.name(),
        "gender": random.choice(["Male", "Female"]),
        "age": random.randint(18, 70),
        "city": random.choice(cities),
        "country": random.choice(countries),
        "join_date": created_at.date(),
        "status": random.choice(["ACTIVE", "SUSPENDED"]),
        "created_at": created_at,
        "updated_at": updated_at,
    })

dim_customer_df = pd.DataFrame(customers)

# -----------------------------
# GENERATE dim_plan
# -----------------------------
plans = []

for idx, plan in enumerate(plan_data, start=1):
    created_at = datetime(2025, 1, 1)

    plans.append({
        "plan_key": idx,
        "plan_id": plan[0],
        "plan_name": plan[1],
        "subscription_type": plan[2],
        "monthly_fee": plan[3],
        "data_limit_gb": plan[4],
        "voice_limit_min": plan[5],
        "sms_limit": plan[6],
        "created_at": created_at,
        "updated_at": created_at,
    })

dim_plan_df = pd.DataFrame(plans)

# -----------------------------
# GENERATE dim_date
# -----------------------------
date_rows = []

current_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

while current_date <= end_date:
    date_rows.append({
        "date_key": int(current_date.strftime("%Y%m%d")),
        "full_date": current_date.date(),
        "year": current_date.year,
        "quarter": (current_date.month - 1) // 3 + 1,
        "month": current_date.month,
        "month_name": current_date.strftime("%B"),
        "day": current_date.day,
        "day_of_week": current_date.weekday(),
        "is_weekend": current_date.weekday() >= 5,
    })

    current_date += timedelta(days=1)

dim_date_df = pd.DataFrame(date_rows)

# -----------------------------
# GENERATE fact_usage_daily
# -----------------------------
usage_rows = []

for i in range(1, NUM_USAGE_RECORDS + 1):
    customer_key = random.randint(1, NUM_CUSTOMERS)
    plan_key = random.randint(1, len(plan_data))

    usage_date = fake.date_between(
        start_date=HISTORICAL_START_DATE,
        end_date=HISTORICAL_END_DATE,
    )

    created_at = datetime.combine(usage_date, fake.time_object())
    updated_at = created_at + timedelta(hours=random.randint(0, 72))

    if updated_at > HISTORICAL_END_DATE:
        updated_at = HISTORICAL_END_DATE

    usage_rows.append({
        "usage_id": i,
        "customer_key": customer_key,
        "plan_key": plan_key,
        "date_key": int(usage_date.strftime("%Y%m%d")),
        "usage_date": usage_date,
        "data_usage_gb": round(random.uniform(0.1, 20.0), 3),
        "voice_minutes": random.randint(0, 500),
        "sms_count": random.randint(0, 300),
        "roaming_usage_gb": round(random.uniform(0, 5.0), 3),
        "created_at": created_at,
        "updated_at": updated_at,
    })

fact_usage_df = pd.DataFrame(usage_rows)

# -----------------------------
# GENERATE fact_billing
# -----------------------------
billing_rows = []

for i in range(1, NUM_BILLING_RECORDS + 1):
    customer_key = random.randint(1, NUM_CUSTOMERS)
    plan_key = random.randint(1, len(plan_data))

    billing_date = fake.date_between(
        start_date=HISTORICAL_START_DATE,
        end_date=HISTORICAL_END_DATE,
    )

    billing_amount = round(random.uniform(20, 300), 2)
    tax_amount = round(billing_amount * 0.18, 2)

    created_at = datetime.combine(billing_date, fake.time_object())
    updated_at = created_at + timedelta(hours=random.randint(0, 72))

    if updated_at > HISTORICAL_END_DATE:
        updated_at = HISTORICAL_END_DATE

    billing_rows.append({
        "billing_id": i,
        "customer_key": customer_key,
        "plan_key": plan_key,
        "date_key": int(billing_date.strftime("%Y%m%d")),
        "billing_date": billing_date,
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
# EXPORT CSV FILES
# -----------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

csv_files = {
    "dim_customer.csv": dim_customer_df,
    "dim_plan.csv": dim_plan_df,
    "dim_date.csv": dim_date_df,
    "fact_usage_daily.csv": fact_usage_df,
    "fact_billing.csv": fact_billing_df,
}

for file_name, df in csv_files.items():
    local_path = f"{OUTPUT_DIR}/{file_name}"
    df.to_csv(local_path, index=False)

    blob_path = f"historical/{file_name}"
    upload_to_adls(local_path, blob_path)

print("Historical CSV files generated and uploaded successfully!")
print(f"Output directory: {OUTPUT_DIR}")
print(f"dim_customer rows: {len(dim_customer_df)}")
print(f"dim_plan rows: {len(dim_plan_df)}")
print(f"dim_date rows: {len(dim_date_df)}")
print(f"fact_usage_daily rows: {len(fact_usage_df)}")
print(f"fact_billing rows: {len(fact_billing_df)}")