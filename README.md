# README

## Overview

This Python script is designed to interact with servers listed in the IANA RDAP (Registration Data Access Protocol) directory, assess their response compliance with various media types when making RDAP requests and server reactions to additional media types or unknown media type parameters. The script makes repeated HTTP requests with different `Accept` headers to test server responses and collects metrics on response type, content, and compliance with RDAP standards. The results are saved in a CSV file for later analysis.

## Requirements

- Python 3.x
- Required libraries: `requests`

Install any missing libraries using:

```bash
pip install requests
```

## How It Works

### Script Logic

1. **Download JSON Data:** Retrieves and parses the list of RDAP servers.
2. **Initialize Testing Parameters:** Sets up headers for different test cases, a reference test for comparison, and a retry/backoff system for managing rate limits.
3. **Request Testing and Rate Limiting:** Iterates through servers, sending requests with different headers. If rate-limited, the script follows exponential backoff before retrying.
4. **Response Comparison:** Compares server responses with and without specific parameters for consistency.
5. **Result Collection:** Aggregates results and stores them in a CSV file.
6. **Final Report:** Summarizes test statistics, including compliance rates and rate-limiting observations.

### Rate Limiting and Backoff

The script uses a rate-limiting system to avoid overwhelming servers:
- **Initial Backoff:** Starts at 5 seconds.
- **Exponential Backoff:** Doubles the wait time up to a maximum of 2 hours.
- **Max Retries:** Stops retrying after 5 failed attempts per server.

### Running the Script

Run the script from the command line:

```bash
python rdap_server_tester.py
```

To stop the script at any time, use `Ctrl + C`.

### Output

- **CSV File (`rdap_help_responses.csv`):** Stores response data for each server, including response status, content, type, and compliance.
- **Console Output:** Periodically prints progress and summaries, including compliance percentages.

## Important Notes

- **Rate Limits:** The script respects server rate limits by implementing exponential backoff. Avoid modifying backoff settings to prevent IP bans.
- **Reference Test:** "RFC conform" serves as the reference test to which other responses are compared.
- **Error Handling:** Servers that cannot be reached or return repeated errors are marked and skipped after max retries.

## License

This script is open-source and may be used and modified under the MIT License. Please review and adhere to IANA RDAP usage guidelines when using this script.