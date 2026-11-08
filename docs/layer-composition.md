# Independent filter composition

AEL ACHF's optional [bounded signed contrast](achf-bounded-contrast.md) uses a zero-centered algebraic display curve with independent per-variant gain. It preserves signed raw detail and coverage, uses the revised isotropic profile, and overrides global normalization for that variant. Follow filter normalization remains the default; Adaptive ACHF is unaffected.

`core/pipeline.execute_pipeline` always uses `LayerEngine.render`. Every branch starts from the same immutable working mono source, optionally background-corrected, at its target resolution. `apply_filter` is a numerical dispatcher for zero or one active operator and rejects multiple active filters. There is no sequential enhancement chain.

## Layer order and initial controls

These are the prepared defaults for the first direct image load in Standard or Expert. Basic uses the reviewed six-layer starter described below. Geometry-dependent filter heuristics are evaluated for that image; this table is not a universal numerical recipe.

| Layer | Fixed mode | Initially active/included | Opacity | Gain |
| --- | --- | --- | ---: | ---: |
| NRGF | Multiply | No | 40% | — |
| NAFE (AEL) | Overlay | No | 40% | — |
| FNRGF | Multiply | Yes | 20% | — |
| RHEF | Overlay | No | 20% | — |
| MGN | Overlay | Yes | 20% | — |
| WOW (AEL guided edge-aware) | Overlay | Yes | 10% | — |
| Tangential Detail | Overlay | No | 10% | — |
| Larson–Sekanina | Linear Light | No | 75% | 25% |
| ACHF Adaptive | Overlay | No | 10% | — |
| ACHF ISO 01 | Overlay | No | 10% | — |
| ACHF ISO 04 | Overlay | Yes | 10% | — |
| ACHF Angular | Overlay | Yes | 10% | — |

Larson–Sekanina exposes Gain from 0 to 200%; tangential detail and adaptive ACHF also retain their operator-specific gain controls. The Larson–Sekanina radial increment is fixed at zero and angular increment starts at 3°. Other numerical branches run at internal strength 100 and expose opacity rather than redundant strength sliders. Opacity sliders map track position x to 100 × x^1.5 percent; displayed, typed and saved values stay in actual percentage units. Opacity mixes a cached layer; Gain changes Larson–Sekanina encoding before Linear Light clipping and therefore invalidates that layer.

ACHF variants have separate Active cards with independent parameters and opacity. Basic shows ISO 04 and Angular; Standard and Expert expose all four variants. Expanding a card does not activate it.

Directly opening another image preserves all filter parameters, activations and inclusion flags, including settings restored from JSON. Geometry is detected again; initial filter heuristics are not reapplied. Loading current JSON instead resets/restores its controls; absent filters remain disabled. See [settings](settings.md).

### Basic first-load starter

Basic enables NAFE original at 40%, Reference-compatible FNRGF at 15%, AEL guided WOW at 10%, Source-relative Tangential at 10%, and ISO04/Angular Bounded contrast 3 at 10% each. FNRGF uses 2-native-pixel rings, inner radius 1 R, outer radius 12.6 R, Fourier order 16 and 64 sectors. WOW uses eight scales and noise reduction 3; experimental AEL statistics separation is on. Other numerical controls retain their prepared defaults. NRGF/MGN remain available but off; RHEF, ISO01, adaptive ACHF and Larson–Sekanina remain excluded in Basic.

This applies once after first-image heuristics, only for a direct image load in Basic. Later image loads, eligible mode switches and saved recipes retain their controls. Geometry is measured from the loaded image; no reviewed-master coordinates or source paths are installed. Native-preview selection remains a viewport choice. This recipe was visually accepted on one master, with slight noise distraction and a visible but acceptable limb ring; it is not general multi-image qualification.

## Encoding and presentation

Layer samples are mono encoded into RGB16 with separate unassociated alpha. Overlay detail is encoded around neutral grey; NRGF/FNRGF use Multiply encodings and Larson–Sekanina a signed Linear Light encoding. AEL filters retain their MAD/tanh encoding. Opacity is quantized to 1/255 and layer channels to 16 bits; composition uses float intermediates.

