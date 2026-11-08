# Bounded AEL ACHF contrast

Each AEL ACHF card offers **Contrast: Bounded signed (experimental)** below Opacity, followed by **Detail contrast**. The default remains **Follow filter normalization**, preserving existing recipes and Compatible/Revised behavior. ISO04 and Angular expose these controls in Basic too; ISO01 remains in Standard/Expert. Adaptive ACHF is unchanged.

This local EIP extension changes display encoding, not the signed spatial detail or missing-data alpha. Isotropic variants use the revised radial profile in this mode, independently of the global normalization selector. Angular does not use that profile.

```
scale = 0.05  # natural-log intensity contrast
z = gain*detail/(2.5*scale)
encoded = 0.5 + 0.5*z/hypot(1,z)
```

The curve is monotone, zero-centered and approaches its bounds more slowly than tanh. Gain ranges are 1–2 for ISO01 and 1–4 for ISO04/Angular. Selecting the experimental mode starts at the maximum qualified gain. This enhances contrast, including noise; strong detail is still compressed.

An initial ISO01 4× trial failed the unchanged 0.95 synthetic detail-correlation criterion (0.9148). ISO01 passed at 2×; its limit was reduced rather than weakening the criterion. Failed-trial evidence is retained. These limits are fixture checks, not universal image-quality guarantees.

## Settings and calculation

Optional per-variant v4 controls persist as `achf_ael_controls.<variant>.encoding` and `.contrast`; numerical parameters are `encoding=normalization|bounded` and `contrast`. Missing controls reset to Follow and the variant's bounded gain limit. Each variant is independent. Gain is disabled and ignored in Follow mode. Bounded mode ignores global normalization in its cache; contrast changes recalculate the encoded layer, while opacity only recomposes cached layers. Receipts record the formula, scale, gain and local revision.

## Qualification — 8 November 2026

- **552 repository tests passed**, including six bounded-contrast tests covering signs, masks, units, compatibility, cancellation, cache isolation, settings/UI and TIFF/PSB consistency.
- **66 synthetic cases** and **18 weak-detail injection measurements** passed frozen criteria. Injection correlations were at least 0.98405, with no negative or zero target responses. Cases include radial/constant nulls, clean/noisy structure, correlated noise, sky gradients, stars and spikes.
- Six approved-master preview/native cases preserved both original mappings pixel for pixel. Bounded raw detail matched Revised exactly; alpha remained identical and missing source pixels gained no coverage. Encoding matched the frozen formula within two uint16 steps.
- At matched gain, exact 0/1 encoding in the native 1–1.5-radius band fell from 0.0534% to zero for ISO01 and 0.1577% to zero for ISO04. Angular had zero in both. This measures numerical endpoint saturation, not all visible clipping or limb artifacts.
- Native colour TIFF/JPEG/PSB export completed. TIFF pixels matched the verified PSB composite exactly; original prominence-layer hashes were unchanged, and the saved recipe restored all three controls. Source FITS SHA-256 remained unchanged.
- Actual Qt controls were rendered and inspected in Basic ISO04 and Expert ISO01.

Fast preview remains approximate. Encoded preview-versus-reduced-native RMSE was 0.00880 (ISO01), **0.07492 (ISO04)** and 0.01624 (Angular), on the 0–1 layer range. The larger ISO04 difference makes full-resolution review particularly important; preview is not a native-detail acceptance test.

Evidence is in `/Volumes/Astro/Imágenes/Eclipse-Filter-Quality-and-Default-Parameters-2026-11-08/11-AEL-ACHF-Bounded-Contrast-Implementation-and-Validation/`. Only the approved e1c3c474 master was used; SHA-256: `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`.

One master cannot establish general defaults or prove faint structures are solar. No default mapping change, app/DMG rebuild, Windows run or native Photoshop recomposition was performed.
