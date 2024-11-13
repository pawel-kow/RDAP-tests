import requests
import json
import csv
from collections import defaultdict

# URL for the JSON file
url = "https://data.iana.org/rdap/dns.json"

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

def request_help(server_url, headers):
    print(f"Requesting {server_url} with {headers}", end="")
    try:
        response = requests.get(f"{server_url}/help", headers=headers)
        content_type = response.headers.get("Content-Type", "Unknown")
        print("... OK!")
        return response.status_code, response.text, content_type
    except requests.RequestException as e:
        print(f"... ERROR {e}")
        return None, str(e), "Error"

def compare_results(results_with_param, results_without_param):
    status_match = results_with_param[0] == results_without_param[0]
    content_type_match = results_with_param[2] == results_without_param[2]
    content_match = results_with_param[1] == results_without_param[1]
    return status_match and content_type_match and content_match

def main():
    # Step 1: Download and parse the JSON file
    data = download_json(url)
    services = data["services"]

    # Step 2: Create the server dictionary
    server_dict = parse_services(services)

    # Step 3: Make requests to each server's /help endpoint
    results = []
    same_response_count = 0
    same_response_buggy_count = 0
    total_servers = 0

    for server_url, tlds in server_dict.items():
        # Request headers for each content type
        headers_no_param = {"Accept": "application/rdap+json"}
        headers_with_param = {"Accept": "application/rdap+json; extensions=foo,bar"}
        headers_buggy_param = {"Accept": "application/x.foobar"}

        # Make all requests
        status_code_no_param, content_no_param, content_type_no_param = request_help(server_url, headers_no_param)
        status_code_with_param, content_with_param, content_type_with_param = request_help(server_url, headers_with_param)
        status_code_buggy_param, content_buggy_param, content_type_buggy_param = request_help(server_url, headers_buggy_param)

        # Compare the responses
        same_response = compare_results(
            (status_code_no_param, content_no_param, content_type_no_param),
            (status_code_with_param, content_with_param, content_type_with_param)
        )
        same_response_buggy = compare_results(
            (status_code_no_param, content_no_param, content_type_no_param),
            (status_code_buggy_param, content_buggy_param, content_type_buggy_param)
        )
        if same_response:
            same_response_count += 1
        if same_response_buggy:
            same_response_buggy_count += 1
        total_servers += 1

        # Store result
        results.append({
            "Server URL": server_url,
            "TLDs": ", ".join(tlds),
            "Status Code No Param": status_code_no_param,
            "Content Type No Param": content_type_no_param,
            "Content No Param": content_no_param[:30],  # Truncate content for CSV readability
            "Status Code With Param": status_code_with_param,
            "Content Type With Param": content_type_with_param,
            "Content With Param": content_with_param[:30],  # Truncate content for CSV readability
            "Status Code With Buggy": status_code_buggy_param,
            "Content Type Buggy": content_type_buggy_param,
            "Content With Buggy": content_buggy_param[:30],  # Truncate content for CSV readability
            "Same Response": same_response,
            "Same Response Buggy": same_response_buggy
        })
        if total_servers == 5:
            break

    # Step 4: Save results to CSV
    with open("rdap_help_responses.csv", "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = results[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect='excel', delimiter=';')
        writer.writeheader()
        writer.writerows(results)

    # Step 5: Output statistics
    percentage_same = (same_response_count / total_servers) * 100
    print(f"{percentage_same:.2f}% of servers {same_response_count}/{total_servers} returned the same response for both request with and without parameters in application/rdap+json media type.")
    percentage_same_buggy = (same_response_buggy_count / total_servers) * 100
    print(f"{percentage_same_buggy:.2f}% of servers {same_response_buggy_count}/{total_servers} returned the same response for both request with valid application/json and invalid application/x.foobar media type.")

if __name__ == "__main__":
    main()
