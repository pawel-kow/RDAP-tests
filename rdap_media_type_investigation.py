import requests
import json
import csv
import time
import socket
from collections import defaultdict, deque
from urllib.parse import urlparse, urljoin
import random

# URL for the JSON file
url = "https://data.iana.org/rdap/dns.json"

RATE_LIMIT_STATUS_CODES = {429, 403}
TIMEOUT_STATUS_CODES = {500, 502, 503, 504}
INITIAL_BACKOFF = 5  # Start with 5 seconds
MAX_BACKOFF = 60 * 60 * 2  # Maximum of 2 hours
MAX_RETRIES = 5

def download_json(url):
    response = requests.get(url)
    response.raise_for_status()  # Ensure we raise an error for bad responses
    return response.json()

def parse_services(services):
    server_dict = defaultdict(list)
    for service in services:
        tlds, servers = service[0], service[1]
        for server in servers:
            server_dict[server].extend(tlds)
    return server_dict

def get_server_ip(server_url):
    parsed_url = urlparse(server_url)
    try:
        # Use socket.gethostbyname to get the IP address of the server
        ip_address = socket.gethostbyname(parsed_url.hostname)
        return ip_address
    except socket.gaierror:
        return None

def request_help(server_url, headers):
    print(f"Requesting {server_url} with {headers}", end="")
    try:
        response = requests.get(urljoin(server_url, 'help'), headers=headers, timeout=5)
        content_type = response.headers.get("Content-Type", "Unknown")
        print(f"... OK [{response.status_code}] [{content_type}]!")
        # if response.status_code != 200:
        #     print(f"DEBUG code {response.status_code}: {response.headers} {response.text[:300]}")
        return response.status_code, response.text, content_type
    except requests.ConnectTimeout as e:
        print(f"... ERROR Timeout {e}")
        return "Timeout", str(e), "ConnectTimeout"
    except requests.Timeout as e:
        print(f"... ERROR Read Timeout {e}")
        return "Timeout", str(e), "ReadTimeout"
    except requests.RequestException as e:
        print(f"... ERROR {e}")
        return "Error", str(e), "Error"

def is_valid_rdap(content):
    try:
        data = json.loads(content)
        has_rdap_conformance = "rdapConformance" in data
        return True, has_rdap_conformance
    except json.JSONDecodeError:
        return False, False

def compare_results(results_with_param, results_without_param):
    status_match = results_with_param[0] == results_without_param[0]
    content_type_match = results_with_param[2] == results_without_param[2]
    content_match = results_with_param[1] == results_without_param[1]
    return status_match and content_type_match and content_match

