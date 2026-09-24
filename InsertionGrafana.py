import requests
import json
import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# === Configuration PostgreSQL ===
POSTGRES_URL = 'postgresql://admin:?BdDgraf2526!@10.3.2.216:5432/Bdd_Grafana'


# === Configuration API UiPath ===
client_id = '3f4ca141-dcc1-499a-ba04-3dde2f88c7ac'
client_secret = 'B)#KmRVGDwoS5t*D'
token_url = 'https://cloud.uipath.com/identity_/connect/token'
api_url = 'https://cloud.uipath.com/lyrecomanagement/DefaultTenant/orchestrator_/odata/Jobs'
organization_unit_ids = ["1966356","1966108","1966362","1966391","1966046","1966072","1966085","1966379","2016480","1966350","1966100","1966059","1966042","1966004","1966003","1966091","1966036","1966022","1966064"]
proxies = {
    "http": "http://proxy.lyreco.com:8080",
    "https": "http://proxy.lyreco.com:8080"
}

# === SQLAlchemy Setup ===
Base = declarative_base()
engine = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=engine)

# === ORM Model ===
class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    state = Column(String)
    job_priority = Column(String)
    source = Column(String)
    info = Column(Text)
    creation_time = Column(DateTime)
    release_name = Column(String)

# === DB Setup ===
def create_tables():
    try:
        Base.metadata.create_all(engine)
        print("✅ Tables créées ou déjà existantes")
    except SQLAlchemyError as e:
        print(f"❌ Erreur création des tables : {e}")
        sys.exit(1)

# === Auth ===
def get_access_token():
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'OR.Jobs.Read'
    }
    try:
        response = requests.post(token_url, data=payload, proxies=proxies)
        response.raise_for_status()
        token_data = response.json()
        return token_data['access_token'], datetime.now() + timedelta(seconds=token_data['expires_in'])
    except requests.RequestException as e:
        print(f"❌ Erreur token : {e}")
        sys.exit(1)

# === Multi-OU Job Fetch ===
def fetch_jobs_for_all_units(api_url, token):
    all_jobs = []
    headers_base = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }

    for unit_id in organization_unit_ids:
        headers = headers_base.copy()
        headers['X-UIPATH-OrganizationUnitId'] = unit_id

        try:
            response = requests.get(api_url, headers=headers, proxies=proxies)
            response.raise_for_status()
            jobs_data = response.json().get('value', [])
            print(f"✅ {len(jobs_data)} jobs récupérés pour OrganizationUnitId {unit_id}")
            all_jobs.extend(jobs_data)
        except requests.RequestException as e:
            print(f"❌ Erreur pour OrganizationUnitId {unit_id} : {e}")

    return all_jobs

# === Enregistrement dans PostgreSQL ===
def save_jobs_to_db(jobs):
    session = Session()
    try:
        for job_data in jobs:
            job = Job(
                id=job_data.get("Id"),
                key=job_data.get("Key"),
                start_time=parse_date(job_data.get("StartTime")),
                end_time=parse_date(job_data.get("EndTime")),
                state=job_data.get("State"),
                job_priority=job_data.get("JobPriority"),
                source=job_data.get("Source"),
                info=job_data.get("Info"),
                creation_time=parse_date(job_data.get("CreationTime")),
                release_name=job_data.get("ReleaseName")
            )
            # UPSERT
            existing = session.query(Job).get(job.id)
            if existing:
                for attr, value in job.__dict__.items():
                    if attr != "_sa_instance_state":
                        setattr(existing, attr, value)
            else:
                session.add(job)
        session.commit()
        print(f"✅ {len(jobs)} jobs enregistrés / mis à jour.")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"❌ Erreur enregistrement DB : {e}")
        sys.exit(1)
    finally:
        session.close()

# === Utilitaire pour les dates ===
def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None

# === Main ===
def main():
    create_tables()
    token, expiry_time = get_access_token()
    jobs = fetch_jobs_for_all_units(api_url, token)
    if not jobs:
        print("⚠️ Aucun job récupéré.")
        sys.exit(1)
    save_jobs_to_db(jobs)

if __name__ == "__main__":
    main()