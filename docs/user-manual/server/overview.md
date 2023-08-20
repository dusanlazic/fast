# Fast Server Overview

``` mermaid
    graph LR

        targets["Opponents'<br/>services"]
        targets --> aliceExploits[Alice's exploits]
        targets --> bobExploits[Bob's exploits]
        targets --> carolExploits[Carol's exploits]

        subgraph "Alice's machine"
            aliceExploits --> client1[Alice's client]
        end

        subgraph "Bob's machine"
            bobExploits --> client2[Bob's client]
        end

        subgraph "Carol's machine"
            carolExploits --> client3[Carol's client]
        end

        client1 -->|extracts &<br/>forwards flags| server[Fast server]
        client2 -->|extracts &<br/>forwards flags| server
        client3 -->|extracts &<br/>forwards flags| server

        server -->|submits| flagService[Flag-checking service]
```


Fast server is responsible for collecting and submitting flags, filtering out duplicates, providing useful insights through the dashboard, and keeping all the connected clients in sync. It's designed to operate under heavy load conditions and implements measures for quick and easy recovery if anything goes wrong.

This section provides instructions for [configuring the Fast server](configuration.md) and [writing the submitter](submitter-guideline.md). It includes real-world examples and details every option in the configuration YAML. You can use this documentation both as a guide during setup and as a reference in a competition.