The main TIFF and JPEG compose these layers over the same exposure-controlled PSB Asinh presentation base, including selected prominence presentation. The viewport toggle can inspect an un-stretched composition without changing exports. GUI exports also preserve float32 working mono/RGB and validity in a separate source package. Display products embed sRGB; raw working sources do not. Optional native Color Correction remains Photoshop-only. See [PSB presentation and export](psb-export.md).

RGB colour calibration is gain-only, calculated from native RGB, and reused for reduced colour display. It does not recalculate mono detail filters. Fast tone mapping of reduced data can differ from native tone mapping followed by reduction. Native bounds and presentation scale are shared so resolution changes do not independently choose a new brightness window.

Missing/nonfinite display pixels are black. A two-native-pixel smoothstep transition on the observed side of lunar/missing boundaries reduces pixel stair-steps. It changes presentation only, without reconstructing samples or blurring surrounding coronal intensity. Connected black lunar pixels can join that boundary; isolated measured zeros elsewhere remain observations. Layer packages reproduce the fade using an editable black Normal **Edge Antialias** layer, below optional Color Correction. Original layer alpha and validity masks remain intact.

## Filter-specific conventions

[NAFE](nafe-ael.md) uses AEL 1.4.2 fuzzy equalization directly as an Overlay layer. It starts disabled; Standard exposes opacity and Expert exposes automatic/manual gate sigma and native support window. Fast preview scales the window but retains internal target-pixel Gaussians, so native export is recalculated. Noise gate sigma uses working linear input units. Statistical exclusions remove actual NAFE kernel samples, independently of the experimental AEL support-separation toggle.

NRGF adapts AEL continuous radial statistics through 1.4.1: initial annuli 2 native pixels, median/MAD, minimum 12 samples and no profile smoothing. Its inner radius starts at one reference-disk radius; there is no outer-radius cutoff. Sparse/constant annuli without measurable angular spread remain transparent. Profile smoothing and minimum samples are advanced controls. Signed input is supported. It is independent of FNRGF; both can be active.

MGN sigmas are **1.25, 2.5, 5, 10, 20, 40 native pixels**, weights 1, gamma 3.2, k 0.7, h 0.7 and truncation 3. Preview scales sigmas down internally; sliders retain native units. Both complete and masked paths rescale extreme input units before local normalization and clipping; masked transport values never set that scale.

NRGF layers use AEL 1.4.1 shared-angle chaining: when neighboring annuli cover different angular cells, profile and spread changes are measured on their common observed angles. Runs containing only complete annuli retain the observed-annulus result; partial annuli earlier in a run can introduce an accumulated offset in legacy chaining. Missing pixels remain undefined. The direct `nrgf_normalize` API keeps `partial_annuli='observed'` by default; application layers explicitly select `'chain'` and record it in their mapping metadata.

Expert offers an opt-in **Anchored shared-angle chain (EIP)** variant (`chain_anchored`). In each contiguous usable run, it subtracts the cumulative chain correction at the first genuinely complete annulus, separately for the brightness profile and residual spread. Eligibility requires complete coverage flags and statistical samples in all 360 angular sectors; sparse-annulus coverage flags alone cannot establish an anchor. With no eligible annulus, the run retains legacy chaining. Runs without a positive, finite correction statistic retain the existing uncorrected model for that statistic. Mapping metadata records `operator_revision=eip-chain-anchor-1`, per-run anchor bins (target-pixel radius divided by ring width), correction-term validity, and the legacy fallback. Empty/short unusable runs do not produce anchor records.

This extension uses only the already stacked linear HDR, reference geometry and statistical mask. Output-only targets cannot select an anchor, observed validity remains separate, and missing radiance is never filled. It does not process individual exposures or change the master, other numerical branches, prominence RGB/alpha, or blend masks. Anchored output intentionally differs from upstream AEL chaining; it is not a claim of recovered resolution or scientific detail. Legacy chaining remains the new-session and omitted-parameter default. Fast preview and native export use the same selected mode, but resampling can change anchor availability and statistics, so preview is approximate. Changing the mode invalidates only the NRGF numerical layer; opacity only recomposes.

