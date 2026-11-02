"""The threaded AEL ACHF (isotropic bands, chunked spline, angular strips) is bit-identical to the previous code."""
from types import SimpleNamespace
import unittest

import cv2
import numpy as np
from scipy.interpolate import LSQUnivariateSpline

import core.ael_achf as achf
from core.parallelism import filter_budget


def _old_radial_log_residual(luminance, valid, geometry):
    """The previous implementation, kept verbatim as the reference."""
    a = np.asarray(luminance, np.float32)
    m = valid & np.isfinite(a) & (a>0)
    r = geometry.radius_map()
    m &= r>0
    ri = np.floor(r[m]).astype(int)
    order = np.argsort(ri,kind='stable'); cnt = np.bincount(ri); cuts=np.r_[0,np.cumsum(cnt)]
    values=np.log(a[m])[order]
    bins=np.flatnonzero(cnt>=12)
    med=np.array([np.median(values[cuts[i]:cuts[i+1]]) for i in bins])
    lr_values=np.log(r[m].astype(np.float64))[order]
    lr=np.array([np.mean(lr_values[cuts[i]:cuts[i+1]]) for i in bins])
    candidates=np.log(geometry.sun_radius_px*np.array([1.03,1.06,1.10,1.15,1.22,1.32,1.45,1.65,1.95,2.4,3,3.8,4.8,6]))
    knots=[v for v in candidates if lr[3]<v<lr[-4]]
    while True:
        try:
            fit=LSQUnivariateSpline(lr,med,knots,w=np.sqrt(cnt[bins]),k=3)
            break
        except ValueError:
            if not knots: raise
            knots=knots[::2] if len(knots)>1 else []
    ln=np.zeros(a.shape,np.float32); ln[m]=np.log(a[m])
    profile=fit(np.log(np.clip(r,np.exp(lr[0]),np.exp(lr[-1]))))
    return np.where(m,ln-profile,np.nan).astype(np.float32)


def _old_isotropic(luminance, valid, geometry, sigmas, outer_sigma):
    residual=_old_radial_log_residual(luminance,valid,geometry)
    m=np.isfinite(residual)
    detail=np.zeros(residual.shape,np.float32)
    for s in sigmas:
        detail += (residual-achf.normalized_gaussian(residual,m,s,min_support=.01))/len(sigmas)
    if outer_sigma:
        detail=achf.normalized_gaussian(detail,m,outer_sigma,min_support=.01)
    detail[~m]=np.nan
    return detail


def _old_angular_highpass(image, mask, cx, cy, radius, sigma_deg):
    """The previous single-thread implementation, kept verbatim as the reference."""
    from scipy.ndimage import gaussian_filter1d
    h, w = image.shape
    r0 = .5*radius
    r1 = float(np.hypot(max(cx,w-cx),max(cy,h-cy)))
    nr = int(round(r1-r0))+1
    na = int(np.ceil(2*np.pi*r1/1.5))
    radii = np.linspace(r0,r1,nr)
    pa = (np.arange(na)+.5)*(360/na)
    direction = np.radians((-pa)%360)
    ux,uy = np.sin(direction),-np.cos(direction)
    signal = np.where(mask,image,0).astype(np.float32)
    support = mask.astype(np.float32)
    polar = np.full((nr,na),np.nan,np.float32)
    def remap(values, weights, x, y):
        kw = dict(borderMode=cv2.BORDER_CONSTANT,borderValue=0.)
        observed = cv2.remap(weights,x,y,cv2.INTER_LINEAR,**kw)
        samples = cv2.remap(values,x,y,cv2.INTER_LINEAR,**kw)
        return np.where(observed>=.9999,samples,np.nan).astype(np.float32)
    for first in range(0,nr,64):
        rs = radii[first:first+64,None]
        x = (cx+rs*ux).astype(np.float32)
        y = (cy+rs*uy).astype(np.float32)
        samples = remap(signal,support,x,y)
        ok = np.isfinite(samples)
        sigma = sigma_deg/(360/na)
        num = gaussian_filter1d(np.where(ok,samples,0),sigma,axis=1,mode='wrap')
        den = gaussian_filter1d(ok.astype(np.float32),sigma,axis=1,mode='wrap')
        smooth = np.where(ok & (den>=.3),num/np.maximum(den,1e-12),np.nan)
        polar[first:first+len(rs)] = samples-smooth
    padded = np.concatenate([polar[:,-4:],polar,polar[:,:4]],axis=1)
    weights = np.isfinite(padded).astype(np.float32)
    values = np.nan_to_num(padded)
    output = np.full(image.shape,np.nan,np.float32)
    for first in range(0,h,128):
        y = (np.arange(first,min(h,first+128))-cy)[:,None]
        x = (np.arange(w)-cx)[None,:]
        r = np.hypot(x,y)
        pa = (-np.degrees(np.arctan2(x,-y)))%360
        ri = ((r-r0)/(r1-r0)*(nr-1)).astype(np.float32)
        ci = (pa/(360/na)-.5+4).astype(np.float32)
        output[first:first+len(y)] = remap(values,weights,ci,ri)
    output[~mask] = np.nan
    return output


class ThreadedAchfTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(5)
        self.cx, self.cy, self.radius = 171.3, 140.6, 30.
        yy, xx = np.mgrid[:283, :331]
        self.r = np.hypot(xx-self.cx, yy-self.cy).astype(np.float32)
        theta = np.arctan2(yy-self.cy, xx-self.cx)
        self.image = ((1 + 400*(np.maximum(self.r, 1)/self.radius)**-3*(1+.2*np.cos(9*theta)))
                      * np.exp(.03*rng.standard_normal(self.r.shape))).astype(np.float32)
        self.mask = (self.r > self.radius) & np.isfinite(self.image)
        self.mask[:, 320:] = False
        self.geometry = SimpleNamespace(sun_radius_px=self.radius, radius_map=lambda: self.r)

    def test_isotropic_bands_and_chunked_spline_match_the_previous_code(self):
        sigmas, outer = (1., 2., 4., 8., 16.), 1.5
        expected = _old_isotropic(self.image, self.mask, self.geometry, sigmas, outer)
        original = achf.SPLINE_CHUNK_SAMPLES
        try:
            achf.SPLINE_CHUNK_SAMPLES = 331*7                    # several chunks, one not full
            for workers in (1, 2, 8):
                with self.subTest(workers=workers), filter_budget(workers):
                    detail, _ = achf.achf_isotropic(self.image, self.mask, self.geometry,
                                                    sigmas=sigmas, outer_sigma=outer)
                    np.testing.assert_array_equal(detail, expected)
        finally:
            achf.SPLINE_CHUNK_SAMPLES = original

    def test_angular_strips_match_the_previous_code(self):
        logged = np.where(self.mask, np.log(np.maximum(self.image, 1e-30)), np.nan)
        expected = _old_angular_highpass(logged, self.mask, self.cx, self.cy, self.radius, 4.)
        for workers in (1, 8):
            with self.subTest(workers=workers), filter_budget(workers):
                np.testing.assert_array_equal(
                    achf.angular_highpass(logged, self.mask, self.cx, self.cy, self.radius, 4.), expected)


if __name__ == '__main__':
    unittest.main()
