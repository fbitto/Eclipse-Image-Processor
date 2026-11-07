# CoronaHDR visual consistency — Codex handoff

Prepared 6 November 2026 from the current working trees, including uncommitted changes. This is a reference for future work, not a record of an implemented CoronaHDR redesign.

## Task and working agreement

Work in `/Users/franciscobitto/Proyectos/CoronaHDR`. The user wants CoronaHDR to have a similar look and feel to Eclipse Image Processor, so the applications feel consistent. Use `/Users/franciscobitto/Proyectos/Eclipse-Image-Processor-publicacion` as the visual and interaction reference. Read each project's `AGENTS.md` before working there.

Keep CoronaHDR's identity, HDR workflow and scientific behavior. Make the smallest complete UI change that achieves consistency. Reuse its existing PySide6 widgets and process orchestration. Do not introduce a shared package, a new GUI framework or a dependency between the two repositories. This request is a design direction; it does not require copying Eclipse's enhancement filters or export workflow.

## Where to look first

All reference paths below are relative to the Eclipse Image Processor repository:

| Question | Authoritative implementation |
| --- | --- |
| Application style and startup | `main.py:main`, `config.py:LIGHTROOM_QSS` — Fusion style plus global QSS |
| Main layout and action hierarchy | `gui/app.py:EclipseProcessorApp._build_ui` |
| Sidebar surfaces, buttons, checkboxes | `gui/components.py:PANEL_CONTENT_STYLE`, `BUTTON_STYLE`, `CHECKBOX_STYLE` |
| Expand/collapse and independent enable state | `gui/components.py:CollapsibleSection` |
| Scroll-safe inputs | `gui/components.py:ScrollSafeSlider`, `ScrollSafeComboBox`, `_scroll_sidebar` |
| Parameter row, value editing, defaults | `gui/factories.py:create_slider`, `update_slider_display`, `set_parameter_title` |
| Uppercase group headings | `gui/factories.py:create_filter_group` |
| Tooltip presentation and dismissal | `gui/components.py:InWindowTooltips` |
| Image canvas and physical-pixel zoom | `gui/image_view.py:ImageView` |
| Progressive disclosure | `gui/ui_levels.py`, `docs/ui-levels-20261103.md` |
| Icons and platform formats | `assets/README.md`, `utils/helpers.py`, platform builders |

Read local widget styles as well as the global QSS: sidebar controls override the older, brighter global defaults. Existing screenshots and dated reports may show retired controls. Current source wins. Preserve attribution/licence requirements for any copied code or artwork.

## Visual specification from the current source

The overall character is a restrained, dense, neutral-dark photographic workspace. The image is dominant; control panels use subtle borders and small corner radii. Use color sparingly for state and warnings.

| Role | Current reference |
| --- | --- |
| Main workspace/sidebar | `#2b2b2b` |
| Image canvas | `#1c1c1c` |
| Section header / inset field | `#303030` |
| Expanded section content | `#383838` |
| Regular sidebar button | `#3c3c3c`, text `#dddddd`, border `#555555` |
| Button hover | `#494949`, border `#777777` |
| Button pressed/checked | `#575757`, border `#999999` |
| Button disabled | `#303030`, text `#777777`, border `#444444` |
| Parameter labels | `#bbbbbb` |
| Secondary labels/headings | `#aaaaaa` |
| Numeric values / section titles | `#dddddd` |
| General global text | `#ffffff` |
| Checked checkbox / attention | `#e5a00d`, checkbox border `#f5b025` |
| Initial informational status | `#9cdcfe` |
| Success / failure status in source | `#00ff00` / `#ff3333` (some failures use `#cc3335`) |
| Tooltip | background `#151a21`, text `#f5f7fa`, border `#8796a8` |

Most controls use 11 px text and the system font; section titles use 12 px, weight 500. Group headings use uppercase 10 px text, weight 600 and 0.8 px letter spacing. Numeric value editors use Qt's system fixed font. These are source values, not a reason to sacrifice legibility or clip content under OS scaling.

Reference dimensions:

- Main window starts at 1180 × 780, minimum 960 × 600; outer margins and main horizontal gap are 12 px.
- Large viewer on the left; fixed 380 px control sidebar on the right. Sidebar margins/gaps are 6 px, with a persistent status/action header above a frameless scrolling controls area.
- Section header margins are 8/4/8/4 px; expanded content margins are 8/6/8/8 px. Thin separators and 2–4 px control radii; sidebar outer radius is 6 px.
- Parameter rows: 126 px wrapping name, flexible slider with minimum 70 px, right-aligned value editor at least 58 px, 7 px gaps. Value width grows to fit formatted content.
- Slider groove is 3 px, dark `#252525` with `#666666` border; handle is 10 px wide, `#b0b0b0`, dark border, lighter on hover. No colored filled track.
- Active checkboxes have 13 × 13 px indicators. Sidebar buttons use 4/6 px padding and weight 500.

CoronaHDR has wider paths and a six-column frame table. Preserve usable space for them: retain a resizable splitter or give the table a separate review area rather than force everything into a 380 px column. Matching surfaces, typography, grouping and interactions matters more than duplicating every dimension.

