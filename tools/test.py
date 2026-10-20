#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline rendering checks; never install, configure queues, or contact printers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from build import ROOT, copy_tree, plain_copy, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    args = parser.parse_args()
    build_dir = args.build_directory.resolve()
    base = build_dir / 'payload/Library/Printers/PantumCompat'
    stage = Path(tempfile.mkdtemp(prefix='PantumCompat-QA-', dir='/private/tmp'))
    runtime = stage / 'Runtime'
    runtime.mkdir()
    copy_tree(base / 'Runtime', runtime)
    for p in (runtime / 'bin').iterdir():
        p.chmod(0o755)
    fontconfig = (runtime / 'fonts.conf').read_text()
    fontconfig = fontconfig.replace('/Library/Printers/PantumCompat/Runtime', str(runtime))
    fontconfig = fontconfig.replace('/Library/Caches/PantumCompat/fontconfig', str(stage / 'font-cache'))
    (runtime / 'fonts.conf').write_text(fontconfig)
    (stage / 'font-cache').mkdir()
    plain_copy(ROOT / 'resources/selfcheck.ps', stage / 'input.ps')
    binary = stage / 'filter'
    run('/usr/bin/xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
        '-Wno-deprecated-declarations', '-DPANTUM_RUNTIME_ROOT=' + json.dumps(str(runtime)),
        ROOT / 'src/pantum_pclxl_encode.c', '-lcups', '-o', binary)
    run('/usr/bin/codesign', '--force', '--sign', '-', '--identifier', 'org.pantumcompat.offline-check', binary)
    profile = '(version 1) (allow default) (deny network*) (deny file-read* (subpath "/opt/homebrew")) (deny file-read* (subpath "/Users"))'
    results = []
    cases = [('file', 'PageSize=A4', None, True),
             ('stdin', 'PageSize=A4', (stage / 'input.ps').read_bytes(), True),
             ('bad-paper', 'PageSize=Unsupported', None, False),
             ('invalid-input', 'PageSize=A4', b'not valid PostScript\n', False)]
    valid_hashes = []
    for name, options, data, valid in cases:
        argv = ['/usr/bin/sandbox-exec', '-p', profile, str(binary),
                '1', 'test', 'public self-check', '1', options]
        if data is None:
            argv.append(str(stage / 'input.ps'))
        result = subprocess.run(argv, input=data, capture_output=True, cwd=stage, timeout=60)
        if valid:
            decoded = bytes(x ^ 0xa5 for x in result.stdout)
            passed = result.returncode == 0 and decoded.startswith(b'\x1b%-12345X') and \
                b'PCLXL' in decoded[:160] and decoded.endswith(b'\x1b%-12345X')
            valid_hashes.append(hashlib.sha256(result.stdout).hexdigest())
        else:
            passed = result.returncode != 0 and len(result.stdout) == 0
        results.append({'case': name, 'pass': passed, 'exit': result.returncode,
                        'output_bytes': len(result.stdout)})
    results.append({'case': 'stdin-and-file-output-identical', 'pass': len(set(valid_hashes)) == 1})
    (build_dir / 'offline-test.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    print('No installation, printer connections, or physical printing performed.')
    if not all(x['pass'] for x in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
