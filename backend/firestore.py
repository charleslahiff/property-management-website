import os
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

_db = None

def get_db() -> firestore.Client:
    global _db
    if _db is None:
        project_id = os.environ.get("GCP_PROJECT_ID")
        _db = firestore.Client(project=project_id)
    return _db