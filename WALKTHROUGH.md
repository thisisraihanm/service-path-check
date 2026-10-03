# Learn and demonstrate it

## A 20-minute lab

1. Run the offline demo and read the full evidence in the HTML report. Explain why a TLS failure can happen after TCP succeeds.
2. Start a disposable local HTTP service in another terminal: `python -m http.server 8765 --bind 127.0.0.1`. Serve an empty lab folder, not a directory with private files.
3. Create `services.local.json` with one service: `{"services":[{"name":"Local lab","host":"127.0.0.1","port":8765,"tls":false}]}`.
4. Run the tool. DNS and TCP should pass. No HTTP request is made, so there is no evidence yet that the page actually works.
5. Stop the HTTP service with Ctrl+C and rerun. Resolution should still work; the TCP path should fail.
6. Explain the difference between the two reports without saying the host is down.

## Read the implementation in this order

`validate_config()` restricts explicit targets and limits. `resolve()` enforces an OS-resolver deadline using a child process. `check_service()` preserves per-address TCP/TLS results. `run()` summarizes multiple samples without hiding failures. `report.py` renders escaped local evidence.

The real-TLS test creates a temporary certificate and checks trusted, wrong-hostname, and untrusted cases. Do not copy a test trust setting into production without an approved CA.

## Explain your work honestly

“I worked on a local service-path diagnostic that distinguishes DNS, TCP, and TLS observations. It preserves mixed-address and intermittent failures and gives evidence for escalation. I used loopback tests and fictional demos; I still need to validate it in an authorized workplace pilot.”

After completing the lab, describe the behavior in your own words. Avoid claiming reduced downtime unless you measure a real before/after result.

## A useful next contribution

Add a separate explicit HTTP check with a small response limit and expected status code. Keep network-path success separate from application success; write a local failure test before adding a green result.
