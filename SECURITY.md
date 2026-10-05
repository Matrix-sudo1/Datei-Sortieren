# Security Policy

## Supported Versions

The current development line is v8.1. Security fixes are applied to the active development branch and released with the next stable version.

| Version | Supported |
| --- | --- |
| v8.x | :white_check_mark: |
| v7.x | :white_check_mark: for security fixes only |
| < v7 | :x: |

## Security-sensitive areas

The project treats the following as security-sensitive:

- file and path handling
- symlink handling
- cronjob generation
- notification command construction
- HTML report generation
- temporary files
- configuration/profile parsing

Security fixes are regression-tested before being merged into main.

## Reporting a Vulnerability

Please report suspected vulnerabilities through the repository's private GitHub security reporting mechanism (Security Advisories) when available. Avoid publishing exploit details in a public issue.

When reporting a vulnerability, include:

1. affected version or commit
2. affected command or GUI action
3. minimal reproduction steps
4. expected and actual behavior
5. relevant logs or error messages without secrets
