# 🚩 Fast — Flag Acquisition and Submission Tool

Fast is a Python tool designed to easily manage your exploits and automate submitting flags in A/D competitions. With Fast, writing exploits will be your only concern.

## Installation

To install Fast, follow these steps:

```sh
git clone https://github.com/dusanlazic/fast.git
cd fast
pip install .
```

## Usage

1. Navigate to the directory containing your exploit scripts. Directory structure may look like this, and exploits should follow this [simple guideline](#exploit-script-guidelines).

```
myexploits/
├── alpha.py
├── bravo.py
├── charlie.py
├── delta.py
└── echo.py
```


1. In the same directory, create a file called `fast.yaml`. This file will contain configuration, names of your exploits and their target IPs. IP ranges can be expressed using hyphens. For example:

```yaml
config:
  tick_duration: 60  # Tick duration in seconds

exploits:
  - name: alpha
    targets: 
      - 172.20.0.2-7
  - name: bravo
    targets: 
      - 172.20.0.2
      - 172.20.0.5-7
  - name: charlie
    targets: 
      - 172.20.0.3
  - name: delta
    targets: 
      - 172.20.0.2
      - 172.20.0.5-7
  - name: echo
    targets: 
      - 172.20.0.2-7
```

3. Run fast

```sh
fast
```

## Exploit Script Guideline

Your exploit scripts should follow certain guidelines to work properly with Fast:

1. Each script should have a function named `exploit`.

2. The `exploit` function should take one parameter, `target`, which is the target's IP address.

3. The `exploit` function should return the flag as a string.

Here is a very basic example of how an exploit script should be structured:

```python
import requests

def exploit(target):
    return requests.get(f"http://{target}:8000/flag").text
