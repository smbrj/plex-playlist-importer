# Plex Playlist Importer Documentation Standards

**Version:** 1.0
**Status:** Draft
**Last Updated:** July 2026

---

## 1. Purpose

This document defines the documentation philosophy, standards, conventions, and review practices used throughout the Plex Playlist Importer project.

The purpose of these standards is not to make every document look the same. Their purpose is to ensure that every document answers the right questions, for the right audience, in a consistent voice.

Documentation is treated as a first-class project artifact and should be maintained with the same care as application code.

These standards exist to help preserve not only how the application works, but also why it works the way it does.

---

## 2. Documentation Philosophy

Good documentation is part of the application.

An application without adequate documentation may technically provide functionality while leaving much of that functionality difficult to discover, understand, operate, or maintain.

Plex Playlist Importer documentation therefore serves several distinct purposes:

* Help new users understand what the application does.
* Help users install, configure, and operate the application.
* Help operators troubleshoot unexpected behavior.
* Help developers understand the architecture and implementation.
* Help contributors make changes consistent with the project's design.
* Preserve the reasoning behind significant decisions.
* Preserve the history and evolution of the project.

Documentation should explain the application as it exists while preserving enough context to help future maintainers understand how it arrived there.

---

## 3. Core Documentation Principles

### 3.1 Documentation Is Part of the Source Code

Documentation should evolve with the application.

A feature is not considered fully documented when its implementation changes but its documentation does not.

Documentation should be stored under version control whenever practical so that changes to application behavior and documentation can be reviewed and maintained together.

---

### 3.2 Documentation Preserves Intent

Code generally explains what an application does.

Documentation should also explain why significant decisions were made.

Implementation details change over time. The reasoning behind important decisions often remains relevant much longer.

Preserving intent helps future developers distinguish deliberate architectural choices from accidental implementation details.

---

### 3.3 Assume Intelligence, Not Familiarity

Documentation should assume that the reader is capable of understanding technical concepts.

It should not assume that the reader already understands this application, its history, its terminology, or its architecture.

Explain project-specific concepts clearly without unnecessarily explaining basic computing concepts.

Use industry-standard terminology where appropriate.

Avoid unnecessary jargon when plain language communicates the same idea more clearly.

---

### 3.4 Every Document Has an Audience

Before writing a document, identify who is expected to read it.

Examples include:

* New users
* Experienced users
* System operators
* Developers
* Contributors
* Documentation authors

The intended audience determines the appropriate level of technical detail.

A README should not read like source-code documentation.

A Developer Guide should not read like a Quick Start.

An Architecture Decision Record should not read like a user manual.

---

### 3.5 Every Document Has a Purpose

Each document should answer a clearly defined set of related questions.

Information should be placed where a reader would reasonably expect to find it.

When information belongs in another document, provide a reference rather than duplicating a detailed explanation.

This reduces documentation drift and prevents multiple documents from becoming competing sources of truth.

---

### 3.6 Follow the Reader's Journey

Documentation should generally follow the sequence in which the reader encounters questions.

For example, a new user typically asks:

```text
What is this?

        ↓

Why would I use it?

        ↓

Can I run it?

        ↓

How do I install it?

        ↓

How do I configure it?

        ↓

How do I run it?

        ↓

How do I understand the results?

        ↓

Where do I learn more?
```

Documentation intended for users should follow this journey rather than the internal architecture of the application.

The application's architecture may begin with parsers, caches, matching engines, and service clients.

The user's experience does not.

---

### 3.7 Explain Why Before How

When documenting architecture, design, or behavior, explain the reason for a decision before describing its implementation.

Understanding why a design exists helps readers understand how the implementation fits into the larger system.

This principle does not apply equally to every document.

A Quick Start exists to help someone begin using the application quickly. It should answer immediate operational questions without requiring the reader to first understand the project's design philosophy.

---

### 3.8 Start With the Original Problem

When explaining a feature or architectural decision, begin with the problem that caused it to exist.

For example:

* Plex does not natively import common external playlist formats.
* Music metadata frequently differs between sources.
* External services may be temporarily unavailable.
* Repeated acquisition searches can waste resources.
* A stale local cache can reference media that no longer exists.

Starting with the problem makes the resulting design easier to understand.

---

### 3.9 Prefer Plain English

Use clear, direct language.

Prefer short paragraphs and active voice.

Avoid unnecessarily complex terminology.