Validation on 5 November 2026: all 458 repository tests passed, including 15 focused NRGF tests. The native 5801 × 4596 handoff HDR green-channel result matched the isolated experimental anchor exactly, with the source SHA-256 unchanged; the complete-annulus anchor was bin 152 at 2 native pixels per bin. Synthetic PSB channel/composite verification and an offscreen Expert-selector layout check also passed. This is numerical integration validation, not native GUI/Photoshop acceptance or independent scientific-detail certification.

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

Explicit statistics masks now reach layer construction. Continuous FNRGF and RHEF distinguish samples used to estimate models from finite observed targets: excluded targets are evaluated only inside populated radial model ranges. Excluded intensities cannot affect those models or FNRGF's display normalization. Missing pixels and undefined/sparse models remain transparent. Item 33 also has operator-specific target evaluation for NRGF, compatible radial modes and local filters, as described below. AEL compatibility support remains the default, with a separate opt-in policy; merely forcing alpha to one would expose undefined values.

Finite zero/negative observations remain distinct from missing data. Background correction includes them; positive-only logarithmic ACHF/WOW support remains a separate operator restriction (item 34).

Item 33 follow-up: NRGF now evaluates excluded observed targets from its fitted continuous profile and spread, using only the selected samples to choose models and display scale. Compatible FNRGF evaluates its Fourier model at observed targets separately from sector fitting; compatible RHEF evaluates its empirical rank curve without adding targets to the rank population. Defaults with identical masks retain the reference results. Local and AEL logarithmic support rules are described below; no missing observations are reconstructed.

Local item-33 support: MGN and standard/adjustable WOW now estimate neighborhoods, power, noise and display scaling from sample support, while evaluating finite observed targets separately. Adaptive ACHF omits excluded central statistical weights and requires accepted observed neighbor pairs; undefined targets remain transparent. Tangential extras use their measured intensity against the observed angular background. Larson–Sekanina extras require complete observed shifted footprints. Display scales exclude excluded targets, so their intensity cannot renormalize neighbors. Legacy single-filter numerical dispatch retains its prior exclusion/bypass behavior unless separate targets are requested internally for layers.

**Experimental AEL support separation** is opt-in and saved in recipes; older recipes default off. The compatibility path still uses the common statistical mask as operator support. In experimental mode, AEL angular and guided WOW retain observed positive operator samples and use exclusions for display-scale statistics; isotropic ACHF also excludes them from radial-profile fitting. New radial targets need a populated model annulus. This preserves the original operators’ sampled observations instead of interpreting statistical exclusions as missing data. Bright excluded structures can still affect neighboring kernel responses, so this mode is not a halo-removal guarantee. Missing/nonpositive inputs stay outside AEL operator support.

Same-mask image/alpha parity passes for all three AEL ACHF variants and guided WOW. A fixed faint-detail injection has positive response in the restored sector; independent-noise correlations there were 0.090, 0.017, 0.186 and 0.019 for ISO 01, ISO 04, angular and WOW. These controls qualify an experiment on one synthetic scene, not an astrophysical or native-camera validation; the default remains compatibility mode.

## Presentation colour layers

Above the RGB Color layer, General warmth provides an RGB-wide baseline,
Corona warmth adds enhanced coronal excess, and Reduce green sky suppresses
an adjustable 0–100% (default 75%) of positive G − (R+B)/2 only in supported sky. All use Normal RGB16 targets
with separate editable alpha16 masks. Coverage is measured before tinting and
is independent of warmth strengths. Unsupported sky sampling disables the
masked stages, while general warmth remains available. Original prominence
RGB and masks are composed afterward and keep their independent colours.
Neutral/off settings retain the historical layer list and corona-only pixels.

## Optional revised normalization

The global Filter Statistics & Normalization selector keeps Compatible as default. Revised (experimental) uses fixed zero-centered signed detail for ACHF/Tangential and revised continuous FNRGF model/encoding. Layer order, blend modes and missing-data alpha remain unchanged. Contrast differs; other filters and reference-compatible FNRGF retain their original paths. See [method and extensive validation](revised-filter-normalization.md).

Tangential can independently select [source-relative signed contrast](tangential-source-relative.md). It reuses the original operator and alpha, replaces only encoding, and overrides global normalization for this layer. Neither opacity nor unrelated normalization toggles recompute an unchanged source-relative result.
