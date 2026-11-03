# Evoke Net

Pilot onboarding for a distributed GPU-compute network. Evoke nodes contribute only through an explicitly configured local renderer; the network never sends executable code to a node.

## Pilot status

- Node client: `v0.1.0` pre-release.
- Rewards and transfers are **disabled** while the pilot validates reliability, abuse controls, and workload demand. Regla Alfa requires separate live credentials, an explicit enablement flag, and individual admin approval before any transfer.
- Do not run a node while gaming or doing latency-sensitive work.

## Install the node client

Requires Python 3.10 or later.

```bash
pip install https://github.com/gezasolar/evoke-net/releases/download/v0.1.0/evokenet_node-0.1.0-py3-none-any.whl
```

Obtain a pilot join code at [evoke.tbbw.net](https://evoke.tbbw.net/), then:

```bash
evokenet activate EVK-XXXXXX
evokenet renderer '/path/to/your-local-renderer'
evokenet run --enable
```

The client starts paused. The renderer command is chosen locally by the node operator, receives job JSON on standard input, and must write its final PNG/JPEG to `EVOKE_OUTPUT_PATH`.

## Security principles

- Tokens are stored only on the node and sent over HTTPS to authenticate the node.
- Results are checked for file integrity, dimensions, uniqueness, and spot checks.
- No private application code, customer data, or live payout credentials are published here.

## Links

- [Pilot release v0.1.0](https://github.com/gezasolar/evoke-net/releases/tag/v0.1.0)
- [Evoke Net](https://evoke.tbbw.net/)
- [Terms](https://evoke.tbbw.net/legal/terminos.html) · [Privacy](https://evoke.tbbw.net/legal/privacidad.html)
