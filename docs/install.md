Installing Fast is a straightforward process with no need to clone the repo or manually build the frontend. You can install it in your environment using a single pip command.

## Installing via pip <small>recommended</small> { #installing-via-pip data-toc-label="Installing via pip" }

To install the latest release, run the following command.

=== "Linux"

    ```sh
    pip install https://github.com/dusanlazic/fast/archive/refs/tags/1.0.0.tar.gz
    ```

=== "Windows"

    ```powershell
    pip install https://github.com/dusanlazic/fast/archive/refs/tags/1.0.0.zip
    ```

Older versions can be found on the [releases page](https://github.com/dusanlazic/fast/releases) on GitHub.

!!! tip

    It's highly recommended to install Fast within a Python virtual environment. This isolates the dependencies and ensures a clean workspace. To create and activate a new Python virtual environment, run the following command:

    === "Linux"

        ```sh
        python3 -m venv venv && source venv/bin/activate
        ```

    === "Windows"

        ```powershell
        python -m venv venv && .\venv\Scripts\activate
        ```

## Installing From Source

Fast can also be installed directly from its source. This requires building the frontend with `npm`.

```sh
git clone https://github.com/dusanlazic/fast.git
cd fast/web/
npm install
npm run build
cd ../../
pip install -e fast/
```

## Next Steps

Once the installation is complete, two main commands will be accessible from *any* directory on your system:

- `fast`: For running the client, allowing you to manage and run exploits.
- `server`: For running the server, used for flag submission and other server-related tasks.

Before running the client or the server, you will need to configure them using YAML files. Fast will always look for the configuration and other relevant files within the current working directory, allowing you to have multiple separate configurations for different competitions. 

If you are already familiar with the tool, you can move on to [Client Configuration](user-manual/client/configuration.md) if you want to run and manage exploits, or [Server Configuration](user-manual/server/configuration.md) to configure the server.

To get familiar with the basics and get Fast running quickly, continue to [Quickstart](quickstart.md).