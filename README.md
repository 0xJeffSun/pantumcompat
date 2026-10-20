# PantumCompat: macOS printing for the China domestic P3305DN

English | [简体中文](README.zh-CN.md)

**PantumCompat is an open-source macOS CUPS compatibility driver for the China domestic Pantum P3305DN, commonly described as the Xinchuang configuration.** It targets the case where the printer is reachable and works through its UOS driver, but jobs sent through the tested stock Mac driver produce no pages. A native Apple Silicon filter converts the job to encoded PCL XL; WPS printing has succeeded on the originating domestic printer.

> **Check the regional version first.** The China product page specifies **31 ppm and an 800 MHz processor**. An overseas P3305DN page specifies different hardware and software support. The shared model name does not establish compatibility. See the [regional comparison and official sources](docs/COMPATIBILITY.md).

## What problem does it solve?

The motivating case was a China domestic P3305DN that printed successfully with its UOS driver while the tested Mac/PostScript path produced no printed page. An otherwise reachable printer could therefore appear installed on macOS without working from WPS.

PantumCompat supplies the missing macOS conversion and encoding path:

```text
Application → macOS CUPS PostScript → Ghostscript outlined PDF
            → monochrome PCL XL → whole-stream XOR 0xA5
            → CUPS socket backend → printer
```

It also bundles a private Ghostscript runtime when built locally, so the installed filter does not need to execute Homebrew's `gs` from inside the macOS CUPS sandbox. The earlier sandbox failure and the printer-format mismatch were separate issues.

This is an independent interoperability project, not an official Pantum driver. It does not repair network connectivity, add a printer firmware feature, or recover fonts already missing from the input document.

## Compatibility at a glance

| Item | Scope |
| --- | --- |
| Intended printer | China domestic / Xinchuang-oriented **Pantum P3305DN**; match the [regional specification](docs/COMPATIBILITY.md) |
| Mac architecture | **Apple Silicon / arm64**; Intel Macs are not validated |
| Development environment | macOS 26.4.1 and Ghostscript 10.08.0 |
| Implemented print path | macOS CUPS, Ethernet, RAW TCP port 9100, encoded PCL XL |
| Rendering | 600 dpi monochrome; A4, A5, Letter and Legal options |
| Hardware evidence | WPS printing succeeded with the earlier 0.2.0 component on the originating domestic unit |
| Public release checks | Source builds and isolated conversion tests passed; public packaging revisions have not independently completed physical-print acceptance |
| Overseas P3305DN / other models | **Unvalidated**; do not select this component solely from the model name |

Duplex, copies, page selection and n-up options exist, but their presence is not a promise that every combination has passed a paper test. See [Testing and evidence boundaries](docs/TESTING.md).

## Build and install

This is a **source-only release**. It contains no ready-to-share Ghostscript bundle, third-party fonts, proprietary vendor driver, or captured print job.

Prerequisites: an Apple Silicon Mac, Xcode Command Line Tools, Python 3.9 or newer, and Ghostscript already installed through Homebrew. The build tool does not download or install dependencies.

From the project directory:

```sh
python3 tools/build.py
```

The tool creates a fresh `build/local-*` directory and a `LOCAL-USE.pkg` installer. It relocates Ghostscript and its non-system dependencies into the printer runtime. It does not install the package, change queues, or submit a print job.

Optional paper-free conversion checks; replace the example with the directory printed by the build tool:

```sh
python3 tools/test.py build/local-YOUR-BUILD-DIRECTORY
```

Open the locally built package and follow the macOS administrator prompt. Installation runs a genuine CUPS self-check through a temporary loopback queue, without contacting the physical printer. It leaves global CUPS sandbox configuration and existing queues unchanged. The local package is ad-hoc signed, not Developer ID signed or notarized.

Then create or update the destination queue, replacing `printer.example` with your printer's own IPv4 address or DNS hostname:

```sh
sudo /Library/Printers/PantumCompat/Tools/configure-printer printer.example
```

The tool configures `P3305DN_Compat`, displayed as **Pantum P3305DN China (Compatible)**. Defaults are A4, 600 dpi and simplex. It does not submit a test page or change the default printer, and stops if that queue has unfinished jobs. IPv6 and full device URIs are not accepted by this configuration tool.

Select that queue in WPS or another application and test one page first. A failed job is a reason to inspect the queue, not repeatedly resend the document.

## Frequently asked questions

### Does this support the overseas Pantum P3305DN?

Overseas units are outside the validated target. Pantum's regional product pages list materially different configurations under the P3305DN name. Use the [comparison](docs/COMPATIBILITY.md) and the official driver for the correct region where it works; the shared name is insufficient evidence for this workaround.

### Does this guarantee printing from every WPS document, table or PDF?

No. The hardware evidence covers specific documents on the originating domestic printer. Font fidelity, complex tables, mixed orientation, images, duplex and multiple-copy jobs need their own checks. Converting glyphs to outlines cannot undo font substitution that happened upstream.

### Does this add AirPrint or iPhone printing?

No. This project supplies a Mac CUPS filter and network queue configuration. It is not an AirPrint server or printer firmware update.

### Must I disable the macOS CUPS sandbox or install UOS on my Mac?

No. The package builds a native arm64 conversion runtime under the printer component directory and checks the actual CUPS path during installation. UOS driver behavior informed the interoperability work; Linux executables are not shipped or run on macOS.

### How do I tell whether my unit is the intended domestic version?

Check its purchase region, regional documentation and configuration information against the [official-source comparison](docs/COMPATIBILITY.md). The domestic specification is an identification clue, not a compatibility certificate. If the variant is unclear, report it as unknown rather than inferring support from the front-panel model name.

## Privacy and safety

The filter has no telemetry, downloader, or direct printer connection. It finishes conversion and validates the output framing before releasing bytes to the CUPS backend. Temporary files, CUPS spooling and system logs remain subject to the local operating system's behavior.

RAW port 9100 has no transport encryption or server authentication; use it only on a trusted network. Never upload real documents, PRN/PCL/PS captures, full configuration pages, serial numbers, MAC addresses, printer addresses or unredacted logs to an issue. Use the generic `resources/selfcheck.ps` fixture where possible. See [Privacy](docs/PRIVACY.md).

## License

Project source, scripts, compatibility PPD and public fixture are **AGPL-3.0-or-later**; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Third-party components retain their own licenses. Review [Redistribution](docs/REDISTRIBUTION.md) before publishing a locally built binary installer; copying license notices alone does not complete corresponding-source obligations.
