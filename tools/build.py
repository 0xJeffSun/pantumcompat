#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an unsigned LOCAL-USE macOS package from existing Homebrew inputs.

No download, installation, queue change, global configuration change or cleanup.
Binary redistribution needs a separate corresponding-source/license review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def plain_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)  # deliberately do not copy xattrs/ACLs
    destination.chmod(0o644)


def copy_tree(source, destination):
    for entry in sorted(source.iterdir()):
        if entry.name.startswith('.') or entry.name == '__MACOSX':
            continue
        target = destination / entry.name
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            copy_tree(entry, target)
        elif entry.is_file():
            plain_copy(entry, target)


def load_commands(binary):
    lines = run('/usr/bin/otool', '-L', binary).splitlines()[1:]
    return [line.strip().split(' (compatibility version')[0] for line in lines]


def rpaths(binary):
    return re.findall(r'\bcmd LC_RPATH\n.*?\n\s*path (.*?) \(offset',
                      run('/usr/bin/otool', '-l', binary))


def resolve_dependency(name, binary, main):
    if name.startswith('/'):
        candidate = Path(name)
    elif name.startswith('@loader_path/'):
        candidate = binary.parent / name.removeprefix('@loader_path/')
    elif name.startswith('@executable_path/'):
        candidate = main.parent / name.removeprefix('@executable_path/')
    elif name.startswith('@rpath/'):
        suffix = name.removeprefix('@rpath/')
        candidates = [binary.parent / suffix]
        for item in rpaths(binary) + rpaths(main):
            expanded = item.replace('@loader_path', str(binary.parent))
            expanded = expanded.replace('@executable_path', str(main.parent))
            candidates.append(Path(expanded) / suffix)
        candidate = next((x for x in candidates if x.exists()), candidates[0])
    else:
        raise ValueError('Unsupported dependency format: ' + name)
    return candidate.resolve(strict=True)


