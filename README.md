# bl531

bl531 - Osprey Agent Application
An AI agent built with the Osprey framework to automate experimental procedures and data handling at Beamline 5.3.1 by interacting with the queue server and Tiled data server.
mock mode is available for test if the agent isn't in the beamline computer

## Quick Start

```bash
# Install the framework
pip install osprey-framework

# Recommended: Interactive setup (guides you through everything!)
osprey
# Start the command line chat interface
osprey chat
```

## Project Structure

```
bl531
    ├── api_test.py      # Scripts for testing API connections
    ├── BL531API.py      # API wrapper for the Bluesky queue server
    ├── BL531DataAPI.py  # API wrapper for the Tiled data server client
    ├── capabilities/    # Directory for all Osprey agent capabilities
    └── context_classes.py # Data classes for context management
```
## Development

*   **`count_capability.py`**: Get the beam intensity.
*   **`move_capability.py`**: Move a motor to a certain position.
*   **`diode_alignment_capability.py`**: Grid scan the diode and find the beam position.
*   **`retrieve_data_capability.py`**: Retrieve the data from the Tiled server using a UID.
*   **`gisaxs_alignment_capability.py`**: Align the sample for a GISAXS experiment.
*   **`scan_capability.py`**: Capture images or get readings while moving a motor.

## Documentation for AI-agent osprey

- Framework: https://als-apg.github.io/osprey
- Tutorial: [Building Your First Capability](https://als-apg.github.io/osprey/developer-guides/building-first-capability.html)

## Copyright Notice

Osprey Framework Copyright (c) 2025, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software, please contact Berkeley Lab's Intellectual Property Office at IPO@lbl.gov.

NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform publicly and display publicly, and to permit others to do so.
