# Optional v4 visual trial

The default build still produces the documented v3 dock. `patchers/dock-v4` is a separate device trial for app artwork and focus styling. It is not part of the default apply pipeline.

The trial creates a private backplate for app shortcuts so the native shared rectangular focus plate cannot show through rounded icon corners. A separate rounded outline indicates focus, and app focus zoom drops from 1.18 to 1.08. Other Samsung controls retain their existing shared backplate behavior.

An optional local JSON map replaces app artwork by exact displayed title. Values are filenames inside the supplied TV asset directory. Supply square 512 × 512 PNGs. The mask must also be 512 × 512: a smaller mask cropped the higher-resolution artwork on the development TV, leaving only the middle letters visible. The initial 256-pixel-mask trial was rejected for this reason.

The source patcher accepts only the exact historical v3 renderer hash checked in its source. A different build path, embedded resource path, firmware, or v3 artifact can produce a different hash. Do not remove this gate to make an unqualified input pass. The normal build pipeline is intentionally unchanged while this trial is reviewed.

Build the source with SDK 9. Run the patcher with these arguments: input renderer, output renderer, private reference-assembly directory, absolute TV asset directory, and optionally the local artwork-map JSON path. `make-assets.py OUTPUT_DIRECTORY` generates original rounded mask and outline PNGs using Python's standard library. It does not download or redistribute application logos.

All generated assemblies, app artwork, signed startup packages, signing certificates, device records, and deployment/rollback scripts stay in ignored local storage. No brand artwork or Samsung assemblies are shipped in this source tree. The development session used some vector marks from [Simple Icons](https://github.com/simple-icons/simple-icons) and locally rendered text cards; those session assets remain private.

## Device evidence

The first trial loaded successfully and the owner confirmed rounded focus, but reported severe artwork cropping. A revised trial with matching 512-pixel artwork and mask loaded and Home relaunched successfully. The owner confirmed that the full logos now fit. Rounded focus was confirmed in the prior trial.

The TV-only startup helper remains separate, private experimental work. The owner reported a failed unplug test; a later boot restored the dock locally and the owner confirmed it was visible. A controlled repeat unplug test was deferred at the owner's request. Do not describe cold-power-loss recovery as fully verified.
