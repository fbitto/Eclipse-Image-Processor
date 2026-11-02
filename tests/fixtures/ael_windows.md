# Windows AEL numerical references

Generated 2 November 2026 directly from upstream AEL repository revision
331196e225b758cb0ef90cbb93b4de7f1028d396 (ael/ revision 17029c9),
using Windows 11 AMD64, Python 3.14.7, NumPy 2.5.4, SciPy 1.18.1,
OpenCV 5.0.0.93. Upstream copyright Pere Guerra Serra, MIT; see
docs/third-party/AEL-MIT.txt. No application outputs were used as references.

The three Windows archives retain the existing synthetic inputs/geometry and
replace only expected values with native upstream make_filter outputs for ACHF
ISO 01/04/angular4 and radial_quantile_rank outputs for both global RHEF scenes.
All three application ACHF variants and both RHEF scenes matched these upstream
outputs exactly before fixture creation. Existing macOS archives remain intact.
RHEF differs from the macOS reference by at most 6.765127e-6 and 1.949072e-5;
ACHF ISO 04 differed by about 1.073e-6 and up to one encoded uint16 level.
Disabling NumPy AVX2/FMA3/AVX512F did not remove the ACHF differences.

Windows tests select these references, retaining exact RHEF and export checks
and the existing ACHF tolerance. This evidence covers this dependency/backend
combination; it does not establish universal byte equality across platforms.
