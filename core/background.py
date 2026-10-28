"""Robust additive sky planes in original linear units; retain the sampled sky level."""
import numpy as np
from .image_data import resize_observed, observed_bounds


def sample_allowed(point,shape,geometry,radius):
    h,w=shape;cx,cy,sr=geometry;x,y=point
    half=max(2,min(32,int(min(h,w)/200)))
    return (half<=x<w-half and half<=y<h-half and
            np.hypot(x-cx,y-cy)-np.sqrt(2)*half>=radius*sr)


def sample_grid(shape, geometry, radius, count):
    h,w=shape;cx,cy,sr=geometry
    if not np.isfinite([cx,cy,sr,radius]).all() or sr<=0 or radius<1:
        raise ValueError('Background extraction needs valid geometry and an exclusion radius >= 1')
    half=max(2,min(32,int(min(h,w)/200)))
    points=[]
    for y in np.linspace(half,h-half-1,count):
        for x in np.linspace(half,w-half-1,count):
            if sample_allowed((x,y),shape,geometry,radius):
                points.append((int(round(x)),int(round(y))))
    return points


def equalize_background(base, geometry, radius, grid, points=None, enabled=True, degree=1):
    """Fit patch medians per channel, subtract spatial variation, and preserve missing/zero pixels.

    Coordinates are native pixel centres normalized to [-1,1]. One shared robust
    weight per RGB sample protects channel consistency. Reference is the weighted
    sample centroid; the mean polynomial basis preserves the fitted sky at the accepted samples.
    """
    if type(degree) is not int or degree not in (1,2):
        raise ValueError('Background degree must be 1 or 2')
    minimum=6 if degree==1 else 12
    if not enabled:
        return dict(base,points=points,report=None,display_bounds=base.get('display_bounds') or observed_bounds(base['full']))
    source=base['rgb'] if base['rgb'] is not None else base['full']
    a=np.asarray(source)
    h,w=a.shape[:2];cx,cy,sr=geometry
    if not np.isfinite([cx,cy,sr,radius]).all() or sr<=0 or radius<1:
        raise ValueError('Background extraction needs valid geometry and exclusion radius')
    if points is None:points=sample_grid((h,w),geometry,radius,grid)
    half=max(2,min(32,int(min(h,w)/200)))
    samples=[];accepted=[]
    for x,y in points:
        if not sample_allowed((x,y),(h,w),geometry,radius):continue
        patch=a[y-half:y+half+1,x-half:x+half+1]
        valid=np.isfinite(patch).all(axis=-1) if patch.ndim==3 else np.isfinite(patch)
        valid &= np.any(patch!=0,axis=-1) if patch.ndim==3 else patch!=0
        if valid.sum()<.9*valid.size:continue
        samples.append(np.atleast_1d(np.median(patch[valid],axis=0)))
        accepted.append((x,y))
    if len(samples)<minimum:
        raise ValueError(f'Need at least {minimum} valid sky samples; reduce exclusion radius or edit the sample grid')
    xy=np.asarray(accepted,float)
    xy=(xy+.5)/np.array([w,h])*2-1
    if np.any(np.ptp(xy,axis=0)<.4):
        raise ValueError('Sky samples must cover both image axes; spread them around the corona')
    design=np.column_stack([np.ones(len(xy)),xy]);values=np.asarray(samples,float)
    if degree==2:
        u,v=xy.T
        design=np.column_stack([design,u*u,u*v,v*v])
    weights=np.ones(len(xy))
    for _ in range(12):
        root=np.sqrt(weights)[:,None]
        coefficients,_,rank,_=np.linalg.lstsq(design*root,values*root,rcond=None)
        if rank<design.shape[1] or np.linalg.cond(design*root)>1e6:
            raise ValueError('Sky samples are collinear or insufficiently distributed')
        residual=values-design@coefficients
        center=np.median(residual,axis=0)
        scale=np.maximum(1.4826*np.median(np.abs(residual-center),axis=0),
                         np.maximum(np.max(np.abs(values),axis=0)*1e-7,1e-12))
        distance=np.max(np.abs((residual-center)/scale),axis=1)/4.685
        updated=np.where(distance<1,(1-distance**2)**2,0)
        if np.count_nonzero(updated) < minimum:
            raise ValueError('Too few uncontaminated sky samples remain after robust rejection')
        if np.max(np.abs(updated-weights))<1e-4:break
        weights=updated
    reference=np.average(xy,axis=0,weights=weights)
    reference_basis=np.average(design,axis=0,weights=weights)
    corrected=np.empty(a.shape,np.float32)
    xs=(np.arange(w)+.5)/w*2-1-reference[0]
    for first in range(0,h,128):
        last=min(h,first+128)
        ys=(np.arange(first,last)+.5)/h*2-1-reference[1]
        slope=(ys[:,None,None]*coefficients[2]+xs[None,:,None]*coefficients[1])
        if degree==2:
            u=xs+reference[0];v=ys+reference[1]
            slope+=(u[None,:,None]**2-reference_basis[3])*coefficients[3]
            slope+=(v[:,None,None]*u[None,:,None]-reference_basis[4])*coefficients[4]
            slope+=(v[:,None,None]**2-reference_basis[5])*coefficients[5]
        block=a[first:last]
        if a.ndim==2:slope=slope[...,0]
        valid=np.isfinite(block).all(axis=-1) if a.ndim==3 else np.isfinite(block)
        valid &= np.any(block!=0,axis=-1) if a.ndim==3 else block!=0
        corrected[first:last]=block
        np.subtract(block,slope,out=corrected[first:last],where=valid[...,None] if a.ndim==3 else valid,casting='unsafe')
    rgb=corrected if a.ndim==3 else None
    mono=np.empty((h,w),np.float32) if rgb is not None else corrected
    if rgb is not None:
        for first in range(0,h,128):
            block=rgb[first:first+128]
            mono[first:first+128]=.299*block[...,0]+.587*block[...,1]+.114*block[...,2]
    preview=resize_observed(mono,(base['preview'].shape[1],base['preview'].shape[0]))
    return dict(base,full=mono,rgb=rgb,preview=preview,display_bounds=observed_bounds(mono),points=accepted,
                report=dict(method='robust RGB/mono polynomial; mean fitted sky preserved',degree=degree,
                            basis=['1','u','v'] if degree==1 else ['1','u','v','u^2','u*v','v^2'],
                            reference_basis=reference_basis.tolist(),
                            coordinate_basis='u=2*(x+0.5)/width-1; v=2*(y+0.5)/height-1',
                            coefficients=coefficients.tolist(),reference=reference.tolist(),
                            samples=len(accepted),inliers=int(np.count_nonzero(weights)),
                            residual_rms=np.sqrt(np.average((values-design@coefficients)**2,axis=0,weights=weights)).tolist(),
                            sample_patch_side=2*half+1,
                            exclusion_radius=float(radius),preserve_sky_level=True))