## Interaction conventions

- Group controls by task. Eclipse uses Preparation, enhancement groups, Appearance and Export. Adapt the grouping to CoronaHDR's import, frame review, HDR build and output tasks.
- Collapse/expand is separate from enable/bypass. Collapsing must not change processing; bypassing retains parameter values and allows configuration.
- Wheel/trackpad motion over sidebar sliders and combos scrolls the panel rather than changing a parameter, even when focused. Keyboard and deliberate pointer editing remain available.
- Sliders pair with editable physical values and units. Reject nonfinite or out-of-range edits, restore the displayed valid value, and retain keyboard access. Double-click restores that parameter's default.
- Explain consequential controls with tooltips. Eclipse's opaque in-window tooltip waits 800 ms, stays within the window and dismisses on interaction or deactivation. Port only if needed; avoid copying the whole application to reproduce it.
- Keep processing state visible in text. Disable unavailable actions, expose cancellation while busy, and do not report ready before the requested operation finishes. Color supplements the message.
- Eclipse offers Fit, 50%, 100% and 200%, with drag/scroll/arrow-key pan at fixed zoom. Native zoom is defined against physical screen pixels. If CoronaHDR gains these controls, implement real matching behavior; a styling pass alone does not require new zoom features.
- Preserve clear preview-versus-output wording. CoronaHDR's inspection stretch, gray missing pixels and camera RGB declaration are meaningful scientific information.

## CoronaHDR-specific starting points and boundaries

Inspected files in the target repository:

- `src/coronahdr/desktop.py`: `CoronaWindow`, `path_row`, `inspection_preview`, `launch`. Current window is 1240 × 850, controls/table on the left and preview on the right, in a `QSplitter` initially sized `[700, 540]`. It has a pale warning panel and a `#202020` preview. This is the main styling/layout entry point.
- `src/coronahdr/desktop_import.py`, `desktop_folders.py`: inspect their dialogs for consistency before declaring the desktop complete.
- `src/coronahdr/desktop_jobs.py`: preserve job behavior; desktop processing uses `QProcess`. No thread-model rewrite is needed for visual consistency.
- `tests/test_desktop.py`, `docs/desktop.md`, `README.md`: inspect and update when changed behavior or launch instructions require it.

Read the current code again before editing; this handoff is a dated snapshot. Start by applying Fusion and a small local stylesheet using the effective reference styles. Extend coverage to CoronaHDR's table headers, selection, line edits, read-only logs, progress bars, warning panel and dialogs, which the reference sidebar styles alone do not cover. Use readable dark warning surfaces and explicit warning text. Reorganize the preview and controls only as needed to meet the visual goal without making frame review harder.

Preserve CoronaHDR's repository rules:

- Python **3.14.8 through uv**; retain `.python-version`, `uv.lock` and `python-downloads = "never"`.
- Generated images, caches, diagnostics, previews and scratch files belong under `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work`, using the existing `artifacts/` link. The Astro volume must be connected. Do not replace the link or store large generated files on the internal disk.
- Original Lights, Bias and Flats remain unchanged. Source discovery excludes `CoronaHDR_Work`.
- Do not change radiometric calculations, masks, geometry, source selection, output data, job cancellation or scientific provenance as a side effect of styling.
- Preserve uncommitted user work in both repositories. Do not import Eclipse's `gui`/`config` modules into CoronaHDR at runtime.

## Completion checks for the implementing Codex session

1. Inspect both applications side by side on the target OS; compare surfaces, text hierarchy, control density and state feedback. Check OS scaling, resize, long paths, table headers, dropdowns, tooltips and keyboard focus for clipping or illegibility.
2. Exercise CoronaHDR with no prepared run and with a prepared run: import dialog, frame selection, method changes, warnings, processing, cancellation, completion and opening the output folder. Preserve the inspection-preview explanation.
3. Run the relevant desktop tests first, then required regression checks (`uv run pytest -q` per the target README) with the required Python and external storage available. Add a small behavior test only for new nontrivial interaction logic.
4. Capture before/after screenshots under the target's approved external artifact directory. Report checks actually performed and any platform or data-dependent checks still outstanding.

## Pasteable kickoff prompt

> Work on CoronaHDR at `/Users/franciscobitto/Proyectos/CoronaHDR`. Read its AGENTS.md and the handoff at `/Users/franciscobitto/Proyectos/Eclipse-Image-Processor-publicacion/docs/coronahdr-codex-handoff.md`. Make its desktop UI feel consistent with Eclipse Image Processor using the current source references in that handoff. Preserve CoronaHDR's HDR workflow, scientific behavior and external-storage rules. Inspect existing code and local changes first, make the smallest complete implementation, and verify the UI and relevant tests. Use the reference repository to answer detailed styling and interaction questions. Report what changed and what you actually checked.

## Evidence limits

This handoff was prepared by reading source and documentation in both repositories. Neither application was launched, no live visual comparison was performed, and no tests were run for this documentation-only task. No CoronaHDR files or application behavior were changed.
