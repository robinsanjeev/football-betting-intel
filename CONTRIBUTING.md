# Contributing

Thanks for your interest in contributing to Football Betting Intelligence!

## How to Contribute

### Bug Reports

- Open an [issue](https://github.com/robinsanjeev/football-betting-intel/issues) with:
  - A clear description of the bug
  - Steps to reproduce
  - Expected vs actual behavior
  - Your environment (OS, Python version, Docker version if applicable)

### Feature Requests

- Open an issue with the `enhancement` label
- Describe the feature and why it would be useful
- If possible, suggest an implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test that the API starts and the dashboard loads
5. Commit with a clear message
6. Push and open a PR against `main`

### Code Style

- **Python**: Follow PEP 8. Use type hints where practical.
- **TypeScript/React**: Follow the existing patterns in `web/src/`
- **Tailwind**: Use the existing dark theme color palette (see `web/src/index.css`)

### Development Setup

```bash
# Backend
pip install -r requirements.txt
cp config/config.yaml.example config/config.yaml
# Fill in your API keys
uvicorn football_intel.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd web
npm install
npm run dev
```

### Areas Where Help is Welcome

- **New prediction models** — Elo ratings, xG models, ensemble methods
- **Additional data sources** — more leagues, alternative odds providers
- **UI improvements** — mobile experience, charts, accessibility
- **Testing** — unit tests, integration tests, model backtesting
- **Documentation** — tutorials, examples, translations

## Code of Conduct

Please be respectful and constructive in all interactions. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions?

Open a discussion or issue — happy to help.
