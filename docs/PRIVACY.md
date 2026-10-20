# Privacy

The public source archive is generated from an explicit file allowlist, not from the complete development workspace. It excludes real documents, screenshots, print streams, diagnostic logs, proprietary vendor drivers, fonts, build outputs, installer receipts, Git history and hidden system metadata.

The project has no personal author attribution, preset office printer address, or telemetry. The destination is entered by the user and stored in that user's local CUPS queue configuration. Public repository ownership and hosting-platform profile information are managed separately by the hosting platform.

## Local processing

Print documents pass through local CUPS spooling, conversion temporary files and the network backend. System retention behavior depends on local OS settings. The filter removes its own temporary files individually; it does not empty system queues or logs.

Installation uses only a public fixture and a loopback receiver. It records local diagnostics at `/Library/Logs/PantumCompat-install.log` and `/Library/Logs/PantumCompat-selfcheck.prn`. These files are not part of a public source release and are not uploaded automatically.

System logs can contain usernames, document titles, times and destinations. Encoded PRN/PCL/PS files may still reveal document content; encoding is not privacy encryption. Never attach real print streams or unredacted configuration pages to a public issue.

## Source release checks

`python3 tools/release.py` checks the allowlisted UTF-8 files, then creates a ZIP with fixed timestamps and no owner, group or extended attributes. It rejects common user-specific home paths, hardcoded personal email addresses and private/link-local IPv4 addresses except loopback.

Pattern checks cannot identify every name, secret or business detail; manually review the exact files before publishing. A fresh repository and privacy-preserving commit identity avoid carrying local history into publication. Check the hosting account's public profile and email preferences separately.
