# Independent filter composition

`core/pipeline.execute_pipeline` always uses `LayerEngine.render`. Every branch starts from the same immutable working mono source, optionally background-corrected, at its target resolution. `apply_filter` is a numerical dispatcher for zero or one active operator and rejects multiple active filters. There is no sequential enhancement chain.

## Layer order and initial controls

These are the prepared defaults for the first direct image load. Geometry-dependent filter heuristics are evaluated for that image; this table is not a universal numerical recipe.

| Layer | Fixed mode | Initially active/included | Opacity | Gain |
| --- | --- | --- | ---: | ---: |
| NRGF | Multiply | No | 40% | — |
| FNRGF | Multiply | Yes | 20% | — |
| RHEF | Overlay | No | 20% | — |
| MGN | Overlay | Yes | 20% | — |
| WOW (AEL guided edge-aware) | Overlay | Yes | 10% | — |
| Tangential Detail | Overlay | No | 20% | — |
| Larson–Sekanina | Linear Light | No | 75% | 25% |
| ACHF Adaptive | Overlay | No | 19% | — |
| ACHF ISO 01 | Overlay | No | 10% | — |
| ACHF ISO 04 | Overlay | Yes | 10% | — |
| ACHF Angular | Overlay | Yes | 10% | — |

Larson–Sekanina exposes Gain from 0 to 200%; tangential detail and adaptive ACHF also retain their operator-specific gain controls. The Larson–Sekanina radial increment is fixed at zero and angular increment starts at 3°. Other numerical branches run at internal strength 100 and expose opacity rather than redundant strength sliders. Opacity mixes a cached layer; Gain changes Larson–Sekanina encoding before Linear Light clipping and therefore invalidates that layer.

ACHF's selector chooses the variant to edit. Its Include controls independently enable variants, and the master Active checkbox gates the family. ISO 04 is initially selected for editing. Switching panels preserves each variant's parameters and opacity.

Directly opening another image preserves all filter parameters, activations and inclusion flags, including settings restored from JSON. Geometry is detected again; initial filter heuristics are not reapplied. Loading current JSON instead resets/restores its controls; absent filters remain disabled. See [settings](settings.md).

## Encoding and presentation

Layer samples are mono encoded into RGB16 with separate unassociated alpha. Overlay detail is encoded around neutral grey; NRGF/FNRGF use Multiply encodings and Larson–Sekanina a signed Linear Light encoding. AEL filters retain their MAD/tanh encoding. Opacity is quantized to 1/255 and layer channels to 16 bits; composition uses float intermediates.

The main TIFF composes these layers over a linearly normalized native base with **no presentation stretch**. The PSB uses the same filter layers over its own Asinh presentation base. Therefore the main TIFF and cached PSB composite are different products. The preview toggle selects the presented or un-stretched view; JPEG follows that selection. See [PSB presentation and export](psb-export.md).

RGB colour calibration is gain-only, calculated from native RGB, and reused for reduced colour display. It does not recalculate mono detail filters. Fast tone mapping of reduced data can differ from native tone mapping followed by reduction. Native bounds and presentation scale are shared so resolution changes do not independently choose a new brightness window.

Missing/nonfinite display pixels are black. A two-native-pixel smoothstep transition on the observed side of lunar/missing boundaries reduces pixel stair-steps. It changes presentation only, without reconstructing samples or blurring surrounding coronal intensity. Connected black lunar pixels can join that boundary; isolated measured zeros elsewhere remain observations. Layer packages reproduce the fade using an editable black Normal **Edge Antialias** layer, below optional Color Correction. Original layer alpha and validity masks remain intact.

## Filter-specific conventions

NRGF adapts AEL continuous radial statistics through 1.4.1: initial annuli 2 native pixels, median/MAD, minimum 12 samples and no profile smoothing. Its inner radius starts at one reference-disk radius; there is no outer-radius cutoff. Sparse/constant annuli without measurable angular spread remain transparent. Profile smoothing and minimum samples are advanced controls. Signed input is supported. It is independent of FNRGF; both can be active.

MGN sigmas are **1.25, 2.5, 5, 10, 20, 40 native pixels**, weights 1, gamma 3.2, k 0.7, h 0.7 and truncation 3. Preview scales sigmas down internally; sliders retain native units. Both complete and masked paths rescale extreme input units before local normalization and clipping; masked transport values never set that scale.

NRGF layers use AEL 1.4.1 shared-angle chaining: when neighboring annuli cover different angular cells, profile and spread changes are measured on their common observed angles. Complete annuli retain the previous result. Missing pixels remain undefined. The direct `nrgf_normalize` API keeps `partial_annuli='observed'` by default; application layers explicitly select `'chain'` and record it in their mapping metadata.

