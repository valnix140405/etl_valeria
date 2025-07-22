from airflow import DAG
from airflow.decorators import task
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from utils.mongo_utils import get_mongo_client
from utils.transform_helpers import (
    normalize_keys_to_snake_case,
    remove_duplicates_by_key,
    safe_parse_date
)
import requests

DB_NAME = "project2"

default_args = {
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="main_pipeline",
    description="Pipeline ETL completo: ingesta + transformación + carga",
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    tags=["pipeline"]
) as dag:

    # --- INGESTAS ---
    @task()
    def ingest_api_1():
        client = get_mongo_client()
        db = client[DB_NAME]
        db["raw_worldbank_country"].drop()
        url = "http://api.worldbank.org/v2/country/MX?format=json"
        response = requests.get(url)
        data = response.json()
        if len(data) < 2 or not data[1]:
            return {"records": 0, "source": "WorldBankCountry"}
        db["raw_worldbank_country"].insert_one(data[1][0])
        return {"records": 1, "source": "WorldBankCountry"}

    @task()
    def ingest_api_2():
        client = get_mongo_client()
        db = client[DB_NAME]
        db["raw_hipolabs"].drop()
        data = requests.get("http://universities.hipolabs.com/search?country=Mexico").json()
        db["raw_hipolabs"].insert_many(data)
        return {"records": len(data), "source": "Hipolabs"}

    @task()
    def ingest_api_3():
        client = get_mongo_client()
        db = client[DB_NAME]
        db["raw_worldbank"].drop()
        response = requests.get("https://api.worldbank.org/v2/country/MX/indicator/SE.TER.ENRR?format=json&per_page=100")
        data = response.json()
        records = data[1] if len(data) > 1 else []
        db["raw_worldbank"].insert_many(records)
        return {"records": len(records), "source": "WorldBank"}

    # --- TRANSFORMACIONES ---
    @task()
    def transform_country_profile():
        client = get_mongo_client()
        db = client[DB_NAME]
        raw = db["raw_worldbank_country"].find_one()
        if not raw:
            return {"processed_records": 0}
        doc = normalize_keys_to_snake_case(raw)
        doc["ingreso_simple"] = doc.get("income_level", {}).get("value", "").lower()
        doc["region_simple"] = doc.get("region", {}).get("value", "").lower()
        db["processed_worldbank_country"].drop()
        db["processed_worldbank_country"].insert_one(doc)
        return {"processed_records": 1}

    @task()
    def transform_hipolabs_data():
        client = get_mongo_client()
        db = client[DB_NAME]
        raw_data = list(db["raw_hipolabs"].find({}))
        transformed = []
        for doc in raw_data:
            doc = normalize_keys_to_snake_case(doc)
            if not doc.get("name"):
                continue
            doc["name_upper"] = doc["name"].upper()
            doc["country_code"] = "MX" if doc.get("country", "").lower() == "mexico" else "UNKNOWN"
            transformed.append(doc)
        final = remove_duplicates_by_key(transformed, lambda x: x["name"].lower())
        db["processed_hipolabs"].drop()
        if final:
            db["processed_hipolabs"].insert_many(final)
        return {"processed_records": len(final)}

    @task()
    def transform_worldbank_data():
        client = get_mongo_client()
        db = client[DB_NAME]
        raw_data = list(db["raw_worldbank"].find({}))
        transformed = []
        for doc in raw_data:
            doc = normalize_keys_to_snake_case(doc)
            if not doc.get("value") or not doc.get("date"):
                continue
            doc["value_percent"] = round(float(doc["value"]), 2)
            doc["parsed_date"] = safe_parse_date(doc["date"], fmt="%Y")
            transformed.append(doc)
        final = remove_duplicates_by_key(transformed, lambda x: (x["date"], x["indicator"]["id"]))
        db["processed_worldbank"].drop()
        if final:
            db["processed_worldbank"].insert_many(final)
        return {"processed_records": len(final)}

    # --- CARGA ---
    @task(trigger_rule=TriggerRule.ALL_SUCCESS)
    def load_mongo():
        client = get_mongo_client()
        db = client[DB_NAME]
        logs = {}
        for col, keys in {
            "processed_hipolabs": ["name"],
            "processed_worldbank": ["date", "indicator.id"]
        }.items():
            db[col].create_index([(k, 1) for k in keys])
            logs[col] = db[col].count_documents({})
        return logs

    # --- DEPENDENCIAS ---
    i1 = ingest_api_1()
    i2 = ingest_api_2()
    i3 = ingest_api_3()

    t1 = transform_country_profile()
    t2 = transform_hipolabs_data()
    t3 = transform_worldbank_data()

    [i1 >> t1, i2 >> t2, i3 >> t3] >> load_mongo()
