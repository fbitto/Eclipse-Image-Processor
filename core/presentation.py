"""Display-only transforms shared by preview and full-resolution export."""
import numpy as np
from .image_data import normalize_observed


def apply_ghs(mat, D, SP, b, BP=0., LP=0., HP=1., WP=1.):
    """Reference GHS followed by an optional, separate linear BP/WP adjustment.

    D is the original UI stretch factor ln(D_formula+1). BP/WP do not modify
    the five-parameter GHS curve; their default 0/1 leaves it unchanged.
    """
    from .ghs import generalized_hyperbolic_stretch
    if not np.isfinite([BP, WP]).all() or not -1 <= BP < WP <= 2:
        raise ValueError('Linear display adjustment requires -1 <= BP < WP <= 2')
    result = generalized_hyperbolic_stretch(mat, D, SP, b, LP, HP)
    return np.clip((result-BP)/(WP-BP), 0., 1.)


def stretch_image(image, settings):
    """Normalize finite mono data then apply the selected display curve once."""
    a = normalize_observed(image)
    mode = settings.get('mode', 'asinh')
    strength = float(settings.get('strength', 1.))
    if mode == 'log':
        k = 10. ** (strength / 10.)
        return np.log1p(k * a) / np.log1p(k)
    if mode == 'ghs':
        return apply_ghs(a, strength, settings.get('sp', .1),
                         settings.get('b', 0.), settings.get('bp', 0.),
                         settings.get('lp', 0.), settings.get('hp', 1.),
                         settings.get('wp', 1.))
    if mode != 'asinh':
        raise ValueError('Unknown display stretch')
    return a if strength <= 0 else np.arcsinh(a * strength) / np.arcsinh(strength)


def render_presentation(processed, original, settings):
    """The comparison button is transient; exported images always use Reveal."""
    alpha = float(settings.get('blend', 1.))
    if not np.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError('Reveal opacity must be between zero and one')
    if alpha == 0:
        return stretch_image(original, settings)
    if alpha == 1:
        return stretch_image(processed, settings)
    return (alpha * stretch_image(processed, settings)
            + (1 - alpha) * stretch_image(original, settings))
