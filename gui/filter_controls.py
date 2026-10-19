"""Additional numerical controls with explicit physical units and conversions."""
from PySide6.QtWidgets import QCheckBox
from .components import ScrollSafeComboBox
from .factories import create_slider_float, create_slider

# attribute, recipe key, title, min, max, default, divisor, help
CONTROLS = {
    'noise_gate': [
        ('noise_gate_sigma', 'noise_gate_sigma', 'Local sigma (preview px)', 5, 200, 30, 10., 'Gaussian sigma for local signal and residual spread, in preview pixels; scaled on export.'),
        ('noise_gate_smooth', 'noise_gate_smooth', 'Gate sigma (preview px)', 0, 200, 20, 10., 'Gaussian sigma for the attenuation map; zero disables gate smoothing.')],
    'fnrgf': [
        ('fnrgf_smooth', 'fnrgf_smooth', 'Model smoothing (preview px)', 0, 640, 80, 10., 'Radial Gaussian sigma of the continuous background model, not the final image. Zero disables smoothing.'),
        ('fnrgf_fade', 'fnrgf_fade', 'Boundary fade (preview px)', 0, 1280, 80, 10., 'Continuous mode: smooth application at the inner and outer radii without changing observed-data validity.'),
        ('fnrgf_ridge', 'fnrgf_ridge', 'Harmonic regularization', 0, 1000, 10, 1000., 'Dimensionless penalty on higher angular harmonics. Increased automatically for partial coverage; zero disables it.'),
        ('fnrgf_floor', 'fnrgf_floor', 'Minimum width fraction', 0, 100, 5, 100., 'Floor relative to typical annular spread. Continuous mode also keeps its divisor positive.'),
        ('fnrgf_robust', 'fnrgf_robust', 'Robust fit iterations', 0, 5, 2, 1., 'Continuous-model reweighting passes; zero selects ordinary regularized least squares.'),
        ('fnrgf_min_pixels', 'fnrgf_min_pixels', 'Minimum samples per sector', 1, 32, 1, 1., 'Sectors with fewer observed pixels do not constrain the model. Widths always need at least two samples; rings without three measured sector widths retain the input.'),
        ('fnrgf_mean_tail', 'fnrgf_mean_tail', 'Highest-harmonic mean weight', 0, 100, 0, 100., 'Final weight of the linearly attenuated brightness harmonics. Continuous mode preserves the DC mean unless all coefficients are removed.'),
        ('fnrgf_width_tail', 'fnrgf_width_tail', 'Highest-harmonic width weight', 0, 100, 0, 100., 'Final weight of the width harmonics. Continuous mode fits log-width and always retains its DC scale.')],
    'rhef': [
        ('rhef_upsilon_high', 'rhef_upsilon_high', 'Upper-tail exponent', 1, 500, 35, 100., 'Exponent for the upper half of the rank curve. One leaves this tail unchanged.'),
        ('rhef_min_count', 'rhef_min_count', 'Minimum samples per ring', 2, 128, 12, 1., 'Continuous mode: fewer positive samples leave the ring unprocessed.'),
        ('rhef_quantiles', 'rhef_quantiles', 'Quantile samples', 17, 1025, 257, 1., 'Continuous mode: number of quantile nodes interpolating the intensity distribution.'),
        ('rhef_noise_confidence', 'rhef_noise_confidence', 'Noise confidence (0 = off)', 0, 100, 0, 10., 'Optional blend attenuation where angular spread is near estimated noise. Adjacent-pixel noise is approximate, particularly on correlated stacks.')],
    'tangential': [
        ('tangential_arc', 'tangential_arc', 'Angular Gaussian sigma (degrees)', 1, 300, 30, 10., 'Angular blur sigma, 0.1 to 30 degrees. The corresponding arc length increases with radius.'),
        ('tangential_gain', 'tangential_gain', 'Detail gain', 0, 50, 10, 10., 'Multiplier of the signed angular residual before the separate Strength blend.'),
        ('tangential_denoise', 'tangential_denoise', 'Noise threshold (sigma)', 0, 100, 0, 10., 'Soft threshold on signed detail, using a robust adjacent-pixel noise estimate. Zero bypasses it; not calibrated detector noise.'),
        ('tangential_inner', 'tangential_inner', 'Inner radius (disk radii)', 0, 40, 10, 10., 'Start of tangential processing in reference disk radii.'),
        ('tangential_outer', 'tangential_outer', 'Outer radius (disk radii)', 11, 200, 40, 10., 'Outer processing radius in reference disk radii, used only when Limit outer radius is checked.'),
        ('tangential_fade', 'tangential_fade', 'Boundary fade (preview px)', 0, 1280, 80, 10., 'Smooth radial blend width at the application boundaries; scaled on export.')],
}


