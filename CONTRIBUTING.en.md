# Contributing Guide

English | [简体中文](CONTRIBUTING.md)

Welcome! Please take a few minutes to read the guidelines below to make collaboration smoother.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Environment](#development-environment)
- [How to Contribute](#how-to-contribute)
- [Branching Strategy](#branching-strategy)
- [Commit Convention](#commit-convention)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Reporting Issues](#reporting-issues)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project has adopted the [Contributor Covenant](CODE_OF_CONDUCT.en.md) as its Code of Conduct. All contributors are expected to follow it.

## Development Environment

```bash
# Clone the repository
git clone https://github.com/yansheng836/python-toolbox.git
cd python-toolbox

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py

# Run tests
cd test/ && python -m unittest discover -v
```

## How to Contribute

### 🐛 Reporting Bugs

1. Search [Issues](https://github.com/yansheng836/python-toolbox/issues) first to check for an existing report
2. Submit an issue using the Bug Report template

### 💡 Suggesting Features

1. Search Issues first to check for a similar suggestion
2. Submit an issue using the Feature Request template

### 🔧 Submitting Code

Please follow this workflow:

1. **Research** — search GitHub for existing implementation patterns first; avoid reinventing the wheel
2. **Plan** — for complex features, open an Issue to discuss the design first
3. **Implement** — follow [TDD](https://en.wikipedia.org/wiki/Test-driven_development) practices
4. **PR** — create a Pull Request (see the PR process below)

## Branching Strategy

- `main` — stable branch, always deployable
- `feat/*` — feature branches (e.g. `feat/add-webp-support`)
- `fix/*` — bug-fix branches (e.g. `fix/crash-on-empty-list`)

```bash
git checkout -b feat/my-feature
# ... develop ...
git commit
git push -u origin feat/my-feature
# Create a Pull Request → main
```

## Commit Convention

Commit message format:

```
<type>: <Chinese description>

<optional body>
```

| Type | Description |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Refactoring |
| `docs` | Documentation |
| `test` | Testing |
| `chore` | Build/tooling/dependencies |
| `perf` | Performance optimization |
| `ci` | CI/CD configuration |

Examples:

```
feat: 新增图片缩放百分比模式
fix: 修复空文件列表导致崩溃的问题
docs: 更新 README 安装说明
```

## Code Standards

### Python

- UTF-8 encoding, LF (`\n`) line endings
- Follow PEP 8 style
- Module-level docstring describing the purpose
- Exception handling: catch only where meaningful, always report error info

### PyQt6

- **Colors** — use `Theme` constants; never hardcode color values
- **Text** — use `SelectableLabel` instead of `QLabel` for user-copyable info
- **Layout** — responsive layout; no `addStretch()` at the end of layouts
- **Themes** — every plugin must implement `update_theme()`; test in dark and light themes

### Code Reuse

When identical or similar code appears more than twice, it must be abstracted into a shared component. Shared components live in:

- `common/` — common helper classes and functions
- base classes in `toolbox.py` such as `ToolPlugin`, `Theme`, and `Card`

### Syntax Check

After modifying a Python file, always run:

```bash
python -m py_compile <file.py>
```

## Testing

Test files live in the `test/` directory, named with a `test_` prefix.

```bash
cd test/ && python -m unittest discover -v
```

Create a matching test file when adding a feature.

## Reporting Issues

- Please use the issue templates
- Bug reports must include: reproduction steps, expected behavior, actual behavior, environment
- Feature requests must describe: use case, expected outcome

## Pull Request Process

1. **Fork** this repository and create a feature branch
2. **Write tests** — write tests first, then implement
3. **Implement** — make sure all tests pass
4. **Code review** — check against the [CLAUDE.md](CLAUDE.md) standards
5. **Run tests** — do not break existing functionality
6. **Syntax check** — `python -m py_compile`
7. **Submit the PR** — fill in the description using the PR template

### PR Checklist

- [ ] Code syntax checked (`python -m py_compile`)
- [ ] All tests pass
- [ ] Tested in dark and light themes
- [ ] Responsive layout works
- [ ] No new hardcoded color values
- [ ] Exception handling follows the standards
- [ ] If a new plugin was added, `hiddenimports` in `toolbox.spec` has been updated

---

Thanks again for your contribution! 🙏