Technical precision should not require complicated prose.

---

### 3.10 Prefer Examples When They Answer the Question Faster

Examples are particularly valuable for:

* Command-line usage
* Configuration
* Playlist formats
* File layouts
* Expected output
* Common workflows

Examples should be realistic and kept current with the application.

An outdated example is often more harmful than no example.

---

### 3.11 Avoid Unnecessary Duplication

The same detailed information should not be maintained independently in multiple documents.

The README may summarize a concept.

A dedicated reference document may explain it completely.

The Developer Guide may explain its architectural significance.

An ADR may explain why the underlying decision was made.

These are complementary perspectives rather than duplicate documentation.

---

### 3.12 Document Significant Decisions Promptly

Significant decisions should be documented as close as possible to the time they are finalized and agreed upon.

The rationale behind a decision is often more valuable than the decision itself.

Immediately after a decision is made:

* The original problem is still understood.
* Alternatives are still remembered.
* Trade-offs remain clear.
* Reasons for rejecting other approaches are still available.

Months later, people often remember what was decided but not why.

If a future maintainer is likely to ask:

> Why did we do it this way?

the decision should be considered for an Architecture Decision Record.

---

## 4. Documentation Rules

The following rules provide practical guidance for applying the documentation principles.

### 4.1 README Is User-Focused

`README.md` provides:

* Project introduction
* Project purpose
* High-level capabilities
* Requirements
* Installation
* Basic configuration guidance
* Quick Start examples
* High-level design principles
* Documentation navigation
* Project status
* Roadmap
* Licensing information

Implementation details belong in the Developer Guide or supporting documentation.

---

### 4.2 Quick Start Contains Only What Is Needed to Start

Quick Start should help a new user perform a basic operation successfully.

It may include short examples or brief information required to understand those examples.

It should not contain:

* Architectural discussions
* Design rationale
* Detailed configuration references
* Internal implementation details
* Complete command-line reference material

When additional information is required, Quick Start should link to the appropriate reference document.

---

### 4.3 Supporting Documents Explain What the README Introduces

The README should remain readable as the project grows.

Detailed information should move into dedicated documents.

Examples include:

* `docs/configuration.md`
* `docs/parser.md`
* `docs/testing.md`
* `docs/runtime.md`
* `docs/subsystem-overview.md`
* `docs/runtime.md`

The README should point readers toward these documents when additional detail is appropriate.

---

### 4.4 Developer Guide Contains the Weeds

The Developer Guide is intended for readers who need to understand how the application is designed and implemented.

Detailed technical discussion belongs there.

This includes:

* Internal architecture
* Module responsibilities
* Application lifecycle
* Persistent data
* Integration boundaries
* Extension points
* Development workflows
* Performance considerations
* Error handling strategies

The Developer Guide should remain understandable to someone with basic programming knowledge who is unfamiliar with the codebase.

---

### 4.5 Keep Reference Information Separate When It Evolves Independently

Information likely to expand or change independently should have a dedicated reference document.

For example, supported playlist formats are documented in:

`docs/parser.md`

Adding a new input format should primarily require updating that document rather than expanding the README with parsing details.

---

### 4.6 Use Relative Links

Documentation within the repository should use relative links wherever practical.

This allows documentation to remain navigable when:

* Viewed on GitHub.
* Cloned locally.
* Moved between repository hosts.
* Viewed in compatible Markdown tools.

---

### 4.7 Keep Examples Runnable

Command examples should reflect actual application syntax.

Configuration examples should use valid option names.

Playlist examples should use formats accepted by the parser.

Examples should be reviewed when related functionality changes.

---

### 4.8 Avoid Placeholders in Published Documentation

Documents added to the main documentation library should be sufficiently complete to serve their intended purpose.

Avoid publishing documents that consist primarily of:

* TODO markers
* Empty headings
* Planned content
* One-paragraph placeholders

Documentation may evolve, but readers should be able to rely on a document when it is published.

---

## 5. Documentation Library

The project documentation is organized by audience and purpose.

