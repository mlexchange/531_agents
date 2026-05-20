# bl531

bl531 - Osprey Agent Application
An AI agent built with the Osprey framework to automate experimental procedures and data handling at Beamline 5.3.1 by interacting with the queue server and Tiled data server.
mock mode is available for test if the agent isn't in the beamline computer

## Quick Start

```bash
# 1) Clone the repository and enter it
git clone <repo-url>
cd 531_agents

# 2) Install uv (if needed) and create a Python 3.11 virtual environment
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11
source .venv/bin/activate

# 3) Install the package with development dependencies
uv pip install -e ".[dev]"

# 3.1) Re-activate environment (recommended on some systems)
source .venv/bin/activate

# 4) Copy environment template
cp .env.example .env

# 5) Add your language-model API key(s) to .env (at least one required)
# Example:
# OPENAI_API_KEY=your-openai-key

# 6) Start the command line chat interface
osprey chat
```

Example prompt:

```text
help me to do xanes 30eV 1eV step around Fe edge
```

In mock mode (for Tiled server and beamline), the AI will ask for your approval before running the scan. If you approve, a mock scan is performed.

Supported API keys in `.env`:

```env
# API key for language model access
ANTHROPIC_API_KEY=your-anthropic-key      # Recommended: Claude Haiku 4.5
CBORG_API_KEY=your-cborg-key             # LBNL institutional provider
AMSC_I2_API_KEY=your-amsc-key             # American Science Cloud
STANFORD_API_KEY=your-stanford-key        # Stanford AI Playground
OPENAI_API_KEY=your-openai-key            # OpenAI GPT models
GOOGLE_API_KEY=your-google-key            # Google Gemini models
```

## Project Structure

```
<!-- TREE START -->
<pre>
.
├── README.md
├── requirements.txt
├── pyproject.toml
├── config.yml
├── src/
│   └── bl531/
│       ├── bl531_api.py
│       ├── bl531_data_api.py
│       ├── context_classes.py
│       ├── registry.py
│       ├── INTEGRATION_GUIDE.md
│       ├── README.md
│       └── capabilities/
├── scripts/
│   └── update_readme_tree.py
├── services/
│   ├── docker-compose.yml.j2
│   ├── jupyter/
│   ├── open-webui/
│   └── pipelines/
├── mkdocs/
├── _tests/
└── Dockerfile
</pre>
<!-- TREE END -->
```
## Development

Capabilities are implemented in `src/bl531/capabilities/`:

* **`count_capability.py`**: Get beam intensity/readback values.
* **`move_capability.py`**: Move a motor to a specified position.
* **`diode_alignment_capability.py`**: Grid-scan the diode and find beam position.
* **`retrieve_data_capability.py`**: Retrieve run data from the Tiled server by UID.
* **`gisaxs_alignment_capability.py`**: Align the sample for GISAXS experiments.
* **`scan_capability.py`**: Execute a scan workflow (scan → retrieve → format) with approval flow.
* **`xray_edge_capability.py`**: Look up X-ray absorption edge energies (K/L/M) for elements (with Henke verification).

## Documentation for AI-agent osprey

- Framework: https://als-apg.github.io/osprey
- Tutorial: [Building Your First Capability](https://als-apg.github.io/osprey/developer-guides/building-first-capability.html)

## Copyright Notice

MLExchange Copyright (c) 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software, please contact Berkeley Lab's Intellectual Property Office at IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department of Energy and the U.S. Government consequently retains certain rights.  As such, the U.S. Government has been granted for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform publicly and display publicly, and to permit others to do so.
