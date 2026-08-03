# Security Policy

Thank you for helping improve the security of Plex Playlist Importer (PPI).

The security of PPI and its users is important. If you believe you have discovered a security vulnerability, please report it responsibly so that it can be investigated and resolved before public disclosure.

---

# Supported Versions

The following versions are currently supported with security updates:

| Version          | Supported |
| ---------------- | --------- |
| 0.1.x            | ✅ Yes     |
| Earlier versions | ❌ No      |

Users are encouraged to upgrade to the most recent supported release whenever practical.

---

# Reporting a Vulnerability

**Private reporting is strongly preferred.**

If you believe you have discovered a security vulnerability in Plex Playlist Importer (PPI), please do **not** disclose it publicly before it has been investigated.

## Preferred Method

Use **GitHub Private Vulnerability Reporting** to submit your report.

Private reports allow the vulnerability to be investigated and corrected before technical details become publicly available.

## Alternative Method

If GitHub Private Vulnerability Reporting is unavailable, you may contact the project maintainer directly.

Please include as much information as possible, including:

* A description of the issue.
* Steps required to reproduce the problem.
* The affected PPI version.
* Any relevant log output or screenshots.
* Suggested mitigations, if known.

Reports containing sufficient technical detail help speed investigation.

Please do **not** create a public GitHub Issue for a suspected security vulnerability unless specifically requested by the project maintainer.


---

# What Constitutes a Security Issue

Examples of security-related issues include, but are not limited to:

* Exposure of API credentials or authentication tokens.
* Improper handling of sensitive configuration information.
* Dependency vulnerabilities that materially affect PPI.
* Command injection.
* Path traversal.
* Unsafe file handling.
* Privilege escalation.
* Arbitrary code execution.

---

# What Is Not a Security Issue

The following should generally be reported through the normal GitHub Issues process:

* Application bugs.
* Playlist matching inaccuracies.
* Music metadata problems.
* Feature requests.
* Performance improvements.
* Documentation corrections.
* User interface or usability suggestions.

---

# Response Process

Security reports will be reviewed as time permits.

If a reported issue is determined to be a legitimate security vulnerability, reasonable efforts will be made to:

* Investigate the report.
* Develop an appropriate remediation.
* Include the fix in a future supported release.
* Publicly disclose the issue after an appropriate fix has been made available, when appropriate.

Because PPI is maintained as an open-source project, specific response or remediation timelines cannot be guaranteed.

---

# Coordinated Disclosure

Please allow a reasonable opportunity to investigate and address reported vulnerabilities before publicly disclosing technical details.

Responsible disclosure helps protect users while corrective updates are being prepared.

---

# Security Philosophy

PPI is designed around the principle of least privilege.

PPI does not intentionally collect telemetry, usage analytics, or personal information. Configuration files may contain service credentials or API tokens and should be treated as confidential. Users should review logs, reports, and configuration files before sharing them publicly.

Optional integrations with Plex, XMPlaylist, Lidarr, and TIDAL require only the permissions necessary to perform their documented functions.

Users are encouraged to:

* Keep PPI up to date.
* Protect API credentials and authentication tokens.
* Avoid committing populated configuration files to source control.
* Use the provided `config.example.ini` when sharing configuration examples.
* Review logs and reports before publishing them to ensure they do not contain environment-specific information.

---

# Acknowledgements

Responsible security reports that help improve PPI are appreciated.

Thank you for helping make Plex Playlist Importer (PPI) more secure for everyone.