| Document                          | Primary Audience               | Purpose                                                                     |
| --------------------------------- | ------------------------------ | --------------------------------------------------------------------------- |
| `README.md`                       | Users                          | Introduce the project and provide installation and Quick Start guidance     |
| `DEVELOPER_GUIDE.md`              | Developers                     | Explain architecture, implementation, and development practices             |
| `CONTRIBUTING.md`                 | Contributors                   | Explain contribution expectations and development workflow                  |
| `CHANGELOG.md`                    | Users and developers           | Record release-level changes                                                |
| `PROJECT_HISTORY.md`              | Users, developers, maintainers | Preserve project origins, foundational decisions, milestones, and evolution |
| `LICENSE`                         | Everyone                       | Define the project's software license                                       |
| `NOTICE`                          | Everyone                       | Maintain Apache 2.0 attribution and notice information                      |
| `docs/documentation-standards.md` | Documentation authors          | Define documentation principles and conventions                             |
| `docs/configuration.md`           | Users and operators            | Provide complete configuration reference material                           |
| `docs/parser.md`        | Users                          | Document supported playlist formats and required fields                     |
| `docs/subsystem-overview.md`            | Developers                     | Describe high-level system architecture                                     |
| `docs/runtime.md`        | Developers and operators       | Explain end-to-end application processing                                   |
| `docs/testing.md`                 | Developers and contributors    | Document testing strategy and regression practices                          |
| `docs/runtime.md`                 | Operators and developers       | Explain logging, diagnostics, and troubleshooting                           |
| `docs/`                | Developers                     | Provide detailed subsystem documentation                                    |
| `docs/adr/`                       | Developers and maintainers     | Preserve significant architectural and project decisions                    |

Additional documents may be added when they have a clearly defined audience and purpose.

---

## 6. README Structure and Purpose

The README follows the reader's journey rather than the application's internal architecture.

Its standard structure is:

|  # | Section                 | Reader's Question                               |
| -: | ----------------------- | ----------------------------------------------- |
|  1 | Introduction            | What is this project?                           |
|  2 | Overview                | What does it do?                                |
|  3 | At a Glance             | What are the highlights?                        |
|  4 | Why This Project Exists | Why was it created?                             |
|  5 | Features                | What can it do?                                 |
|  6 | Supported Input Formats | What can I import?                              |
|  7 | Optional Integrations   | What else can it work with?                     |
|  8 | Requirements            | Can I run it?                                   |
|  9 | Installation            | How do I install it?                            |
| 10 | Configuration           | What do I need to configure?                    |
| 11 | Quick Start             | What is the first thing I run?                  |
| 12 | Generated Reports       | How do I understand what happened?              |
| 13 | Design Principles       | What engineering philosophy guides the project? |
| 14 | Documentation           | Where do I learn more?                          |
| 15 | Current Status          | Where is the project today?                     |
| 16 | Roadmap                 | Where is the project going?                     |
| 17 | Contributing            | How do I contribute?                            |
| 18 | License                 | How is the software licensed?                   |

The structure may evolve as the project grows, but changes should preserve the logical progression of the reader's journey.

---

## 7. Writing Voice and Tone

Project documentation should be:

* Professional
* Direct
* Approachable
* Technically accurate
* Calm and factual
* Respectful of the reader's intelligence

Documentation should avoid:

* Marketing language
* Unsubstantiated claims
* Unnecessary superlatives
* Excessive jargon
* Overly casual language
* Assuming prior knowledge of the project

For example, prefer:

> The application uses a local search index to improve matching performance.

Instead of:

> The application uses a blazing-fast, high-performance search engine.

The first statement explains behavior.

The second makes a performance claim without providing meaningful information.

---

## 8. Architecture Decision Records

Architecture Decision Records preserve the reasoning behind significant project decisions.

An ADR should be created when a decision is important enough that a future maintainer may reasonably ask:

> Why did we do it this way?

ADRs should document decisions, not routine implementation changes.

### Appropriate ADR Topics

Examples include:

* Selecting the project license.
* Choosing embedded persistence.
* Adopting self-contained deployment.
* Defining integration responsibilities.
* Relying on native Plex and Lidarr synchronization.
* Establishing project-wide documentation standards.

### Topics That Usually Do Not Require an ADR

Examples include:

* Variable renaming.
* Code formatting.
* Routine refactoring.
* Minor bug fixes.
* Small internal implementation changes that do not affect architecture.

---

## 9. ADR Lifecycle

The preferred decision workflow is:

```text
Idea

  ↓

Discussion

  ↓

Decision

  ↓

Document Decision

  ↓

Implementation

  ↓

Update Supporting Documentation

  ↓

Release
```

Whenever practical, the ADR should be written immediately after the decision is finalized and before implementation begins.

