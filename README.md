# 🚩 Fast — Flag Acquisition and Submission Tool

Fast is a Python tool designed to easily manage your exploits and automate submitting flags in A/D competitions. The goal of Fast is to make writing exploits your only concern in A/D competitions, while maintaining simplicity.

> Keep in mind that this tool is in early stages of development and at this moment it is still an experimental tool. Fast is yet to be improved and more battle tested. :)


![Dashboard for monitoring real-time data](/docs/dashboard.png)


## Installation

> Remember to create a Python virtual environment before installing:
> 
> `python3 -m venv venv && source venv/bin/activate`

To install Fast you can use this one-liner.

```sh
curl -s https://lazicdusan.com/fast.sh | sh
```

Or you can do it yourself.

```sh
git clone --depth 1 https://github.com/dusanlazic/fast.git
pip install fast/
```

If you wish to edit the source code while using it, install in editable mode.
```sh
pip install -e fast/
```

## Usage

### Setup server 🗄

1. After installing Fast on your submitter-dedicated machine, navigate to a preferably empty directory and create a file named `server.yaml`. This file will contain the configuration for the game, submitter and server. The following example covers everything you should configure.

```yaml
game:
  tick_duration: 120
  flag_format: FAST\{[a-f0-9]{10}\}  # Fast will extract all the flags from your exploit's response
  team_ip: 172.20.0.5  # Skip your own team. If your team has multiple addresses, use a list: [172.20.0.5, 172.20.1.5, 172.20.2.5]

submitter:
  delay: 10  # Submit flags 10 seconds after the beginning of each tick
  run_every_nth_tick: 3  # If flags stay valid for multiple ticks (e.g. 3), you can submit on every 3rd tick instead (default: 1)
  module: submitter  # Submitter module name (default: submitter)

server:
  host: 0.0.0.0  # Accept connections from any network interface or IP address
  port: 2023  # Run Fast server on port 2023
  password: letmein  # Optionally add a password for basic auth
```

2. In the same directory, create a submitter script. If you did not specify `module` in `server.yaml`, name it `submitter.py`. Otherwise, name it to match your custom module name. To work properly with Fast, submitter should follow this [submitter script guideline](#submitter-script-guideline).

3. Run server.

```
server
```

That's it. Fast server will be ready to receive the flags and submit them automatically.

### Setup client 🤖

1. After installing Fast on a player machine, navigate to the directory containing your exploit scripts. Directory structure may look like this, and exploits should follow this [simple guideline](#exploit-script-guidelines).

```
myexploits/
├── alpha.py
├── bravo.py
├── charlie.py
├── delta.rs
├── echo.py
├── foxtrot.py
└── golf.sh
```

2. In the same directory, create a file named `fast.yaml`. This file will contain configuration for the server connection, your exploits and their target IPs. The following example covers everything you can do with Fast for now.

```yaml
connect:
  host: 192.168.1.49  # IP address of the machine that is running Fast server
  port: 2023
  player: s4ndu  # Your username to identify your actions in logs
  password: letmein  # If the server has a password, use it here

exploits:
  # IP addresses can be listed individually, and IP ranges can be expressed using hyphens
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

  # Non-Python exploit can be ran by running a custom shell command
  - name: delta
    cmd: ./delta [ip]
    targets:
      - 172.20.0.2-11

  # Environment variables can be set
  - name: echo
    env:
      KEY: 26fc75b98472
      WEBHOOK: https://webhook.site/00d8f0b7-6084-4aa0-8b59-a728ae2be450
    targets:
      - 172.20.0.2-11

  # Spikes in CPU and network usage in each tick? Arrange exploits by setting a delay
  - name: foxtrot
    delay: 5
    targets:
      - 172.20.0.2-11
```

3. Run client.

```sh
fast
```

Your exploits will now be executed during each tick. At the beginning of a tick, Fast will check if there were any changes in your exploit configuration and apply them.

### Exploit Script Guideline

#### Python scripts 🐍

To work properly with Fast, your script should have a function named `exploit` that takes the target's IP address as the only parameter, and returns the flag (or some text containing the flag) as a string. That's about it.

Here is a very basic example of how an exploit script should be structured:

```python
import requests

def exploit(target):
    return requests.get(f"http://{target}:5000/flag").text
```

#### Other scripts 🦀💲☕

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

### fire

When you add a new exploit to the `fast.yml` file, it will be loaded and executed during the next tick. However, if you do not want to wait and prefer to get the flags right away, you can run the exploits immediately by running `fire <exploit names>`.

### submit

In a similar manner to the `fire` command, you can also trigger flag submission by running `submit`. 

This command can be useful in combination with `fire`. For instance:

```bash
fire alpha bravo && submit
```

Executing this command will run the specified exploits and tell the server to submit all the flags in the queue, without waiting for the next tick.


## Planned features and goals

- [ ] Web dashboard for monitoring. (WIP)
- [ ] Easy exploit health monitoring on dashboard.
- [ ] Handle connection failure with the server and provide a fallback for keeping the flags locally.
- [ ] Guarantee that every non-duplicate retrieved flag will be submitted.
- [ ] Verbose flag history (track OLD, DUP, etc.)
- [ ] Support HTTPS to prevent packet sniffing for flags
- [ ] Optional centralized client integrated with git repository.
- [x] Validate configs when starting.
- [x] Make some client configuration (e.g. `connect`) immutable after starting.
- [x] Synchronizing clients with the server.
- [x] Restrict malicious actors from accessing the server (basic auth).
