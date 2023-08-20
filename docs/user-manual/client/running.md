<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.css">

Before running Fast client, ensure the following:

- [x] **The server is up**: You or someone on your team has configured and started the server.
- [x] **You can access the dashboard**: Open the dashboard to confirm your machine can access the Fast server. Ask your teammates for host, port, and password.
- [x] **Client is configured**: You have [configured the client](configuration.md) and the configuration file (`fast.yaml`) is located in your current working directory.

To run the client, just run the command `fast`.

<div id="client-running-demo"></div>
<script>
  AsciinemaPlayer.create('/fast/assets/demos/client.cast', document.getElementById('client-running-demo'), {
      cols: 121,
      rows: 25,
      idleTimeLimit: 2
  });
</script>

Fast client will start, connect and synchronize with the server. It will wait for the next tick to begin before it starts running your exploits. You can open the dashboard to monitor the tick clock and wait for your flags to show up.

---

That's it. Good luck and have fun hacking! 🍀