This ensures that the ADR records the actual reasoning that led to the implementation rather than becoming a retrospective justification for an implementation that already exists.

---

## 10. ADR Format

ADRs should use a consistent format.

### Title

```text
ADR-NNN - Decision Title
```

### Status

Examples:

* Proposed
* Accepted
* Superseded
* Deprecated

### Context

Describe the problem or situation that required a decision.

### Decision

State clearly what was decided.

### Rationale

Explain why the selected approach was chosen.

### Alternatives Considered

Document meaningful alternatives and why they were not selected.

### Consequences

Describe positive outcomes, trade-offs, constraints, and operational implications.

### Future Reconsideration

Describe circumstances that might justify revisiting the decision.

This section is required even when reconsideration is considered unlikely.

---

## 11. Project History and Foundational Decisions

`PROJECT_HISTORY.md` preserves the story of the project rather than the implementation details of the software.

Its purpose is to answer:

> How did this project arrive where it is today?

The document should include:

1. Project Origins
2. Foundational Decisions
3. Development Timeline
4. Major Milestones
5. Architectural Evolution
6. Future Direction

Foundational decisions may include:

* Treating documentation as a first-class project artifact.
* Establishing documentation standards.
* Adopting Architecture Decision Records.
* Selecting the Apache License 2.0.
* Favoring self-contained deployment.
* Separating playlist management from media acquisition and library management.
* Prioritizing reliability before unnecessary complexity.
* Favoring configuration-driven behavior.

Detailed architectural reasoning should remain in the appropriate ADR. Project History records the significance of the decision within the project's evolution.

---

## 12. Documentation Workflow

Documentation should follow a deliberate review process.

### Step 1 — Draft

Write the document for its intended audience and purpose.

### Step 2 — Technical Review

Confirm that:

* Commands are valid.
* Configuration options are correct.
* Examples reflect actual behavior.
* Architectural descriptions match the implementation.

### Step 3 — Standards Review

Review the document against these documentation standards.

### Step 4 — Read for Flow

Read the document from beginning to end as the intended reader would.

Confirm that questions are answered in a logical order.

### Step 5 — Commit

Commit documentation changes under version control.

Whenever practical, documentation changes related to application functionality should accompany the corresponding code changes.

---

## 13. Documentation Review Checklist

Before considering a document complete, review the following.

### Purpose

* [ ] Does the document have a clearly defined audience?
* [ ] Does the document have a clearly defined purpose?
* [ ] Is this the document where the reader would expect to find this information?

### Content

* [ ] Is the information technically accurate?
* [ ] Does the document explain why when the reasoning is important?
* [ ] Does it begin with the problem when explaining a significant design?
* [ ] Is detailed information duplicated elsewhere unnecessarily?
* [ ] Are references provided when another document contains additional detail?

### Style

* [ ] Does the document assume intelligence rather than familiarity?
* [ ] Is the language clear and direct?
* [ ] Is industry-standard terminology used appropriately?
* [ ] Are paragraphs reasonably short?
* [ ] Are unnecessary jargon and marketing language avoided?

### Examples

* [ ] Are command examples valid?
* [ ] Are configuration examples current?
* [ ] Are file-format examples accepted by the application?
* [ ] Would a new user understand how to apply the example?

### Decisions

* [ ] Was a significant decision made while creating or changing this functionality?
* [ ] Is the decision important enough that someone may later ask why it was made?
* [ ] If so, should an ADR be created or updated?

### Maintenance

* [ ] Are internal links valid?
* [ ] Are references to filenames and directories current?
* [ ] Does the documentation match the current application behavior?
* [ ] Can the document be maintained without creating competing sources of truth?

---

## 14. Maintaining These Standards

These standards are expected to evolve as the project grows.

Changes should be deliberate and should improve the clarity, consistency, or maintainability of the documentation library.

The standards themselves are maintained under version control.

When a new documentation principle is identified, it should be evaluated for inclusion here rather than remaining an informal convention.

The objective is not to create bureaucracy around documentation.

The objective is to preserve a consistent and useful body of knowledge as the project, its contributors, and its implementation evolve.

---

## 15. Closing Principle

The code tells future maintainers what the application does.

The documentation should help them understand how to use it, how to maintain it, and why it became what it is.

Intent is easily lost over time—in code, in project history, and in documentation.

Preserving that intent is one of the primary purposes of this documentation library.
