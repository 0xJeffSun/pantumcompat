# Testing and evidence boundaries

## Hardware evidence

The originating printer was identified by its user as a China domestic P3305DN. With the earlier 0.2.0 component and private conversion runtime, WPS printing succeeded on that unit.

This validates a specific device and documents, not every domestic batch or every P3305DN worldwide. Regional specification differences are documented in [Compatibility](COMPATIBILITY.md); they do not replace a device test.

The public packaging revisions have not independently completed physical-print acceptance. Version 0.2.2 changes the documentation, version strings, domestic model labels and the PPD's rated-throughput metadata. It preserves the conversion algorithm. A successful older test must not be relabeled as a new hardware test of 0.2.2.

## Paper-free conversion checks

After a local build, `tools/test.py` builds a test filter in a temporary directory, denies network access, and denies reads from the default Homebrew prefix and user directory. It verifies:

- File and standard-input interfaces produce identically encoded PCL XL with the expected framing.
- Unsupported paper sizes and malformed input fail with zero output bytes.

These checks exercise an isolated conversion process, not the actual macOS CUPS sandbox.

The installer separately invokes `cups_loopback_check`. It creates its own temporary local queue, routes a public fixture through the real CUPS filter chain, waits for job completion and receives the encoded bytes on a loopback listener. It then removes only its own named queue. It does not contact the physical printer, cancel other jobs, or alter global CUPS sandbox configuration.

## Implemented options versus physical acceptance

The PPD exposes 600 dpi monochrome output, A4/A5/Letter/Legal and simplex/duplex options. Upstream macOS CUPS handles copies, page selection and n-up layout.

Font fidelity, complex tables, grayscale images, mixed page orientation, multiple pages, duplex, copies, page ranges, n-up, non-A4 paper and other applications or OS versions still need appropriate device-and-document checks. Option availability and successful offline conversion are not evidence that every combination has passed a physical print test.

The current build target is Apple Silicon / arm64. Overseas units, other models and Intel Macs are outside the validated scope. The development environment was macOS 26.4.1 with Ghostscript 10.08.0; future macOS compatibility is not guaranteed.
