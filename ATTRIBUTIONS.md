# Third-party code and implementation attributions

Eclipse Image Processor 0.6.0 is developed by Francisco Bitto. Third-party implementation authors retain credit and copyright for their contributions. The application's MIT license does not replace the notices retained for those components. Scientific-method references and other software acknowledgments are listed in the [README credits](README.md#algorithm-credits-scientific-references-and-acknowledgments).

## Agentic Eclipse Library (AEL)

- **Author:** Pere Guerra Serra (`PeterWar` / Peter War).
- **Project:** [Agentic Eclipse Library](https://github.com/PeterWar/Agentic-Eclipse-Library).
- **Source version used for the current ACHF port and PSB writer:** AEL 1.3.3, confirmed from the installed runtime metadata (`pyproject.toml`). This identifies the source used, not a claim about the latest upstream release.
- **Copyright:** Copyright (c) 2026 Pere Guerra Serra.
- **License:** MIT. The original full copyright, permission and disclaimer text is retained in [docs/third-party/AEL-MIT.txt](docs/third-party/AEL-MIT.txt).

### Citation

**Pere Guerra Serra (2026). Agentic Eclipse Library, version 1.3.3.**

The ACHF ISO 01, ISO 04 and Angular implementations and the low-level 16-bit PSB writer in this application contain code copied and adapted from this work. Original authorship and copyright remain with Pere Guerra Serra. The code is used under the MIT license, whose full notice is retained in this repository.

### Copied and adapted ACHF implementation

[core/ael_achf.py](core/ael_achf.py) contains code copied and adapted from AEL. It is not an independently developed replacement for AEL's implementation. This includes the **ISO 01**, **ISO 04** and **Angular** variants.

| AEL source | Functionality used in this application |
| --- | --- |
| `ael/filterbank.py` — `radial_log_residual`, `achf_isotropic`, `display_detail` | Smooth radial spline fitted to log-luminance, multiscale isotropic Gaussian residuals, and MAD/tanh layer encoding. |
| `ael/filters.py` — `_blur`, `gaussian`, `normalized_gaussian`, `tangential_highpass` | Observed-support Gaussian filtering, wide-support approximation, and angular high-pass processing. |
| `ael/polar.py` — linear polar/inverse mapping and observed-support remapping; `ael/geometry.py` — position-angle conventions | Angular sampling, complete bilinear-support checks, inverse mapping and position-angle conventions, adapted into the tiled angular implementation. |

Local adaptations include cooperative cancellation, tiled angular processing, editable per-variant settings, native/preview scaling, validation, and integration with this application's Overlay preview and export workflow. These adaptations do not transfer authorship of the upstream implementation to this project.

The AEL-derived ACHF code is included in the application. The upstream Python package is not needed to run these variants. Synthetic fixtures in `tests/fixtures/ael_achf_*.npz` were generated from AEL 1.3.3 to verify equivalence; their provenance is documented in [the fixture notes](tests/fixtures/ael_achf_iso04.md).

### PSB exporter and research probe

[scripts/research/probe_psb_writer.py](scripts/research/probe_psb_writer.py) directly imports the installed **AEL `ael.photoshop` module** for `new_document`, `add_layer`, `save`, and `verify`. The 16-bit layer-writing implementation used by that experiment belongs to AEL/Pere Guerra Serra. The probe adds test layers, assigns additional blend-mode identifiers, and performs separate structural/pixel checks.

The production exporter [core/psb_export.py](core/psb_export.py) contains code copied and adapted from AEL 1.3.3: `_psd`, `new_document`, `add_layer` and `_to_lr16`. These 16-bit document and layer-writing routines are credited to Pere Guerra Serra under the retained MIT notice. Local additions include merged RGBA compatibility, supported blend modes, embedded recipe metadata, verification and publication without overwriting an existing destination. This is an AEL-derived writer, not an independent reimplementation.

The application bundles the adapted code and requires **psd-tools 1.26.0**, not an upstream AEL installation. Only the historical probe requires an explicitly supplied AEL runtime path. See [the original probe report](docs/psb-writer-probe.md) and [production validation](docs/psb-export.md).

[psd-tools](https://github.com/psd-tools/psd-tools), by its contributors, provides the PSD/PSB structures, compression and reader used by this exporter (MIT license).

### Earlier research references

The earlier study of continuous radial statistics and RHEF used AEL 1.3.2, revision [`5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1`](https://github.com/PeterWar/Agentic-Eclipse-Library/tree/5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1), as a reference. Its historical notes describe that research stage; the explicit copied/adapted-code attribution above describes the later ACHF implementation.

## Other credited components

See the [README software and scientific credits](README.md#algorithm-credits-scientific-references-and-acknowledgments), including sunkit-image, watroo, tse-tools/eclipsetools, EclipseForgeHDR, Eclipse_HDR and GHS. The tse-tools/eclipsetools MIT notice is retained in [docs/third-party/eclipsetools-MIT.txt](docs/third-party/eclipsetools-MIT.txt).