FNRGF uses a separate Fourier model. Legacy mode retains reference coefficients on complete annuli, but fits only measured sector statistics on partial annuli instead of treating absent sectors as zeros. Its fitted order is bounded by the number of populated sectors; fewer than three sectors remain undefined. Continuous mode applies the same support bound and leaves harmonics k ≤ 2 unpenalized so smooth angular sky trends can be fitted even at low coverage. Higher harmonics retain coverage-dependent regularization. Existing attenuation controls still deliberately retain part of the modeled trend. These changes do not reconstruct missing radiance or make the Fourier and annular operators interchangeable.

WOW offers Standard, adjustable Edge-aware and AEL guided edge-aware. The default AEL path follows AEL 1.3.5: eight native B3 scales on linear luminance, range weights from a smoothed guide, symmetric observed pairs, completeness weighting and local-level removal. Display spread is measured at 1.1–2 reference-disk radii (whole observed image if fewer than 1000 samples). Other backend controls and the retired AEL noise floor do not apply. Existing `ael_bilateral` settings select the updated operator; recalculated results change. Preview scale counts adapt approximately. AEL reports residual sign inversions up to 18–20% in worst sectors and rings in its field tests; this is a display filter, not a photometric measurement. No additional WOW layer or unvalidated radial blend is introduced.

See [ACHF](achf-ael.md), [Larson–Sekanina](larson-sekanina.md) and [RHEF](rhef-continuous.md) for their operators and limitations. More contrast can strengthen noise or boundary artifacts as well as real structure.

## Cache, concurrency and cancellation

A worker retains at most two source identities, normally fast and native, with one current configuration per filter/variant. Source arrays and cached layers are read-only within a job. Keys include geometry, support, resolution and filter parameters. Opacity, activation and presentation edits reuse numerical layers; a Gain or numerical edit replaces that filter's cached configuration. Returning to an older value can require recalculation: the cache is not parameter history.

Only completed, uncancelled layers are cached. Completed layers survive later cancellation. Export takes an isolated dictionary sharing read-only native arrays; completed layers are merged back only if the window still has the same source identity. Export writes active variants only, not an additional all-variant set.

Cache misses use a bounded pool: up to four concurrent filters at four million pixels or less, two above that, further limited by logical CPUs and an estimate of 128 bytes/pixel/filter within one third of physical RAM. Unknown RAM falls back to 512 MiB. This is a scratch estimate, not a hard resident-memory guarantee. Helpers inherit context-local CPU and cancellation budgets. Failure cancels queued work, signals running siblings and waits for them to exit. Composition order is deterministic regardless of completion order.

Logs identify new filter calculations, encoding time and batch wall time. Do not sum overlapping per-filter durations. Cached-only composition reports that no filters were recalculated. Export and verification timings are separate. Historical speed measurements are in the [dated performance report](performance-optimization-20261021.md); current correctness evidence is in [validation](validation.md).

## Layer values and support (issue #3, P1)

FNRGF layers use the dimensionless operator output, with NaN where no model is defined. Continuous FNRGF's inner/outer smoothstep fade and limb protection affect alpha only; they never mix radiance into the encoded values. Radial coefficient smoothing uses the existing symmetric local quadratic fitter at physical radial nodes, preserving polynomial curvature and avoiding replicated-endpoint bias. This reduces the smoothing-induced inner ring; sector binning and radial interpolation can still leave residuals on a smooth corona.

RHEF layers contain Upsilon-curved ranks directly, without median/MAD display normalization. Confidence multiplies alpha, not a mixture of ranks and input units. The numerical `run_fnrgf_native` and `run_rhef_native` helpers retain their input-unit blend by default; layer construction requests `operator_output=True`.

Tangential and adaptive ACHF layers estimate level and spread in two-native-pixel annuli using the existing ring-display helper. Gain acts after encoding, so normalization cannot cancel it; zero gain is neutral grey. When thresholding makes MAD exactly zero, the median nonzero absolute deviation supplies a finite spread instead of a near-zero floor. Fewer than three populated annuli use the documented global fallback. Adaptive ACHF Background Retention was removed from the GUI because detail-layer construction discards it. The numerical API still accepts it; older v4 recipes containing that slider load with the retired field ignored. Logarithmic AEL ACHF operators and their default display encoding are unchanged.

Explicit statistics masks now reach layer construction. Continuous FNRGF and RHEF distinguish samples used to estimate models from finite observed targets: excluded targets are evaluated only inside populated radial model ranges. Excluded intensities cannot affect those models or FNRGF's display normalization. Missing pixels and undefined/sparse models remain transparent. This addresses item 33 for these continuous radial models; NRGF, compatible modes and local operators still restrict their operator/output support together. Extending that behavior needs operator-specific evaluation rules, particularly for logarithmic and wavelet operators; merely forcing alpha to one would expose undefined values.

Finite zero/negative observations remain distinct from missing data. Background correction includes them; positive-only logarithmic ACHF/WOW support remains a separate operator restriction (item 34).
