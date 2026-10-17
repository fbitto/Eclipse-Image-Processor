"""Display-only transforms shared by preview and full-resolution export."""
import numpy as np
from .image_data import normalize_observed


def apply_ghs(mat, D, SP, b, BP):
    D = max(0.01, float(D))
    SP = float(np.clip(SP, 0, .999))
    BP = float(np.clip(BP, 0, max(0, SP - 1e-4)))
    b = max(0, float(b))

    def evaluate(v):
        delta = v - SP
        scale = 1 + b * np.maximum(0, delta) if b > 0 else 1
        return np.arcsinh(D * delta / scale)

    denominator = evaluate(1.) - evaluate(BP)
    if abs(denominator) < 1e-7:
        return np.clip(mat, 0, 1)
    return np.clip((evaluate(mat) - evaluate(BP)) / denominator, 0, 1)


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
                         settings.get('b', 2.), settings.get('bp', 0.))
    if mode != 'asinh':
        raise ValueError('Unknown display stretch')
    return a if strength <= 0 else np.arcsinh(a * strength) / np.arcsinh(strength)


def render_presentation(processed, original, settings):
    """The comparison button is transient; exported images always use Reveal."""
    alpha = float(settings.get('blend', 1.))
    if not np.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError('Reveal opacity must be between zero and one')
    return (alpha * stretch_image(processed, settings)
            + (1 - alpha) * stretch_image(original, settings))
