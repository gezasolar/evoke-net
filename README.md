# Evoke Net

Pilot onboarding for a distributed GPU-compute network. Evoke nodes contribute only through an explicitly configured local renderer; the network never sends executable code to a node.

## Pilot status

- Node client: `v0.1.1` pre-release. Its source is included in this repository for review.
- Rewards and transfers are **disabled** while the pilot validates reliability, abuse controls, and workload demand. Regla Alfa requires separate live credentials, an explicit enablement flag, and individual admin approval before any transfer.
- Do not run a node while gaming or doing latency-sensitive work.

## Install the node client

Requires Python 3.10 or later.

```bash
pip install https://github.com/gezasolar/evoke-net/releases/download/v0.1.1/evokenet_node-0.1.1-py3-none-any.whl
```

Obtain a pilot join code at [evoke.tbbw.net](https://evoke.tbbw.net/), then:

```bash
evokenet activate EVK-XXXXXX
evokenet renderer '/path/to/your-local-renderer'
evokenet run --enable
```

The client starts paused. The renderer command is chosen locally by the node operator, receives job JSON on standard input, and must write its final PNG/JPEG to `EVOKE_OUTPUT_PATH`.

### Guided local ComfyUI option

For a more direct pilot setup, install and run [ComfyUI](https://github.com/comfyanonymous/ComfyUI) locally with a checkpoint you have already installed, then configure its filename:

```bash
evokenet comfyui --checkpoint YOUR_CHECKPOINT.safetensors
evokenet run --enable
```

The adapter uses only the local ComfyUI server at `http://127.0.0.1:8188` by default. It builds a fixed image workflow locally; it does not expose ComfyUI to the internet, download models, or execute code delivered by Evoke.

## Security principles

- Tokens are stored only on the node and sent over HTTPS to authenticate the node.
- Results are checked for file integrity, dimensions, uniqueness, and spot checks.
- No private application code, customer data, or live payout credentials are published here.

## Links

- [Pilot release v0.1.1](https://github.com/gezasolar/evoke-net/releases/tag/v0.1.1)
- [Evoke Net](https://evoke.tbbw.net/)
- [Terms](https://evoke.tbbw.net/legal/terminos.html) · [Privacy](https://evoke.tbbw.net/legal/privacidad.html)
