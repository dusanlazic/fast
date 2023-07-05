# 🚩 Fast — Flag Acquisition and Submission Tool

Fast is a Python tool designed to easily manage your exploits and automate submitting flags in A/D competitions. The goal of Fast is to make writing exploits your only concern in A/D competitions, while maintaining simplicity.

> Keep in mind that this tool is in early stages of development and at this moment it is still an experimental tool. Fast is yet to be improved and battle tested. :)

## Installation

To install Fast, follow these steps:

```sh
$ git clone https://github.com/dusanlazic/fast.git
$ cd fast
$ pip install .
```

## Usage

1. After installing Fast, navigate to the directory containing your exploit scripts and the flag submitting script. Directory structure may look like this, and exploits should follow this [simple guideline](#exploit-script-guidelines).

```
myexploits/
├── alpha.py
├── bravo.py
├── charlie.py
├── delta.rs
├── echo.py
├── foxtrot.py
├── golf.sh
└── submitter.py
```

2. In the same directory, create a file named `fast.yaml`. This file will contain configuration for the game, the submitter, your exploits and their target IPs. The following example should cover everything you can do with Fast for now:

```yaml
game:
  tick_duration: 100
  flag_format: FAST\{[a-f0-9]{40}\}  # Fast will extract the flag from your exploit's response
  team_ip: 172.20.0.5  # Skip your own team

submitter:
  tick_start_delay: 30  # Submit flags 30 seconds after the beginning of each tick
  run_every_nth_tick: 3  # If flags stay valid for multiple ticks (e.g. 3), submit on every 3rd tick instead (default: 1)
  module: submitter  # Submitter module name (default: submitter)

exploits:
  # IPs can be listed individually, and IP ranges can be expressed using hyphens
  - name: alpha
    targets:
      - 172.20.0.3
      - 172.20.0.5
      - 172.20.0.7-11

  # Timeout can be set for terminating a hanging exploit
  - name: bravo
    timeout: 15
    targets:
      - 172.20.0.2-11

  # Exploit can have a custom name different from its module name
  - name: charlie (v2)
    module: charlie
    targets:
      - 172.20.0.2-11

  # Non-Python exploit can be ran as a custom shell command
  - name: delta
    cmd: rustc delta.rs && ./delta [ip]
    targets:
      - 172.20.0.2-11

  # Environment variables can be set
  - name: echo
    env:
      KEY: 26fc75b98472
      WEBHOOK: https://webhook.site/00d8f0b7-6084-4aa0-8b59-a728ae2be450
    targets:
      - 172.20.0.2-11

  # Too many exploits consuming resources on each tick? Arrange them by setting a delay
  - name: foxtrot
    delay: 5
    targets:
      - 172.20.0.2-11

  # Choose things that you need!
  - name: golf (bash)
    cmd: bash golf.sh [ip]
    env:
      API_KEY: 0898ef92b120
    timeout: 20
    targets:
      - 172.20.0.2-11

```

3. Run fast

```sh
$ fast
```

### Exploit Script Guideline

#### Python scripts

To work properly with Fast, your script should have a function named `exploit` that takes the target's IP address as the only parameter, and returns the flag (or some text containing the flag) as a string. That's about it.

Here is a very basic example of how an exploit script should be structured:

```python
import requests

def exploit(target):
    return requests.get(f"http://{target}:5000/flag").text
```

#### Other scripts

For non-Python scripts, just provide a way to pass the target's IP address as a command line argument, and make sure to output nothing but the flag (or some text containing the flag) on `stdout`.

Something like this:
```bash
#!/bin/bash
curl -s "http://$1:5000/flag"
```

When adding the exploit to `fast.yaml`, provide the command for running it and include the placeholder for target's IP (`[ip]`):
```yaml
- name: my bash exploit
  cmd: bash getflag.sh [ip]
  targets:
    - 172.20.0.2-11
```

### Submitter Script Guideline

Your submitter script should also follow certain guidelines:

1. Submitter script should have a function named `submit`.
2. The `submit` function should take one parameter, `flags`, which is a list of flags (string values) for submission.
3. The `submit` function should return two lists, the first one should be a list of accepted flags, and the second one a list of rejected flags.

Here is an example of how a submitter script may look like:

```python
import requests
import json

headers = {
    'Content-Type': 'application/json',
    'X-Team-ID': '5c1be7f38b586cd4'
}

def submit(flags):
    payload = json.dumps(flags)

    response = requests.post('http://172.20.0.99:5000/flags', data=payload, headers=headers).text

    flag_statuses = json.loads(response)

    accepted_flags = [item["flag"] for item in flag_statuses if item["status"] == "Flag accepted!"]
    rejected_flags = [item["flag"] for item in flag_statuses if item["status"] != "Flag accepted!"]

    return accepted_flags, rejected_flags
```

## Additional commands

### `fire`

When you add a new exploit to the `fast.yml` file, it will be loaded and executed during the next tick. However, if you do not want to wait and prefer to get the flags right away, you can run the exploits immediately by running `fire <exploit names>`.

### `submit`

In a similar manner to the `fire` command, you can also trigger flag submission by running `submit`. 

This command can be useful in combination with `fire`. For instance:

```bash
fire alpha bravo && submit
```

Executing this command will run the specified exploits and submit all the flags in the queue.
