# Script run on 13-14.11.2024

## Test configuration
```python
{
    "RFC conform": {"Accept": "application/rdap+json"}, # RFC conform
    "With parameter": {"Accept": 'application/rdap+json;extensions="rdap_level_0 rdapx foo"'}, # added parameters
    "Bogus": {"Accept": "application/x.foobar"}, # added buggy media type
    "RDAP-X": {"Accept": 'application/rdap+json,application/rdap-x+json;extensions="rdap_level_0 rdapx foo"'}, # example from RDAP-X draft
    "RDAP-X reversed and with q": {"Accept": 'application/rdap-x+json;extensions="rdap_level_0 rdapx foo",application/rdap+json;q=0.9'}, # RDAP-X as first and with added parameters
}
```

## Summary
```
**** TOTALS ****
99.67% of servers 604/606 returned the same response for the test With parameter.
38.12% of servers 231/606 returned the same response for the test Bogus.
99.50% of servers 603/606 returned the same response for the test RDAP-X.
99.34% of servers 602/606 returned the same response for the test RDAP-X reversed and with q.
```
```
**** TOTALS of servers with correct RDAP answer for application/rdap+json ****
99.65% of servers 564/566 returned the same response for the test With parameter.
35.51% of servers 201/566 returned the same response for the test Bogus.
99.47% of servers 563/566 returned the same response for the test RDAP-X.
99.29% of servers 562/566 returned the same response for the test RDAP-X reversed and with q.
```

## Observations

Some servers would mirror the media type from the query including unknown parameters.
Example:
```
Requesting https://rdap.nic.jpmorgan/ with {'Accept': 'application/rdap+json'}... OK [200] [application/rdap+json]!
Requesting https://rdap.nic.jpmorgan/ with {'Accept': 'application/rdap+json;extensions="rdap_level_0 rdapx foo"'}... OK [200] [application/rdap+json;extensions="rdap_level_0 rdapx foo"]!
Requesting https://rdap.nic.jpmorgan/ with {'Accept': 'application/x.foobar'}... OK [406] [Unknown]!
Requesting https://rdap.nic.jpmorgan/ with {'Accept': 'application/rdap+json,application/rdap-x+json;extensions="rdap_level_0 rdapx foo"'}... OK [200] [application/rdap+json]!
Requesting https://rdap.nic.jpmorgan/ with {'Accept': 'application/rdap-x+json;extensions="rdap_level_0 rdapx foo",application/rdap+json;q=0.9'}... OK [200] [application/rdap+json]!
```
