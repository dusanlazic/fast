# Fast Client Configuration

<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.css">

Client configuration is managed using a YAML file named `fast.yaml`. Fast looks for the configuration file and exploit scripts in the current working directory. This allows having multiple separate configurations and environments for different competitions.

The `fast.yaml` file is composed of two sections, one for configuring the connection with the server, and one for exploit management. This page focuses on the first section. If you are looking for exploit management, see [Exploit Management](exploit-management.md) page.

## Connecting

To setup Fast client for connecting to the server, you need to specify your server's **host**, **port**, **password** (if required), and your custom **username**.

Some starter `fast.yaml` configurations with no managed exploits are shown below:

### Examples

=== "Minimum Team Config"

    ```yaml
    connect:
      host: 192.168.13.37
      player: john

    exploits:
    ```


=== "Customized Port"

    ```yaml
    connect:
      host: 192.168.13.37
      port: 80
      player: john

    exploits:
    ```

=== "Password Auth"

    ```yaml
    connect:
      host: 192.168.13.37
      password: Noflags4you!
      player: john

    exploits:
    ```

=== "Public Server"

    ```yaml
    connect:
      host: fast.example.com
      password: Noflags4you!
      player: john

    exploits:
    ```

=== "Single Player"

    ```yaml
    # Omit to connect to localhost:2023 with no password

    exploits:
    ```

Although the shown examples have no managed exploits, every given configuration is sufficient for launching the client.

You can test the connection by running `fast` in your terminal from the same directory. If everything is OK, the client will start, synchronize with the server, and wait for exploits. 

<div id="client-no-exploits-demo"></div>
<script>
  AsciinemaPlayer.create('/fast/assets/demos/client-no-exploits.cast', document.getElementById('client-no-exploits-demo'), {
      cols: 100,
      rows: 20,
      idleTimeLimit: 2
  });
</script>

### Options

This section starts with the keyword `connect:` placed anywhere at the root level of the file.

`host` <small>default = `localhost`</small>
:   Host address of the Fast server. By default, client will connect to a Fast server running on localhost.

`port` <small>default = `2023`</small>
:   Port number on which the Fast server is listening. Default is `2023`.

`player` <small>default = `anon`</small>
:   Your name or alias to help Fast distinguish your exploits from those of your teammates.

`password` <small>default = `None`</small>
:   Password for authenticating with the Fast server.

## Next Steps

To learn how to start running and managing exploits, read the [Exploit Guideline](exploit-guideline.md) and then continue to [Exploit Management](exploit-management.md).