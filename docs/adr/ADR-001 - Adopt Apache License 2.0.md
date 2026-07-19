# ADR-001 - Adopt Apache License 2.0

**Status:** Accepted
**Date:** July 2026

---

## Context

Plex Playlist Importer requires a software license that clearly defines how the project may be used, modified, distributed, and incorporated into other software.

The project is intended to be useful to the broader Plex and personal media communities. The license should encourage adoption and allow individuals, open-source projects, and commercial organizations to use and contribute to the software without unnecessary restrictions.

At the same time, the future direction of the project cannot be predicted. Although the project is currently developed as an open-source application, future opportunities may include broader distribution, integration with other products, or commercial development.

The selected license should therefore preserve flexibility while providing a clear and established legal framework for users and contributors.

---

## Decision

Plex Playlist Importer will be released under the **Apache License, Version 2.0**.

The repository will include a `LICENSE` file containing the full Apache License 2.0 text.

A `NOTICE` file will also be maintained for project identification and any attribution or notice information that may become applicable as the project evolves.

Source files or distributions will include license and attribution information when required by the Apache License 2.0.

---

## Rationale

Apache License 2.0 was selected because it provides a balance between broad adoption, commercial flexibility, and legal clarity.

The license:

* Permits personal and commercial use.
* Permits modification and redistribution.
* Allows the software to be incorporated into larger open-source or proprietary systems.
* Does not impose copyleft requirements on software that incorporates or modifies the project.
* Includes an explicit patent license from contributors.
* Includes provisions addressing patent litigation.
* Provides established requirements for preserving license and attribution notices.
* Is widely recognized and understood by open-source communities and commercial organizations.

The project's current goal is to make the application useful and accessible without unnecessarily restricting how others may use it.

At the same time, the project may evolve in ways that cannot currently be predicted. Apache License 2.0 preserves flexibility for future development and commercial opportunities while maintaining a clear open-source licensing model for code released under the license.

The license does not prevent other individuals or organizations from commercially using or distributing software based on the project. Its value to this project lies instead in providing clear licensing terms, explicit patent provisions, and a well-established framework for contributions and redistribution.

---

## Alternatives Considered

### MIT License

The MIT License was considered because of its simplicity, widespread adoption, and permissive terms.

Advantages included:

* Very short and easy to understand.
* Minimal requirements for users and distributors.
* Broad compatibility with commercial and open-source use.
* Widespread recognition within the Python community.

It was not selected because Apache License 2.0 provides additional legal clarity, particularly through its explicit patent license and patent-related provisions.

The additional requirements of Apache License 2.0 were considered reasonable for this project.

---

### GNU General Public License Version 3

GPLv3 was considered as a strong copyleft alternative.

Advantages included:

* Modifications distributed as derivative works generally remain subject to GPL requirements.
* Encourages continued availability of source code.
* Provides strong protections for software freedom.

It was not selected because the project's goals favor broad interoperability and adoption without requiring downstream applications or distributed derivative works to adopt a copyleft licensing model.

The project may be integrated with Plex-related tools, automation systems, containers, dashboards, or other software with different licensing models. A permissive license provides greater flexibility for those use cases.

---

### Mozilla Public License 2.0

MPL 2.0 was considered as a middle ground between permissive and strong copyleft licenses.

Advantages included:

* File-level copyleft requirements.
* Explicit patent provisions.
* Allows MPL-licensed files to coexist with proprietary code.

It was not selected because Apache License 2.0 provides a simpler permissive model for the project's intended use and integration scenarios.

---

### BSD Licenses

The BSD 2-Clause and 3-Clause licenses were considered as permissive alternatives similar in philosophy to the MIT License.

They were not selected because Apache License 2.0 provides more explicit patent provisions while retaining a permissive licensing model.

---

## Consequences

### Positive

The project can be freely used by individuals, open-source projects, and commercial organizations subject to the terms of Apache License 2.0.

Users may modify and redistribute the software.

The project can be incorporated into larger systems without imposing a requirement that those systems adopt the same license.

Contributors provide an explicit patent license for applicable patent claims covering their contributions.

The license is widely recognized and provides a mature legal framework for open-source development.

The project retains flexibility to pursue future development and commercial opportunities outside the scope of code already distributed under Apache License 2.0.

---

### Trade-offs

Apache License 2.0 is longer and more legally detailed than permissive alternatives such as MIT or BSD.

Redistributors must comply with the license's requirements concerning license notices, attribution, and applicable NOTICE information.

The license does not require modifications or improvements made by third parties to be contributed back to the project.

Third parties may use the software as part of commercial products, subject to the terms of the license.

Code already released under Apache License 2.0 remains available under that license. Selecting Apache License 2.0 does not provide the ability to later withdraw those previously granted rights from existing releases.

Future relicensing may also become more complicated if the project accepts copyrighted contributions from multiple contributors without obtaining the rights necessary to relicense those contributions.

---

## AI-Assisted Development Considerations

Portions of the Plex Playlist Importer project have been developed with the assistance of generative AI tools.

The use of AI-assisted development does not change the project's decision to distribute its source code under Apache License 2.0.

Project maintainers remain responsible for reviewing generated or AI-assisted code before accepting it into the project.

AI-generated suggestions should be treated in the same manner as other proposed source code:

* Review the implementation for technical correctness.
* Confirm that the code is appropriate for the project.
* Avoid intentionally reproducing source code from incompatible or unknown licensing sources.
* Review third-party dependencies separately and comply with their respective licenses.
* Maintain appropriate attribution when required.

The project's Apache License 2.0 applies to project material that the project is legally entitled to license. It does not override copyrights, licenses, or other rights that may apply to third-party material.

AI assistance is therefore treated as a development tool rather than as an exception to normal source-code review and licensing practices.

---

## Future Reconsideration

The project has no current plans to change its licensing model.

The licensing decision may be reconsidered if future legal, commercial, contribution, or distribution requirements materially change the needs of the project.

Any future licensing change must consider:

* Rights already granted under previous Apache License 2.0 releases.
* Ownership of contributions received from third parties.
* Compatibility with third-party dependencies.
* Impact on existing users and contributors.
* The project's continued goals for community adoption and interoperability.

Any significant change to the project's licensing model should be documented in a new ADR that supersedes this decision rather than modifying the historical record of ADR-001.

---

## Decision Summary

Plex Playlist Importer adopts the **Apache License, Version 2.0** as its open-source software license.

The decision favors broad adoption, interoperability, commercial flexibility, explicit patent provisions, and long-term legal clarity.

The repository will maintain the appropriate `LICENSE` and `NOTICE` files, and future licensing decisions will preserve ADR-001 as the historical record of the project's original licensing decision.