def cellar_root(binary):
    # Homebrew layout: .../Cellar/formula/version/{bin,lib}/file
    for parent in binary.parents:
        if parent.parent.name == 'Cellar':
            relative = binary.relative_to(parent).parts
            return parent / relative[0], parent.name
    raise ValueError('Only dependencies installed in a Homebrew Cellar are supported.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gs', default=shutil.which('gs'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('This release supports Apple Silicon macOS builds only.')
    if not args.gs:
        raise SystemExit('Install Ghostscript first (see README); this tool does not install dependencies.')
    gs = Path(args.gs).resolve(strict=True)
    version = (ROOT / 'VERSION').read_text().strip()
    out = args.output or ROOT / 'build' / ('local-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = out / 'payload/Library/Printers/PantumCompat'
    runtime = base / 'Runtime'
    for name in ('Filters', 'Tools', 'Resources', 'Runtime/bin', 'Runtime/lib', 'Runtime/Licenses'):
        (base / name).mkdir(parents=True, exist_ok=True)

    graph, pending = {}, [gs]
    while pending:
        binary = pending.pop()
        if binary in graph:
            continue
        if 'arm64' not in run('/usr/bin/lipo', '-archs', binary):
            raise ValueError('A dependency does not contain arm64 code.')
        refs = {}
        for name in load_commands(binary):
            if name.startswith(('/usr/lib/', '/System/Library/')):
                continue
            dependency = resolve_dependency(name, binary, gs)
            if dependency == binary:  # a dylib's own LC_ID_DYLIB
                continue
            refs[name] = dependency
            pending.append(dependency)
        graph[binary] = refs

    destinations = {p: runtime / ('bin/gs' if p == gs else 'lib/' + p.name) for p in graph}
    if len(set(destinations.values())) != len(destinations):
        raise ValueError('Two dependencies have the same basename; refusing ambiguous relocation.')
    components = {}
    for source, target in destinations.items():
        plain_copy(source, target)
        target.chmod(0o755)
        for old, dependency in graph[source].items():
            prefix = '@loader_path/../lib/' if source == gs else '@loader_path/'
            run('/usr/bin/install_name_tool', '-change', old, prefix + destinations[dependency].name, target)
        if source != gs:
            run('/usr/bin/install_name_tool', '-id', '@rpath/' + target.name, target)
        run('/usr/bin/codesign', '--force', '--sign', '-', '--identifier', 'org.pantumcompat.runtime.' + target.name, target)
        run('/usr/bin/codesign', '--verify', '--strict', target)
        for name in load_commands(target):
            if not name.startswith(('/usr/lib/', '/System/Library/', '@loader_path/', '@rpath/')):
                raise ValueError('Unrelocated dependency remains in runtime.')
        prefix, formula = cellar_root(source)
        key = formula + '-' + prefix.name
        if key not in components:
            licenses = [x for x in prefix.iterdir() if x.is_file() and
                        any(word in x.name.upper() for word in ('LICENSE', 'COPYING', 'COPYRIGHT'))]
            # Some Homebrew Leptonica bottles keep the full BSD notice only
            # in public headers. Preserve the exact leading notice verbatim.
            if not licenses and formula == 'leptonica':
                header = prefix / 'include/leptonica/allheaders.h'
                text = header.read_text()
                notice = text.split('*/', 1)[0] + '*/\n'
                if not (text.startswith('/*') and 'Redistribution' in notice
                        and 'Copyright' in notice and 'THIS SOFTWARE' in notice):
                    raise ValueError('Leptonica header notice could not be verified.')
                folder = runtime / 'Licenses' / key
                folder.mkdir(parents=True, exist_ok=True)
                (folder / 'NOTICE-from-public-header.txt').write_text(notice)
                components[key] = {'formula': formula, 'version': prefix.name}
                continue
            if not licenses:
                raise ValueError('No top-level license notice found for dependency: ' + formula)
            for notice in licenses:
                plain_copy(notice, runtime / 'Licenses' / key / notice.name)
            components[key] = {'formula': formula, 'version': prefix.name}

    gs_prefix, _ = cellar_root(gs)
    shared = gs_prefix / 'share/ghostscript'
    if not (shared / 'Resource').is_dir():
        choices = [p for p in shared.iterdir() if p.is_dir() and (p / 'Resource').is_dir()]
        if len(choices) != 1:
            raise ValueError('Cannot identify Ghostscript resource root.')
        shared = choices[0]
    for name in ('Resource', 'fonts', 'lib', 'iccprofiles'):
        if not (shared / name).is_dir():
            raise ValueError('Missing Ghostscript resource directory: ' + name)
        copy_tree(shared / name, runtime / 'share/ghostscript' / name)
    plain_copy(ROOT / 'resources/fonts.conf', runtime / 'fonts.conf')
    for name in ('P3305DN-Compat.ppd', 'selfcheck.ps'):
        plain_copy(ROOT / 'resources' / name, base / 'Resources' / name)
    plain_copy(ROOT / 'tools/configure-printer', base / 'Tools/configure-printer')
    (base / 'Tools/configure-printer').chmod(0o755)
    for name, subdir in (('pantum_pclxl_encode', 'Filters'), ('cups_loopback_check', 'Tools')):
        target = base / subdir / name
        run('/usr/bin/xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
            '-Wno-deprecated-declarations', ROOT / 'src' / (name + '.c'), '-lcups', '-o', target)
        run('/usr/bin/codesign', '--force', '--sign', '-', '--identifier', 'org.pantumcompat.' + name, target)
    scripts = out / 'scripts'
    scripts.mkdir()
    for name in ('preinstall', 'postinstall'):
        plain_copy(ROOT / 'packaging' / name, scripts / name)
        (scripts / name).chmod(0o755)
    plain_copy(ROOT / 'LICENSE', base / 'LICENSE')
    plain_copy(ROOT / 'NOTICE', base / 'NOTICE')
    (runtime / 'components.json').write_text(json.dumps(list(components.values()), indent=2) + '\n')
    run('/usr/bin/cupstestppd', '-q', base / 'Resources/P3305DN-Compat.ppd')
    pkg = out / ('PantumCompat-' + version + '-arm64-LOCAL-USE.pkg')
    run('/usr/bin/pkgbuild', '--root', out / 'payload', '--scripts', scripts,
        '--identifier', 'org.pantumcompat.community', '--version', version,
        '--install-location', '/', '--ownership', 'recommended', pkg)
    result = {'version': version, 'architecture': 'arm64', 'ghostscript': run(gs, '--version').strip(),
              'runtime_files': len(graph), 'package_sha256': hashlib.sha256(pkg.read_bytes()).hexdigest(),
              'scope': 'local-use binary; not part of source release', 'components': list(components.values())}
    (out / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Local package built:', pkg)
    print('No installation or printer job was performed. Do not publish this binary without the redistribution review in NOTICE.')


if __name__ == '__main__':
    main()
