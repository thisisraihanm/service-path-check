# Service Path Check

## Open it without commands (Windows)

[**Download the Windows app**](https://github.com/thisisraihanm/service-path-check/releases/latest) → download **ServicePathCheck-Windows.zip** under Assets → **Extract All** → double-click **ServicePathCheck.exe**. Python is included.

Click **Try a safe example** first. Then Type or paste a website address, then click **Check connection**. For an office file server, select **Windows file server** and enter the name provided by IT.

[Step-by-step beginner guide](../START-HERE.md). The screen and report explain the result in plain language. Detailed evidence remains available for IT.

If you downloaded source code with **Code → Download ZIP**, Python 3.11+ with Tk is required; double-click **Start-Windows.cmd** after installing it.


**Find where a configured service connection fails: DNS, TCP, or verified TLS.**

A user says the portal is unavailable. Ping replies, so the ticket gets passed around. This tool checks the path the service actually uses and saves evidence for the next person investigating.

It checks every resolved address up to an explicit limit, preserves failed samples, and separates observation from diagnosis. A TCP timeout can justify checking routing, listeners, and policy; it cannot prove a firewall is the cause.

## Try the offline demo

Requires Python 3.11 or newer. No pip packages. Run from this repository directory:

```sh
python service_path_check.py --demo
```

Open `reports/service-path.html` in your browser. The JSON beside it contains the evidence. The demo uses fictional data, sends no network traffic, and exits **1** because it intentionally shows problems.

[Included fictional example report](demo-report.html)

## Check an authorized service

Copy `examples/services.example.json` to `services.local.json`. Replace the fictional hostnames with the exact services you are authorized to check:

```json
{
  "timeout": 3,
  "samples": 3,
  "services": [
    {"name": "Lab portal", "host": "portal.example.test", "port": 443, "tls": true},
    {"name": "Lab file service", "host": "files.example.test", "port": 445, "tls": false}
  ]
}
```

```sh
python service_path_check.py --config services.local.json --output reports/morning-check
```

These `.test` names are placeholders. There is no subnet scan or automatic device discovery. Only configured endpoints receive TCP connections and, when requested, TLS handshakes. No HTTP requests, login attempts, or file-service operations are sent.

For an internal certificate authority, add `"ca_file": "lab-ca.pem"` to the configuration. The path is resolved relative to the configuration file. Supply a PEM CA certificate, never a private key. Certificate chain and hostname verification stay enabled.

Run the tool from the affected user's network/VPN context: a check from another machine may see a different DNS answer or route.

## Read the result

| Observation | Meaning | Useful next step |
|---|---|---|
| DNS fails or reaches its deadline | This machine did not obtain usable addresses | Check spelling, resolver settings, and VPN context |
| DNS passes; TCP fails | The configured service port could not be reached on that address | Check route, service listener, and firewall evidence |
| TCP passes; TLS fails | A socket connected, but a verified TLS session failed | Check certificate name, expiry, trust chain, clock, and protocol |
| Some addresses/samples pass | Path is inconsistent | Compare failing addresses and timestamps with infrastructure logs |
| All requested stages pass | The observed service path worked during these checks | Test application function, permissions, and authentication separately |

A non-TLS service can pass DNS and TCP only. That does not confirm SMB access or application functionality. Port 587 with STARTTLS, for example, needs protocol negotiation and must not be treated as direct TLS by this tool.

## Design and limits

- DNS uses the operating system resolver, including its cache and hosts file. It does not query each configured upstream DNS server separately.
- A short-lived child process bounds DNS resolution time. Socket timeouts alone do not bound `getaddrinfo()` reliably.
- Every selected address gets a TCP attempt. TLS uses the intended hostname for SNI and validation. A failing address prevents an all-green service result.
- At most eight addresses per sample are checked. Larger answers are explicitly marked incomplete for a full pass.
- The timeout is **per DNS/TCP/TLS stage**, not for the whole run. Checks and samples run sequentially. A large configuration with failing endpoints can take several minutes.
- Samples run consecutively. They are snapshots, not long-term availability statistics; TCP timing excludes DNS and is not ping RTT.
- Trust uses Python's default TLS context or your supplied CA bundle. Revocation checking and application authentication are outside this tool's scope.
- Reports can reveal internal endpoints. Local config and report folders are ignored by Git, but inspect changes before committing.

## Validate and learn

```sh
python -m unittest discover -s tests -v
```

Tests include real loopback connections, refused ports, mixed addresses, DNS deadlines, intermittent samples, and HTML escaping. The optional real TLS test generates a temporary localhost certificate using an installed OpenSSL executable; it checks trust and hostname failures without contacting the internet.

See [WALKTHROUGH.md](../WALKTHROUGH.md) for a short lab and how to explain the design. GitHub Actions is configured for Windows/Linux and Python 3.11/3.12; remote execution is only confirmed after its first successful run.

## References

- [Python socket documentation](https://docs.python.org/3/library/socket.html)
- [Python TLS documentation](https://docs.python.org/3/library/ssl.html)

MIT licensed. Initial implementation prepared with AI assistance for Raihan Mahmud's learning portfolio. No production use or performance improvement is claimed.

