import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://app.jobsbyhumans.com"
API_KEY = os.environ["HUMANSTANDARD_API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

if len(sys.argv) < 2:
    print("Usage: python check_job.py <job_id>")
    sys.exit(1)
job_id = sys.argv[1]
response = requests.get(f"{BASE_URL}/api/jobs/{job_id}/status", headers=HEADERS, timeout=30)
response.raise_for_status()
print(response.json())
