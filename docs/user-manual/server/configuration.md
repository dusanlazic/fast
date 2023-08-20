# Fast Server Configuration

Server configuration is stored inside a YAML file named `server.yaml`. Fast looks for the configuration file within the current working directory. This allows having multiple separate configurations and environments for different competitions.

The `server.yaml` file is composed of multiple sections, each used for configuring different aspects of the tool. These sections are described in detail below.

## Game Settings <small>required</small> { #game-settings data-toc-label="Game Settings" }

The `game` section includes game-related settings that should match the competition's requirements and your team's properties within the competition. This configuration is retrieved by the clients, allowing them to extract flags based on the flag format and synchronize the attacks with the server's tick timing. This way you have to configure only the server, while the clients will automatically configure themselves upon connecting.

### Examples

*a. Complete configuration*

```yaml
game:
  tick_duration: 80
  flag_format: ENO[A-Za-z0-9+\/=]{48}
  team_ip: 10.1.26.1
```

??? example "About the Example"

    Exploits will reload and rerun every 80 seconds, flags will be collected using the given regex, and alerts will appear on the dashboard each time an exploit retrieves a flag from your own service (target `10.1.26.1`).

### Options

The section starts with the keyword `game:` placed anywhere at the root level of the file.

`tick_duration` <small>required</small>

:   Tick duration in seconds. The duration is given by the competition organizers.

`flag_format` <small>required</small>

:   Regex pattern for flag matching. The pattern is given by the competition organizers. Knowing the pattern allows the clients to extract flags from exploit scripts' return values.

`team_ip` <small>required</small>

:   Your team's IP address. Fast will not submit flags originating from this IP. Instead, it will trigger an alert on the dashboard indicating that your exploit affects your own service and immediate patching is required.

    To specify multiple IP addresses (e.g. for Ubuntu, Fedora and Windows machines), use a list like `[10.1.26.1, 10.1.26.2, 10.1.26.3]`.

## Submitter <small>required</small> { #submitter data-toc-label="Submitter" }

The `submitter` section is used for configuring the delay and optionally the module used for flag submission. The submitter module (default `submitter.py`) must be placed in the current working directory. For more details on writing this module, read the [Submitter Guideline](submitter-guideline.md).

### Examples

*a. Minimal*

```yaml
submitter:
  delay: 20
```

??? example "About the Example"

    Flags will be submitted 20 seconds after the beginning of each tick using the `submitter.py` script placed in the same directory.

*b. Setting a custom module name*

```yaml
submitter:
  delay: 20
  module: ecsc_submitter_v2
```

??? example "About the Example"

    Flags will be submitted 20 seconds after the beginning of each tick using the `ecsc_submitter_v2.py` script placed in the same directory.


### Options

The section starts with the keyword `submitter:` placed anywhere at the root level of the file.

`delay` <small>required</small>

:   Number of seconds to wait before submitting the flags. The time is relative to the beginning of the tick.
    
    !!! hint
    
        Choose a value based on the estimated time it takes for all your exploits to complete. Try not to submit too early or too late.

`module` <small>default = `submitter`</small>

:   Custom name of your submitter module. Omit this field if your submitter module is named `submitter.py`; otherwise, name it to match its module name (without *.py* extension).

## Server

The `server` section is used for configuring the gevent server Fast runs on. That includes configuring the host, port, and the password.

These settings must be shared with everyone on the team running Fast clients, allowing them to configure the necessary [connection parameters](../client/configuration.md#connecting).

Omitting this section results in using the default settings, making the server available on port `2023` with no password required.

### Examples

*a. Running on a custom port and setting the HTTP Basic Auth password*

```yaml
server:
  port: 80
  password: Noflags4you!
```

??? example "About the Example"

    Fast server will run on the port 80 and will require a password for connecting and accessing the web dashboard.

### Options

The section starts with the keyword `server:` placed anywhere at the root level of the file.

`host` <small>default = `0.0.0.0`</small>

:   Host address on which the server will run. By default, it will listen on all available network interfaces.

`port` <small>default = `2023`</small>

:   Port number on which the server will accept connections. Default is `2023`.

`password` <small>default = `None`</small>

:   Enables HTTP Basic Authentication and sets the password for Fast clients and web dashboard. Omit this field to disable password authentication.
    It's highly recommended to set a password to deter unauthorized access, especially if your server is publicly accessible (e.g. running on a VPS).

## Database Connection

The `database` section is used for configuring the parameters for connecting to the Postgres database used for storing flags. This includes the database **name**, **user**, **password**, **host**, and **port**. 

Omitting this section results in using the default values, making Fast connect to a database named `fast` on `localhost:5432` with the credentials `admin:admin`. 

You can execute the following command to spin up a "default" database locally using Docker:

```sh
docker pull postgres:alpine && docker run --name "fast_database_container" -e POSTGRES_DB="fast" -e POSTGRES_USER="admin" -e POSTGRES_PASSWORD="admin" -p 5432:5432 -d postgres
```

You can use the same command to run Postgres Docker image with different variables. The database may be hosted on the same machine or on a separate server, depending on your preference and setup requirements.

### Examples

*a. Setting database name and credentials*

```yaml
database:
  name: fast_db_2023
  user: cyberhero
  password: zU189&63!Ixq
```

??? example "About the Example"

    Fast server will connect to a database named `fast_db_2023` running on `localhost` at port `5432`, with the credentials `cyberhero:zU189&63!Ixq`.

### Options

The section starts with the keyword `database:` placed anywhere at the root level of the file.

`name` <small>default = `fast`</small>
:   Name of the database.

`user` <small>default = `admin`</small>
:   Username for authenticating with the database.

`password` <small>default = `admin`</small>
:   Password for authenticating with the database.

`host` <small>default = `localhost`</small>
:   Host address of the database server. By default, Fast will connect to a database running on localhost.

`port` <small>default = `5432`</small>
:   Port number on which the database server is listening. Default is `5432`, same as the Postgres default.

