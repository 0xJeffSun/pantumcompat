# Changelog

## 0.2.2 — China domestic scope and English documentation

- Identify the China domestic / Xinchuang-oriented P3305DN as the intended target.
- Add an official-source comparison with overseas hardware and explicit compatibility boundaries.
- Make the main README and supporting guides English; provide a Chinese README.
- Describe the no-output Mac driver case, the encoded PCL XL workaround and the separate CUPS sandbox issue.
- Add concise compatibility answers and a regional-variant field to the issue template.
- Correct rated-throughput metadata to 31 ppm and label the PPD and queue for China domestic hardware.
- Update version strings; retain the conversion algorithm. No physical printer job was submitted for this revision.

## 0.2.1 — public source edition

- Retain the working PostScript → outlined PDF → PCL XL → XOR A5 conversion.
- Remove preset printer destinations and personal package identifiers.
- Replace private test documents with a fresh generic PostScript fixture.
- Separate component installation from explicit printer address configuration.
- Leave global CUPS sandbox settings and existing queues unchanged at install time.
- Add local runtime bundling, isolated tests and allowlisted source release tools.
- Document privacy, supported scope and third-party redistribution requirements.

The public packaging revision has not independently completed physical printing
acceptance; earlier 0.2.0 hardware success is described separately in docs/TESTING.md.
