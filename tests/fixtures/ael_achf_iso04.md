# AEL ACHF fixture provenance

These fixed synthetic fixtures identify the upstream source used for comparison, not the latest AEL release or the application’s current default composition. See [current ACHF guide](../../docs/achf-ael.md).

Oracle generated from installed Agentic Eclipse Library 1.3.3, `make_filter('achf_iso_04', image, valid, EclipseGeometry(shape, (79.6,63.2),20))`.
Synthetic scene: shape 128x160, r=hypot(x-79.6,y-63.2), theta=atan2(y-63.2,x-79.6), image=float32((1+20*(20/max(r,20))**3)*(1+.03*sin(17*theta))). Valid: r>22 and x>=3. Invalid input samples are NaN. The archive contains input, mask, geometry, and the upstream encoded Overlay layer. No astronomical data.
Upstream copyright and [MIT notice](../../docs/third-party/AEL-MIT.txt). Tests require no installed AEL plugin.

`ael_achf_variants.npz` stores upstream `make_filter` outputs for achf_iso_01, achf_iso_04 and achf_angular4 on exactly the same image, mask and geometry, under the keys ael_iso_01, ael_iso_04 and ael_angular_4. Generated from installed AEL 1.3.3. Both the finite domain and encoded values match the application port (observed zero numerical difference).

## AEL 1.3.5 update

`ael_achf_iso04_135.npz` and `ael_achf_variants_135.npz` use the same synthetic inputs and geometry, with outputs generated directly by `make_filter` from upstream commit `9a391b6ab5ec325efb98ea8d9e18d14ff54de9b6`. They use the default per-ring display. The original 1.3.3 fixtures are retained as historical references.

`ael_wow_guided_135.npz` uses the same input and upstream `wow_edge_aware(..., n_scales=6)`, encoded with `display_detail(..., scale_region=(rs>=1.1)&(rs<2))`. Six scales deliberately exercise an existing saved setting; new GUI defaults use eight. Inputs remain linear. No runtime dependency on AEL is added.
