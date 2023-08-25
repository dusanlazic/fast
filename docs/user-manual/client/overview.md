# Fast Client Overview

``` mermaid
    graph LR

        client[Fast client] -->|spawns<br/>subprocess| alpha["runner"]
        client[Fast client] -->|spawns<br/>subprocess| bravo["runner"]

        subgraph "Exploit Alpha"
            alpha -->|spawns<br/>thread| alphaThread1["exploit(10.1.2.1)"]
            alpha -->|spawns<br/>thread| alphaThread2["exploit(10.1.3.1)"]
            alpha -->|spawns<br/>thread| alphaThread3["exploit(10.1.4.1)"]
        end

        subgraph "Exploit Bravo"
            bravo -->|spawns<br/>thread| bravoThread1["exploit(10.1.2.1)"]
            bravo -->|spawns<br/>thread| bravoThread2["exploit(10.1.3.1)"]
            bravo -->|spawns<br/>thread| bravoThread3["exploit(10.1.4.1)"]
        end

        subgraph "Opponents'<br/>&nbsp;&nbsp;services"
            target1[10.1.2.1]
            target2[10.1.3.1]
            target3[10.1.4.1]
        end

        alphaThread1 -->|attacks| target1
        alphaThread2 -->|attacks| target2
        alphaThread3 -->|attacks| target3

        bravoThread1 -->|attacks| target1
        bravoThread2 -->|attacks| target2
        bravoThread3 -->|attacks| target3
```

Anyone on the team can run a separate Fast client on their own machine. Each client's primary role is to run the exploits according to the user's specification. Fast provides an intuitive way of configuring using a single YAML file. That includes specifying targets, customizing each exploit's environment, and strategic arrangement of the attacks to ensure optimal CPU, memory and network resource utilization.

The core functionality of Fast is to run the attacks concurrently and independently of each other. If an exploit crashes or timeouts on one target, its execution on the other targets will remain unaffected. This is achieved by using threading library, spawning a separate Python thread for each target. 

Exploits are ran separately as subprocesses. This lets attacks of the same exploit share the same Python interpreter, enabling the use of `prepare` and `cleanup` functions in your exploit code, as well as bypassing the main process's Global Interpreter Lock (GIL).

Additionally, all clients will conform to the flag format specified on the server and synchronize with the server's tick clock, making them remain in sync without any time drifts or offsets.

This documentation section covers [client configuration](configuration.md), [exploit development guideline](exploit-guideline.md), and [exploit management](exploit-management.md). Real-world examples complement each topic. You can use this documentation both as a guide during setup and as a reference in a competition.