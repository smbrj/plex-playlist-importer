# Contributing to Plex Playlist Importer (PPI)

Thank you for your interest in contributing to Plex Playlist Importer (PPI).

Contributions of all sizes are welcome, including bug reports, documentation improvements, feature suggestions, testing, and code contributions.

The goal of PPI is to provide a reliable, well-documented, and maintainable playlist management application for Plex while supporting optional integrations such as XMPlaylist, Lidarr, and TIDAL.

---

# Before You Begin

For larger enhancements or architectural changes, please consider opening a GitHub Issue before beginning implementation.

Early discussion often helps avoid duplicate work and ensures that proposed changes fit the overall direction of the project.

Small bug fixes, documentation corrections, and minor improvements generally do not require prior discussion.

---

# Development Environment

PPI is written in Python and is intended to be platform independent.

The project is currently developed and validated primarily on:

* Windows (Python 3.12)
* Linux / Unraid (Python 3.11)

Installation instructions are provided in:

```text
INSTALLATION.md
```

Please use a Python virtual environment during development.

---

# Project Philosophy

Several design principles guide development of PPI:

* Keep the application simple and maintainable.
* Prefer reliability over unnecessary complexity.
* Preserve backward compatibility whenever practical.
* Design optional integrations to remain modular and independent.
* Fail gracefully when external services are unavailable.
* Document verified behavior rather than planned features.

These principles have helped PPI evolve while remaining straightforward to operate and maintain.

---

# Coding Guidelines

Please follow the existing coding style used throughout the project.

In general:

* Keep changes focused on a single objective.
* Prefer clear, readable code over clever implementations.
* Add comments where they improve understanding.
* Avoid unrelated formatting-only changes.
* Maintain consistency with the surrounding code.

When practical, new functionality should integrate with the existing project architecture rather than introducing parallel implementations.

---

# Testing

All contributions should be validated before submission.

The current automated regression suite contains **317 tests**.

Before submitting a pull request, please verify that the complete test suite passes.

Example:

```bash
python -m pytest
```

GitHub Actions automatically executes the regression suite for supported Python versions on every pull request.

Contributions that introduce failing tests should include an explanation describing why the failures are expected.

---

# Documentation

Documentation is considered part of the project.

User-visible changes should include corresponding documentation updates when appropriate.

Examples include:

* README.md
* INSTALLATION.md
* XMPLAYLIST.md
* LIDARR.md
* TIDAL.md

Keeping documentation synchronized with implemented behavior helps ensure a consistent experience for all users.

---

# Optional Integrations

PPI is designed so that optional integrations remain independent of the core Plex playlist functionality.

Contributions affecting:

* XMPlaylist
* Lidarr
* TIDAL

should preserve that modular architecture whenever practical.

Changes to one optional integration should avoid introducing unnecessary dependencies on another.

---

# Pull Requests

Please include:

* A concise description of the change.
* The reason for the change.
* Any related GitHub Issue numbers.
* Notes describing any user-visible behavior changes.
* Documentation updates, when applicable.

Small, focused pull requests are generally easier to review than large collections of unrelated changes.

---

# Bug Reports

When reporting a bug, please include as much information as possible, including:

* PPI version.
* Operating system.
* Python version.
* Relevant command line.
* Configuration details (with secrets removed).
* Relevant log messages.
* Steps required to reproduce the problem.

This information greatly assists troubleshooting.

---

# Feature Requests

Feature requests are welcome.

Please describe:

* The problem being solved.
* The proposed solution.
* Alternative approaches that were considered, if applicable.

Well-described feature requests are generally easier to evaluate and discuss.

---

# Security

Please do **not** report security vulnerabilities through public GitHub Issues.

Refer to:

```text
SECURITY.md
```

for the preferred reporting process.

---

# Code of Conduct

All contributors are expected to participate respectfully and constructively.

Please refer to:

```text
CODE_OF_CONDUCT.md
```

for community expectations.

---

# Thank You

Whether you contribute code, documentation, testing, or ideas, your time and effort are sincerely appreciated.

Every contribution helps improve Plex Playlist Importer (PPI) for the entire community.
