import os

from incident_api.external import fetch_employee_incidents

if __name__ == "__main__":
    user = os.getenv("ELEVATE_API_USER")
    password = os.getenv("ELEVATE_API_PASSWORD")
    creds = (user, password)
    fetch_employee_incidents(creds, debug=True)
