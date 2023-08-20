<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.css">

This quickstart guide outlines the minimal steps to get Fast up and running. This includes setting up the database, writing the submitter module, configuring and running a Fast server, configuring a Fast client and running a single exploit.

If you are in a competition and your teammate has already configured and launched the server, you can skip to [Setting up Fast Client](#setting-up-fast-client).

## Setting up Fast Server

### 1. Setup Postgres

The quickest way of setting up a Postgres database is using Docker. Execute the following command on your submitter-dedicated machine to establish a database that works with the default Fast configuration:

```sh
docker pull postgres:alpine && docker run --name "fastdb" -e POSTGRES_DB="fast" -e POSTGRES_USER="admin" -e POSTGRES_PASSWORD="admin" -p 5432:5432 -d postgres
```

!!! note

    You can find detailed instructions on configuring the database connection in the [User Manual](user-manual/server/configuration.md#database-connection).

### 2. Configure Fast Server

After [installing Fast](index.md) on your submitter-dedicated machine, navigate to an empty directory and create a file named `server.yaml`. An example minimal configuration is as follows:

```yaml
game:
  tick_duration: 80
  flag_format: ENO[A-Za-z0-9+\/=]{48}
  team_ip: 10.1.26.1

submitter:
  delay: 20
```

Change the tick duration, flag format (regex pattern) and your vulnbox IP to match your competition requirements. Submitter delay is set to 20 seconds, meaning that flag submission will run 20 seconds after the start of each tick. Feel free to change this value.

By default, the server runs on host `0.0.0.0`, port `2023`, without a password, and connects to the database set up in the previous step.

!!! note

    Advanced configuration and every YAML section (`game`, `submitter`, `server` and `database`) is described in detail in the [User Manual](user-manual/server/configuration.md).

### 3. Write the Submitter Module

In the same diretory, create a file named `submitter.py`. This will be a script that does the actual flag submission. To work properly with Fast, it should follow this simple guideline:

The submitter script must define a function named `submit` that takes a list of flags (as string values) ready for submission. The `submit` function submits the flags and returns the responses from the flag-checking service as a tuple of two dictionaries: the first dictionary for the accepted flags and the other one for the rejected ones. The keys of the dictionaries are the flags, and the values are the corresponding responses from the flag-checking service.

You can adapt the submit function to work with various flag submission mechanisms, such as submitting through a REST API, or over a raw TCP connection. See below for the examples.

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

For a detailed guide on writing exploits, refer to the [Submitter Guideline](user-manual/server/submitter-guideline.md).

### 4. Run

In the same directory, run `server` command.

<div id="server-quickstart-demo"></div>
<script>
  AsciinemaPlayer.create('/fast/assets/demos/server-no-clients.cast', document.getElementById('server-quickstart-demo'), {
      cols: 90,
      rows: 15,
      idleTimeLimit: 2
  });
</script>



Fast is now ready to receive and submit the flags. By default, Fast server is available on all network interfaces (that includes your local network and your team's VPN) at the port `2023`.

To access the dashboard, navigate to [http://localhost:2023](http://localhost:2023) in your web browser. Your teammates will have to use your machine's IP, which may be the one on your team's local network or the public IP if you are running on a VPS.

!!! warning "If you are running on a VPS"

    Ensure that your instance is allowed to listen on port `2023` (or the one that you specified), and that you can connect to the competition's VPN and reach the flag checking service from the VPS. If the limited number of VPN connections is a problem, [try this](troubleshooting.md#addressing-limited-number-of-vpn-connections).
    
    Also, it's highly recommended to set a password to deter unauthorized access. To set the password, add the following to your `server.yaml` file:

    ```yaml
    server:
      password: <custom password>
    ```

## Setting up Fast Client

### 1. Connect with the Server

After [installing Fast](index.md) on your own (player) machine, navigate to an empty directory and create a file named `fast.yaml`. 

The following starter configuration is used for connecting to a Fast server running on host `192.168.13.37` and port `2023`. Replace those with the agreed values. Also, change the player name so Fast can distinguish your exploits from those of your teammates.

```yaml
connect:
  host: 192.168.13.37
  port: 2023
  player: yourname

exploits: # no exploits yet
```

Although there are no exploits yet, the configuration above is sufficient for launching Fast client. 

You can test the connection by running `fast` in your terminal from the same directory. If everything is OK, the client will start, synchronize with the server, and wait for the exploits. Fast will also alert you that the `exploits` section is empty, but you can ignore that for now.

<div id="client-quickstart-demo"></div>
<script>
  AsciinemaPlayer.create('/fast/assets/demos/client-no-exploits.cast', document.getElementById('client-quickstart-demo'), {
      cols: 100,
      rows: 20,
      idleTimeLimit: 2
  });
</script>

### 2. Write Exploits

When managed by Fast, exploit scripts must adhere to a simple guideline to ensure compatibility.

**Python Scripts:** Python exploit scripts should define a function named `exploit`, taking the target's IP address as the sole parameter. This function must return a text containing one or multiple flags. That's about it, here's a minimal example:

```py
import requests

def exploit(target):
    return requests.get(f'http://{target}:1234/flag').text
```

**Non-Python Scripts:** If you're using non-Python scripts, ensure that the target's IP address can be passed as a command-line argument. The script should only output the text containing one or multiple flags to the standard output (stdout). Here's an example using a Bash script:

```bash
#!/bin/bash
curl -s "http://$1:1234/flag"
```

Scripts must be placed in the same directory as `fast.yaml`. Directory may look like this:

```
exploits/
├── alpha.py
├── bravo.py
├── charlie.sh
└── fast.yaml
```

For more details on writing the exploits, refer to the [Exploit Guideline](user-manual/client/exploit-guideline.md).

### 3. Manage Exploits

Once you've written the exploits and stored them in the directory, add them to the `exploits` section of `fast.yaml`.

Here's the same configuration extended with two example Python scripts and a Bash script:

```yaml
connect:
  host: 192.168.13.37
  port: 2023
  player: yourname

exploits:
  - name: alpha
    targets:
      - 10.1.2-11.1
  
  - name: bravo
    targets:
      - 10.1.2.1
      - 10.1.6.1
      - 10.1.8-11.1
  
  - name: charlie
    run: ./charlie.sh [ip]
    targets:
      - 10.1.2-11.1
```

With this configuration, exploits `alpha.py`, `bravo.py` and `charlie.sh` will be ran on the specified range of targets at the beginning of each tick. Every exploit will be ran and every target will be attacked at the same time.

Any modifications made to the `exploits` section are automatically applied at the beginning of the next tick, ensuring a seamless integration with ongoing game activities.

!!! note

    If you are running an executable file directly (e.g., `./charlie.sh [ip]`), ensure that you have set the execute permission, and you have added an appropriate shebang line (`#!/bin/sh` or similar) or it's a binary file (e.g., `./rust_exploit [ip]`).

### 4. Run

Run `fast` command from the same directory.

Fast client will connect and synchronize with the server. Your exploits will be executed during each tick with the settings specified in your `fast.yaml`.

## Next Steps

You have now successfully completed the Quickstart guide and set up a basic configuration for Fast. For more advanced usage and detailed instructions on how to use Fast effectively during a competition, refer to the sections of the User Manual: [Server](user-manual/server/overview.md), [Dashboard](user-manual/dashboard/overview.md) and [Client](user-manual/client/overview.md),
