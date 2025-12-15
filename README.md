# bl531

bl531 - Osprey Agent Application

## Quick Start

```bash
# API keys were automatically configured from your environment
# Start services
framework deploy up

# Run CLI interface
framework chat
```

## Project Structure

```
bl531/
├── bl531/        # Application code
│   ├── registry.py
│   ├── capabilities/
│   └── context_classes.py
├── services/                  # Docker services
├── config.yml                 # Configuration
└── pyproject.toml            # Dependencies
```

## Development

Edit files in `bl531/` to add functionality. Changes are reflected immediately.

## Documentation

- Framework: https://als-apg.github.io/osprey
- Tutorial: [Building Your First Capability](https://als-apg.github.io/osprey/developer-guides/building-first-capability.html)

