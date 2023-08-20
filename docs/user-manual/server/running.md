# Running Fast Server

<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.css">

Before running Fast server, ensure the following:

- [x] **Server is configured**: You have [configured the server](../server/configuration.md) and the configuration file (`server.yaml`) is located in your current working directory.
- [x] **Submitter module is written**: You have written the submitter module according to the [Submitter Guideline](submitter-guideline.md) and it's located in your current working directory.

To run the server, just run the command `server`.

<div id="server-running-demo"></div>
<script>
  AsciinemaPlayer.create('/fast/assets/demos/server.cast', document.getElementById('server-running-demo'), {
      cols: 129,
      rows: 25,
      idleTimeLimit: 2
  });
</script>

The Fast server is now ready to receive and submit flags. 

To access the dashboard, navigate to [http://localhost:2023](http://localhost:2023) in your web browser. Your teammates will have to use your machine's IP, which may be the one on your team's local network or the public IP if you are running on a VPS. Verify with your teammates that they can access the dashboard with no issues.
