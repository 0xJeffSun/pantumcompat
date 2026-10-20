# Third-party components and binary redistribution

The public release contains project source, not third-party executables or fonts. Original project files are licensed under **AGPL-3.0-or-later**; the complete text is in [LICENSE](../LICENSE).

Ghostscript is available under the AGPL or a separate commercial license. See the [official release page](https://ghostscript.com/releases/gsdnld.html), [official FAQ](https://ghostscript.com/faq/) and [GNU AGPL text](https://www.gnu.org/licenses/agpl-3.0.html).

The local build tool copies Ghostscript, transitive non-system dependencies and resources already installed on the builder's machine. It relocates the runtime and copies recognized license notices. Its output is labeled `LOCAL-USE` and is excluded from source releases.

Copying those notices does not establish that every binary redistribution requirement has been met. Before publishing a binary installer, fix the exact component versions and sources, review all library, font and resource licenses, preserve required notices, and supply complete corresponding source, patches and build/install materials as required by the applicable licenses. An upstream homepage or a license file alone is not a substitute for corresponding source.

The generated `components.json` records component names and versions; it is not a complete software bill of materials. Do not include proprietary vendor drivers, disassembly dumps or fonts extracted from real documents in this source project. Treat any future public binary installer as a separate release review.