def add_controls(window):
    for family, specs in CONTROLS.items():
        section = getattr(window, 'sec_'+family)
        for attr, key, label, minimum, maximum, default, divisor, help_text in specs:
            if divisor == 1:
                slider, _ = create_slider(label, minimum, maximum, default,
                                           section.content_layout, tooltip=help_text,
                                           on_release_callback=window.dispatch_pipeline_request_if_auto)
            else:
                slider, _ = create_slider_float(label, minimum, maximum, default, divisor,
                                                section.content_layout, tooltip=help_text,
                                                on_release_callback=window.dispatch_pipeline_request_if_auto)
            slider.setObjectName('sl_'+attr)
            setattr(window, 'sl_'+attr, slider)
    window.combo_fnrgf_mode = ScrollSafeComboBox()
    window.combo_fnrgf_mode.addItem('Continuous / support-aware', 'continuous')
    window.combo_fnrgf_mode.addItem('Reference-compatible', 'legacy')
    window.combo_fnrgf_mode.setToolTip('Continuous fits use observed angular support and interpolated radial models. Compatible mode retains the original reference conventions.')
    window.sec_fnrgf.content_layout.insertWidget(0, window.combo_fnrgf_mode)
    window.combo_fnrgf_mode.currentIndexChanged.connect(window.dispatch_pipeline_request_if_auto)
    def mode_changed():
        continuous = window.combo_fnrgf_mode.currentData() == 'continuous'
        for name in ('smooth', 'fade', 'ridge', 'robust'):
            getattr(window, 'sl_fnrgf_'+name).setEnabled(continuous)
    window.combo_fnrgf_mode.currentIndexChanged.connect(mode_changed)
    mode_changed()
    window.chk_rhef_symmetric = QCheckBox('Use the same exponent for both tails')
    window.chk_rhef_symmetric.setChecked(True)
    window.chk_rhef_symmetric.setToolTip('Link the upper-tail exponent to the main Upsilon exponent. Uncheck for independent tail control.')
    window.chk_rhef_symmetric.toggled.connect(window.dispatch_pipeline_request_if_auto)
    window.sec_rhef.content_layout.addWidget(window.chk_rhef_symmetric)
    def update_rhef_controls():
        continuous = window.combo_rhef_mode.currentData() == 'continuous'
        for name in ('min_count', 'quantiles'):
            getattr(window, 'sl_rhef_'+name).setEnabled(continuous)
        window.sl_rhef_upsilon_high.setEnabled(not window.chk_rhef_symmetric.isChecked())
    window.chk_rhef_symmetric.toggled.connect(update_rhef_controls)
    window.combo_rhef_mode.currentIndexChanged.connect(update_rhef_controls)
    update_rhef_controls()
    window.chk_tangential_outer = QCheckBox('Limit outer radius')
    window.chk_tangential_outer.setToolTip('Enable an outer processing boundary; otherwise process to the observed image edges.')
    window.sec_tangential.content_layout.addWidget(window.chk_tangential_outer)
    def sync_tangential():
        window.sl_tangential_outer.setMinimum(window.sl_tangential_inner.value()+1)
        window.sl_tangential_outer.setEnabled(window.chk_tangential_outer.isChecked())
    window.chk_tangential_outer.toggled.connect(sync_tangential)
    window.chk_tangential_outer.toggled.connect(window.dispatch_pipeline_request_if_auto)
    window.sl_tangential_inner.valueChanged.connect(sync_tangential)
    sync_tangential()
    window.sl_mgn_sigmas, window.sl_mgn_weights = [], []
    for index, sigma in enumerate((1.25, 2.5, 5, 10, 20, 40)):
        for collection, title, maximum, default, help_text in (
            (window.sl_mgn_sigmas, 'sigma (preview px)', 12800, round(sigma*100), 'Gaussian scale in preview pixels, scaled for export. Each of the six scales is independently adjustable.'),
            (window.sl_mgn_weights, 'weight', 200, 100, 'Nonnegative weight of this local MGN scale. Zero disables its contribution; normalization still divides by six scales.')):
            slider, _ = create_slider_float(f'Scale {index+1} {title}', 25 if collection is window.sl_mgn_sigmas else 0,
                                            maximum, default, 100., window.sec_mgn.content_layout,
                                            tooltip=help_text, on_release_callback=window.dispatch_pipeline_request_if_auto)
            collection.append(slider)
    window.sl_wow_bilateral, _ = create_slider_float('Bilateral intensity scale', 1, 50, 10, 10.,
        window.sec_wow.content_layout, tooltip='Positive intensity sensitivity for the bilateral WOW backend (0.1 to 5); enabled only in edge-aware mode.',
        on_release_callback=window.dispatch_pipeline_request_if_auto)
    window.combo_wow_bilateral.currentIndexChanged.connect(lambda i: window.sl_wow_bilateral.setEnabled(i == 1))


def collect_controls(window):
    params = {}
    for specs in CONTROLS.values():
        for attr, key, label, minimum, maximum, default, divisor, help_text in specs:
            value = getattr(window, 'sl_'+attr).value()/divisor
            params[key] = int(value) if divisor == 1 else value
    params['rhef_upsilon_high'] = window.sl_rhef_upsilon_high.value()
    if window.chk_rhef_symmetric.isChecked():
        params['rhef_upsilon_high'] = window.sl_rhef_upsilon.value()
    if not window.chk_tangential_outer.isChecked():
        params['tangential_outer'] = 0.
    params['fnrgf_mode'] = window.combo_fnrgf_mode.currentData()
    params['mgn_sigmas'] = tuple(sl.value()/100 for sl in window.sl_mgn_sigmas)
    params['mgn_weights'] = tuple(sl.value()/100 for sl in window.sl_mgn_weights)
    params['wow_bilateral'] = window.sl_wow_bilateral.value()/10 if window.combo_wow_bilateral.currentIndex() else None
    return params