def main():
    def print_totals():
        print("**** TOTALS ****")
        for test in headers_list:
            if test != reference_test:
                percentage_same = (same_responses[test] / len(results)) * 100
                print(f"{percentage_same:.2f}% of servers {same_responses[test]}/{len(results)} returned the same response for the test {test}.")
        print("**** TOTALS OK RDAP ****")
        if (ref_response_ok > 0):
            for test in headers_list:
                if test != reference_test:
                    percentage_same = (same_responses_ok[test] / ref_response_ok) * 100
                    print(f"{percentage_same:.2f}% of servers {same_responses_ok[test]}/{ref_response_ok} returned the same response for the test {test}.")
        else:
            print("No successful reference response in results.")

    # Step 1: Download and parse the JSON file
    data = download_json(url)
    services = data["services"]

    # Step 2: Create the server dictionary
    server_dict = parse_services(services)

    # Step 3: Define headers for each test
    headers_list = {
        "RFC conform": {"Accept": "application/rdap+json"}, # RFC conform
        "With parameter": {"Accept": 'application/rdap+json;extensions="rdap_level_0 rdapx foo"'}, # added parameters
        "Bogus": {"Accept": "application/x.foobar"}, # added buggy media type
        "RDAP-X": {"Accept": 'application/rdap+json,application/rdap-x+json;extensions="rdap_level_0 rdapx foo"'}, # example from RDAP-X draft
        "RDAP-X reversed and with q": {"Accept": 'application/rdap-x+json;extensions="rdap_level_0 rdapx foo",application/rdap+json;q=0.9'}, # example from RDAP-X draft
    }
    reference_test = "RFC conform"
    results = []
    ref_response_ok = 0
    same_responses = {}
    same_responses_ok = {}
    for test in headers_list:
        if test != reference_test:
            same_responses[test] = 0
            same_responses_ok[test] = 0
    # Dictionary to store timestamps for each server IP
    request_timestamps = defaultdict(deque)

    # Initialize retry queue
    lst = [(server_url, tlds) for server_url, tlds in server_dict.items()]
    random.shuffle(lst)
    retry_queue = deque(lst)
    server_retries = defaultdict(int)  # Track retry attempts per server
    backoff_info = defaultdict(lambda: {"retries": 0, "delay": INITIAL_BACKOFF, "next_retry": time.time(), "trottled": 0})

    try:
        while retry_queue:
            # Print current state of the queue
            print(f"Queue state: {len(retry_queue)} items to process")

            # Get the next server to process
            server_url, tlds = retry_queue.popleft()
            # Get the server's IP address using socket.gethostbyname
            server_ip = get_server_ip(server_url)
            if not server_ip:
                print(f"Could not resolve IP for {server_url}.")
                server_ip = '0.0.0.0'

            # Check if the server is not backed off and requeue if needed
            if backoff_info[server_ip]["next_retry"] > time.time():
                print(f"Request to server {server_url} [{server_ip}] delayed - Retry: {backoff_info[server_ip]['retries']}, Delay: {backoff_info[server_ip]['delay']}, Next: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(backoff_info[server_ip]['next_retry']))} in {backoff_info[server_ip]['next_retry'] - time.time():.0f}s")
                retry_queue.append((server_url, tlds))
                time.sleep(1)
                continue

            # Step 4: Perform all requests and gather results
            responses = {}
            for test in headers_list:
                status_code, content, content_type = request_help(server_url, headers_list[test])
                if backoff_info[server_ip]["trottled"] > 0:
                    time.sleep(backoff_info[server_ip]["trottled"])
                is_json, has_rdap_conformance = is_valid_rdap(content)
                responses[test] = {
                    "Status Code": status_code,
                    "Content": content[:1000],  # Truncate content for CSV readability
                    "Content Type": content_type,
                    "Is JSON": is_json,
                    "Has rdapConformance": has_rdap_conformance
                }

            # Check if any of the requests had rate-limiting or timeout errors (HTTP 429 or 5xx)
            if any(status_code == "Timeout" or status_code in RATE_LIMIT_STATUS_CODES or status_code in TIMEOUT_STATUS_CODES for status_code in [responses[test]["Status Code"] for test in headers_list]):
                print(f"Rate limiting hit for server {server_url}: {[responses[test]['Status Code'] for test in headers_list]}")
                backoff_info[server_ip]["delay"] = backoff_info[server_ip]["delay"] * 2 if backoff_info[server_ip]["delay"] * 2 < MAX_BACKOFF else MAX_BACKOFF 
                if backoff_info[server_ip]['delay'] == MAX_BACKOFF:
                    backoff_info[server_ip]['retries'] += 1
                backoff_info[server_ip]["next_retry"] = time.time() + backoff_info[server_ip]["delay"]
                backoff_info[server_ip]["trottled"] += 1 
                if backoff_info[server_ip]['retries'] < MAX_RETRIES:
                    print(f"Backing off server {server_url} [{server_ip}] - Retry: {backoff_info[server_ip]['retries']}, Delay: {backoff_info[server_ip]['delay']}, Next: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(backoff_info[server_ip]['next_retry']))} in {backoff_info[server_ip]['next_retry'] - time.time():.0f}s")
                    retry_queue.append((server_url, tlds))
                    continue
                else:
                    print(f"FAIL: Max retries reached for {server_url} [{server_ip}] - Retry: {backoff_info[server_ip]['retries']}, Delay: {backoff_info[server_ip]['delay']}, Next: {backoff_info[server_ip]['next_retry']}")
            else:
                backoff_info[server_ip] = {"retries": 0, "delay": INITIAL_BACKOFF, "next_retry": time.time(), "trottled": backoff_info[server_ip]["trottled"]}

            # Step 5: Compare responses
            for test in headers_list:
                if test != reference_test:
                    same_response = (
                        responses[test]["Status Code"] == responses[reference_test]["Status Code"] and
#                        responses[test]["Content Type"] == responses[reference_test]["Content Type"] and
                        responses[test]["Content"] == responses[reference_test]["Content"]
                    )
                    responses[test]["Same Response"] = same_response
                    if same_response:
                        same_responses[test] += 1
                    if responses[test]["Status Code"] == 200 and responses[test]["Has rdapConformance"] and same_response:
                        same_responses_ok[test] += 1

                else:
                    if responses[test]["Status Code"] == 200 and responses[test]["Has rdapConformance"]:
                        ref_response_ok += 1

            # Store result
            res = {
                "Server URL": server_url,
                "TLDs": ", ".join(tlds)
            }
            for test in headers_list:
                for key in responses[test]:
                    res[f"{test} {key}"] = responses[test][key]
            results.append(res)
            if len(results) % 10 == 0:
                print_totals()

    except KeyboardInterrupt:
        print("Interrupted by user")

    # Step 4: Save results to CSV
    with open("rdap_help_responses.csv", "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = results[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect='excel', delimiter=';')
        writer.writeheader()
        writer.writerows(results)
        
    # Step 5: Output statistics    
    print_totals()
    
if __name__ == "__main__":
    main()
