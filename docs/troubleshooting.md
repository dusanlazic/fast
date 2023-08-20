## Addressing limited number of VPN connections

If you are running the Fast server on a Virtual Private Server (VPS), you might run into issues with reaching the competition infrastructure, such as the flag-checking service essential for flag submission. Event organizers may restrict the number of VPN connections to match the team size, leaving no room for connecting another machine such as your VPS.

To address this, you can establish an SSH tunnel, enabling the VPS to route traffic to the flag-checking service using your local machine as a relay.

```bash
ssh -i /path/to/your/ssh-key.pem -L 5000:10.10.13.37:1337 admin@fast.example.com
```

=== "Direct Access"

    ```python
    r = remote('10.10.13.37', 1337)

    requests.post('http://10.10.13.37:1337/flags', json=flags)
    ```

=== "Via SSH Tunnel"

    ```python
    r = remote('localhost', 5000)

    requests.post('http://localhost:5000/flags', json=flags)
    ```

In the example scenario above, the flag-checking service is available over the VPN at `10.10.13.37:1337`. 

By setting up an SSH tunnel, traffic directed to `localhost:5000` on the VPS is forwarded to `10.10.13.37:1337`. This tunneling ensures bidirectional communication, allowing both sending flags and receiving the responses.