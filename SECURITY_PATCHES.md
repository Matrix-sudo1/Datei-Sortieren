# Security Patches – v8.4

This document records the security hardening included through the v8.4 hardening branch.

## v8.4

### P1 – Cronjob command construction
Cronjob paths are now passed through shell-safe single-quote escaping before being written to crontab. Newline and non-printable characters are rejected as an additional validation layer.

### P2 – Notification arguments
Notification text is sanitized before being embedded into platform-specific notification commands.

### P3 – HTML reports
Dynamic folder and category values are HTML-escaped before being inserted into the generated report.

### P4 – Temporary files
Temporary working files use mktemp rather than predictable filenames.

### P5 – Recursive processing
Recursive sorting creates a snapshot of source files before moving anything. Newly created target directories therefore cannot feed new files back into the same traversal.

### P6 – Symlink handling
Source symlinks are explicitly skipped rather than treated as regular files.

### P7 – Configuration path validation
Custom category names are rejected when they contain path separators, traversal components, or non-printable characters.

### P8 – Undo safety
Undo refuses to overwrite an already existing source path.

## Historical v8.2 hardening

The following are deliberately tracked for subsequent v8.x work:

- replace the legacy tab-separated undo log with a structured journal that can safely represent every Unix filename except NUL and `/`
- make undo transactional and crash-recoverable
- add dedicated regression tests for special filenames, symlinks, duplicate handling, watch mode and cronjob escaping
- protect destination directories against pre-existing symlink redirection
- add machine-readable CLI output for GUI integration beyond the current dry-run preview

## v8.4 hardening

### P9 – Machine-readable API errors
Invalid folders and argument errors now return structured JSON with an error event and exit code instead of leaking argparse text to API consumers.

### P10 – Regression matrix
The regression suite now validates Bash/Python syntax, JSON API error handling, and the v8.3 watch engine in the same CI gate.
