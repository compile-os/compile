# Contributing to Compile

We welcome contributions. This project exists because others shared their work openly, and we intend to do the same.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment (see below)
4. Create a branch for your work
5. Make your changes
6. Submit a pull request

## Development Setup

### ML / Research (Python)

```bash
cd latent/ml
python -m venv .venv && source .venv/activate
pip install -e ".[dev]"
make verify  # runs lint + tests
```

Experiments require FlyWire connectome data. See `latent/ml/DATA.md` for download instructions.

### Frontend (Next.js)

```bash
cd latent/frontend
npm install
npm run dev
```

### Backend (Go)

```bash
cd latent/backend
cp .env.example .env
go run cmd/api/main.go
```

### Full Stack (Docker)

```bash
cd latent/infrastructure/docker
docker compose up -d
```

## What to Contribute

- **New experiments**: Run the pipeline on new connectomes or behaviors
- **Growth program improvements**: Better sequential growth strategies
- **Frontend**: Visualization improvements, accessibility, mobile
- **Bug fixes**: If you find something broken, fix it
- **Documentation**: Clarify methodology, add examples

## Pull Requests

- Keep PRs focused on a single change
- Include a clear description of what and why
- Add tests for new functionality where possible
- Run `make verify` (Python) or `npm run build` (frontend) before submitting

## Code Style

- Python: We use `ruff` for formatting and linting
- TypeScript: ESLint with Next.js config
- Go: Standard `gofmt`

## Reporting Issues

Use GitHub Issues. Include:
- What you expected
- What happened
- Steps to reproduce
- Environment (OS, Python/Node version)

## AI-Assisted Review

We use an AI agent to review incoming pull requests. It will merge reasonable contributions automatically. If your PR isn't merged within a few days, a human will review it.

## License

By contributing, you agree that your contributions will be licensed under the same CC BY-NC 4.0 license as the project.
