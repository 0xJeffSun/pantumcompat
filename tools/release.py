#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Package ONLY the reviewed public source allowlist with neutral ZIP metadata."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    '.gitignore', '.github/ISSUE_TEMPLATE/bug_report.md',
    'VERSION', 'LICENSE', 'NOTICE', 'README.md', 'README.zh-CN.md', 'CHANGELOG.md',
    'docs/PRIVACY.md', 'docs/TESTING.md', 'docs/REDISTRIBUTION.md', 'docs/COMPATIBILITY.md',
    'src/pantum_pclxl_encode.c', 'src/cups_loopback_check.c',
    'resources/P3305DN-Compat.ppd', 'resources/fonts.conf', 'resources/selfcheck.ps',
    'packaging/preinstall', 'packaging/postinstall',
    'tools/configure-printer', 'tools/build.py', 'tools/test.py', 'tools/release.py',
)
EXECUTABLES = {'packaging/preinstall', 'packaging/postinstall', 'tools/configure-printer',
               'tools/build.py', 'tools/test.py', 'tools/release.py'}


def audit(name, data):
    text = data.decode('utf-8', errors='strict')
    if '\x00' in text:
        raise ValueError('Binary content is not allowed: ' + name)
    if re.search(r'/(?:Users|home)/[^\s/"<>]+', text):
        raise ValueError('User-specific home directory detected: ' + name)
    if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text):
        raise ValueError('Email address needs manual review: ' + name)
    for item in re.findall(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', text):
        try:
            address = ipaddress.ip_address(item)
        except ValueError:
            continue
        if (address.is_private or address.is_link_local) and str(address) != '127.0.0.1':
            raise ValueError('Private/link-local network address detected: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise SystemExit('Invalid version')
    prefix = 'pantumcompat-' + version
    target = args.output or ROOT / 'dist' / (prefix + '-source.zip')
    if target.exists():
        raise SystemExit('Output already exists; choose a new explicit path.')
    payload = {}
    hashes = {}
    for name in PUBLIC_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing file or unexpected symlink: ' + name)
        data = path.read_bytes()
        audit(name, data)
        payload[name] = data
        hashes[name] = hashlib.sha256(data).hexdigest()
    manifest = {'version': version, 'kind': 'source-only', 'files': hashes,
                'archive_metadata': 'fixed timestamp; no owner, group, paths or xattrs',
                'excluded': ['binaries', 'fonts', 'personal documents', 'logs', 'print data',
                             'historical installers', 'git history', 'build outputs'],
                'privacy_checks': 'allowlist plus UTF-8, home-directory, email and private-IP checks'}
    payload['RELEASE-MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(prefix + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            mode = 0o755 if name in EXECUTABLES else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    print('Created source-only release:', target)
    print('Files:', len(payload))
    print('SHA256:', hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
