# AI Project Context – Plex Playlist Importer (PPI)

## Purpose

This document provides context for future AI assistants working on the Plex Playlist Importer (PPI) project.

The goal is to minimize the time required to understand the project philosophy, architecture, design decisions, operational constraints, and development methodology before proposing changes.

Treat this document as supplemental context to the project source code and documentation.

---

# Project Summary

Plex Playlist Importer (PPI) is a Python application that creates and maintains Plex playlists from multiple sources.

Current supported capabilities include:

* Text playlist import
* XMPlaylist channel history import
* Plex fuzzy matching
* Artist alias support
* SQLite search cache
* Lidarr integration
* TIDAL companion playlist integration
* Reporting and analytics
* Automated testing
* Cross-platform operation (Windows, Linux, Unraid, etc.)

PPI is written entirely in Python and is intended to be platform independent.

Although the primary development and production environment became Unraid, Unraid is **not** a project requirement.

---

# Primary Design Philosophy

When proposing changes, prefer solutions that satisfy the following principles:

* Simplicity over unnecessary complexity.
* Reliability over cleverness.
* Maintainability over feature count.
* Backward compatibility whenever practical.
* Graceful failure when external services are unavailable.
* Modular optional integrations.
* Configuration over hard-coded behavior.
* Operational simplicity.

Avoid adding features simply because they are technically possible.

Every feature should solve a real operational problem.

---

# Project Development Philosophy

The project was developed using the following workflow:

Business Problem

↓

Requirements Discussion

↓

Acceptance Criteria

↓

Implementation

↓

Focused Testing

↓

Full Regression Testing

↓

Windows Validation

↓

Linux / Unraid Validation

↓

Documentation

↓

GitHub Pull Request

↓

Release

Do not skip these stages.

---

# Documentation Philosophy

Only document verified functionality.

Do not document planned features.

Do not document speculative behavior.

Documentation should describe what the software actually does.

---

# Testing Philosophy

Every feature should include:

* automated tests where practical
* regression validation
* live operational validation when applicable

Maintain or increase regression coverage.

Never reduce test coverage without justification.

---

# Configuration Philosophy

Configuration options should:

* have sensible defaults
* preserve backward compatibility
* avoid surprising existing users

Configuration is preferred over code modifications for operational policy.

---

# Operational Philosophy

PPI is intended to operate unattended.

Design decisions should favor:

* recoverability
* meaningful logging
* useful diagnostics
* graceful degradation
* deterministic behavior
* minimal operational maintenance

---

# External Integrations

Optional integrations should remain independent.

Current optional integrations include:

* XMPlaylist
* Lidarr
* TIDAL

Changes affecting one integration should not unnecessarily impact another.

The Plex playlist functionality remains the project's core capability.

---

# User Experience

Always think from the perspective of:

1. A first-time user.
2. An operator maintaining the application.
3. A future maintainer reading the code.

Documentation should be concise, practical, and focused on real-world operation.

---

# Code Quality

Prefer:

* readable code
* explicit behavior
* clear logging
* small focused functions
* consistent naming
* modular implementation

Avoid unnecessary abstraction.

---

# GitHub Workflow

Development is managed through GitHub Issues.

Typical workflow:

Feature Request / Bug

↓

Issue Discussion

↓

Implementation Branch

↓

Regression Testing

↓

Pull Request

↓

GitHub Actions Validation

↓

Merge

↓

Automatic Issue Closure

---

# Current Repository State

The repository includes:

* comprehensive documentation
* automated GitHub Actions
* Dependabot
* SECURITY.md
* CONTRIBUTING.md
* CODE_OF_CONDUCT.md
* GitHub Issue Forms
* Pull Request Template

Assume these workflows already exist before proposing additional infrastructure.

---

# Things to Avoid

Avoid suggesting:

* unnecessary GUI additions
* unnecessary dashboards
* unnecessary external dependencies
* platform-specific assumptions
* unnecessary architectural rewrites
* breaking backward compatibility
* replacing working components without measurable benefit

---

# Preferred Response Style

When assisting with this project:

* explain tradeoffs
* recommend the simplest reliable solution
* preserve existing project philosophy
* avoid unnecessary redesign
* distinguish facts from assumptions
* identify operational impacts
* identify testing requirements
* identify documentation updates

Do not recommend changes solely because they represent newer technology.

---

# Project History

PPI began as a simple request to import a text playlist into Plex.

During development it evolved into a production-quality, open-source application through iterative enhancement driven by real operational needs rather than speculative features.

Every significant capability was added to solve an actual problem encountered during development or production use.

Future development should continue that philosophy.

This project was not developed by "having an AI write code." It was developed through a partnership between operational experience and implementation expertise. The operational requirements, testing discipline, deployment considerations, and documentation standards were driven by decades of real-world IT operations, while the implementation, design exploration, and rapid iteration were accelerated by AI assistance. Future changes should preserve that balance: solve real problems first, then choose the simplest technology that reliably addresses them.

---

# Final Guidance

Before proposing any change, ask:

* What business or operational problem does this solve?
* Can it be implemented more simply?
* Does it preserve backward compatibility?
* Will it increase long-term maintenance?
* Does it align with the project's philosophy?

If the answer to these questions is unclear, discuss the problem before proposing the implementation.
