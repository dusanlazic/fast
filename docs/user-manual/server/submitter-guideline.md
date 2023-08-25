The submitter module is a vital part of Fast, responsible for the actual submission of flags to the competition's flag-checking service. Fast is adaptable to any A/D competition because it lets you write this module yourself. To work properly with Fast, your submitter script must follow the simple guideline specified below.

## Structure of the Submitter Module

The submitter script must define a function named `submit` that takes a list of flags (as string values) ready for submission. This function is responsible for submitting the flags to the flag-checking service and collecting the responses.

The `submit` function returns a tuple of two dictionaries:

1. **Accepted Flags**: A dictionary containing the flags that were accepted by the service, with the flag as the key and the corresponding response as the value.
2. **Rejected Flags**: A dictionary containing the flags that were rejected by the service, with the flag as the key and the corresponding response as the value.

You can adapt the submit function to work with various flag submission mechanisms, such as submitting through a REST API, or over a raw TCP connection. See below for examples.

=== "HTTP"

    ```python
    import requests

    def submit(flags):
        flag_responses = requests.post('http://example.ctf/flags', json=flags).json()
        accepted_flags = { item['flag']: item['response'] for item in flag_responses if item['response'].endswith('OK') }
        rejected_flags = { item['flag']: item['response'] for item in flag_responses if not item['response'].endswith('OK') }
        return accepted_flags, rejected_flags
    ```

=== "Raw TCP"

    ```python
    from pwn import *

    def submit(flags):
        accepted_flags, rejected_flags = {}
        r = remote('flags.example.ctf', 1337)
        for flag in flags:
            r.sendline(flag.encode())
            response = r.recvline().decode().strip()
            if response.endswith('OK')
                accepted_flags[flag] = response
            else:
                rejected_flags[flag] = response
        return accepted_flags, rejected_flags
    ```


## Template

If you like type hints, you can use the following template.

```python
from typing import List, Tuple, Dict

def submit(flags: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    accepted_flags = {}
    rejected_flags = {}

    # Submit and categorize flags

    return accepted_flags, rejected_flags

```

## Integration

The script must be placed in the same directory as your `server.yaml` configuration file. By default, it must be named `submitter.py`. 

If you need to name it differently, see the example in the [User Manual](configuration.md#examples_1).