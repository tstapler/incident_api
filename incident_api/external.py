import asyncio
import json
import pprint
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from timeit import default_timer
from typing import Dict, List

import httpx
from httpx import Timeout
from pydantic import parse_obj_as

from incident_api.schemas import Denial, Intrusion, Misuse, Other, Probing, Unauthorized, Executable, IncidentCategory, \
    UserIncident, EmployeeRisk

INCIDENT_MAPPING = {
    "denial": Denial,
    "intrusion": Intrusion,
    "misuse": Misuse,
    "other": Other,
    "probing": Probing,
    "unauthorized": Unauthorized,
    "executable": Executable
}
API_HOST = "https://incident-api.use1stag.elevatesecurity.io"


def write_debug_payloads(resp, location):
    with Path(location).open("w") as f:
        f.write(str(resp.url))
        f.write("\n")
        f.write(str(resp.elapsed))
        f.write("\n")
        f.write(pprint.pformat(resp.headers, indent=2))
        f.write("\n")
        f.write(json.dumps(json.loads(resp.text), indent=2))


def fetch_url(creds, url, debug=True):
    # Increased timeouts because occasionally the API will return slow
    resp = httpx.get(url, auth=creds, timeout=Timeout(3, read=6))
    if debug:
        print(f"Fetching {url} took {resp.elapsed}")
    resp.raise_for_status()
    return resp


def fetch_incident(creds, incident_type, debug=False):
    url = f"{API_HOST}/incidents/{incident_type}"
    resp = fetch_url(creds, url)
    if debug:
        write_debug_payloads(resp, f"samples/{incident_type}.txt")
    # Returning results like this is a hack, proper error checking should be done
    return (incident_type, resp.json()["results"])


def fetch_identities(creds, debug=False):
    resp = fetch_url(creds, f"{API_HOST}/identities")
    if debug:
        write_debug_payloads(resp, f"samples/identities.txt")
    return resp.json()


def fetch_incidents_and_normalize(creds, identities: Dict[str, int], debug=False) -> Dict[
    IncidentCategory, List[UserIncident]]:
    Path("samples").mkdir(parents=True, exist_ok=True)

    results = []
    api_data = {}
    total_incidents = 0
    error_count = 0
    errors = []
    with ProcessPoolExecutor(max_workers=len(IncidentCategory)) as executor:
        for incident_category in IncidentCategory:
            results.append(executor.submit(fetch_incident, creds, incident_category, debug=debug))
        for future in as_completed(results):

            start = default_timer()
            incident_category, response_results = future.result()
            output = parse_obj_as(List[INCIDENT_MAPPING[incident_category]], response_results)
            api_data[incident_category] = []
            for incident in output:
                total_incidents += 1
                try:
                    api_data[incident_category].append(incident.to_user_incident(identities))
                # TODO some times the API returns incidents that are not associated with a user
                except KeyError as e:
                    error_count += 1
                    if debug:
                        errors.append((incident_category, e))
            end = default_timer()
            print(f"Processing the incident data for {incident_category} took {end - start}")
        executor.shutdown()
    print(f"Completed fetching {total_incidents} incidents with {error_count} errors")
    if errors:
        pprint.pprint(errors, indent=2)
    return api_data


def aggregate_incidents_per_employee(incident_data: Dict[IncidentCategory, List[UserIncident]]) -> Dict[
    str, EmployeeRisk]:
    aggregate_data = {}
    for incident_category in IncidentCategory:
        for incident in incident_data[incident_category]:
            if incident.employee_id not in aggregate_data:
                risk = EmployeeRisk()
                aggregate_data[incident.employee_id] = risk
            aggregate_data.get(incident.employee_id).add_incident(incident)

    return aggregate_data


def fetch_employee_incidents(creds, debug=False) -> Dict[str, EmployeeRisk]:
    start = default_timer()
    print("Downloading identities")
    identities = fetch_identities(creds, debug=debug)
    print("Downloading incident_data")
    incident_data = fetch_incidents_and_normalize(creds, identities, debug=debug)
    start_aggregate = default_timer()
    aggregate_data = aggregate_incidents_per_employee(incident_data)
    end = default_timer()
    print(f"It took {end - start_aggregate} to aggregate the data")
    print(f"It took {end - start} to fetch and process the data")
    return aggregate_data


async def non_blocking_fetch_employee_incidents(creds):
    loop = asyncio.get_event_loop()
    # This is an easy way to run our blocking fetch_employee_incidents code in an event loop
    return await loop.run_in_executor(None, fetch_employee_incidents, creds)
