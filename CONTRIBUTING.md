# Contributing

## Clone the repository

```bash
git clone https://github.com/ConnorC432/ue4ss_modmanager.git
```

### Running Tests

To run the tests with detailed output:

```bash
PYTHONPATH=. pytest -v
```

To check code coverage:

```bash
PYTHONPATH=. pytest --cov=src tests/
```

### Linting

This project uses `ruff` for linting and formatting. To check for linting issues:

```bash
ruff check .
```

To format the code:

```bash
ruff format .
```