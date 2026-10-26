"""丝印效果图（vtk 离屏渲染，带深度缓冲）：钣金件米白喷粉 + 黑色丝印（丝印按贴图贴在面板外表面）。
输出 png/30_silk_front.png（正视）、30_silk_iso.png（前斜上方）、30_silk_slant.png（垂直斜面看操作区）。
用法：main(items) —— items 为 assembly.build() 的返回值；不传就现建（约 5 min）。"""
import math
import numpy as np
import vtk
from vtk.util import numpy_support as ns
import assembly_panel as AP
import silkscreen as S

POWDER = (0.913, 0.882, 0.812)               # 米白喷粉（约 RAL 9001）
INK = (0.07, 0.07, 0.07)
POWDER_PARTS = ("front_shell", "chin_tray", "side_cover")
SILK_OFF = 0.2                               # 丝印贴图离面板外表面（整机场景深度范围大，0.03 分不出前后）
PPM = 16                                     # 丝印贴图分辨率（像素 / mm）


def _polydata(verts, tris):
    pts = vtk.vtkPoints(); pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(verts, dtype=float), deep=True))
    cells = vtk.vtkCellArray()
    conn = np.hstack([np.full((len(tris), 1), 3), tris]).astype(np.int64).ravel()
    cells.SetCells(len(tris), ns.numpy_to_vtkIdTypeArray(conn, deep=True))
    pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
    nf = vtk.vtkPolyDataNormals(); nf.SetInputData(pd); nf.SetFeatureAngle(35); nf.SplittingOn(); nf.Update()
    return nf.GetOutput()


def _shape_pd(shape, tol=0.08):
    vs, ts, off = [], [], 0
    for s in shape.vals():
        v, t = s.tessellate(tol, 0.15)
        if not t:
            continue
        vs.append(np.array([[p.x, p.y, p.z] for p in v])); ts.append(np.array(t) + off); off += len(v)
    return _polydata(np.vstack(vs), np.vstack(ts)) if vs else None


def _silk_texture(polys, x0, y0, x1, y1):
    """丝印多边形按非零规则栅格化（和制版一样，字体轮廓的微小自交不影响）→ RGBA 贴图，墨处不透明"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from fig_silkscreen import poly_path
    w, h = int((x1 - x0) * PPM), int((y1 - y0) * PPM)
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes((0, 0, 1, 1)); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
    fig.patch.set_alpha(0)
    ax.add_patch(PathPatch(poly_path(polys), fc="black", ec="none"))
    fig.canvas.draw()
    a = np.asarray(fig.canvas.buffer_rgba())[::-1, :, 3].copy()                  # vtk 图像第 0 行在下
    plt.close(fig)
    rgba = np.zeros(a.shape + (4,), np.uint8)
    rgba[..., :3] = (np.array(INK) * 255).astype(np.uint8); rgba[..., 3] = a
    img = vtk.vtkImageData(); img.SetDimensions(a.shape[1], a.shape[0], 1)
    arr = ns.numpy_to_vtk(rgba.reshape(-1, 4), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    arr.SetNumberOfComponents(4); img.GetPointData().SetScalars(arr)
    tex = vtk.vtkTexture(); tex.SetInputData(img); tex.InterpolateOn(); tex.MipmapOn(); tex.SetColorModeToDirectScalars()
    return tex


def _to3d(face, x, y):
    if face == "front":
        return (x, -2 - SILK_OFF, y)
    yy, zz = AP.slant_pt(y, -SILK_OFF)
    return (x, yy, zz)


def silk_actors():
    """每个面一块贴图四边形"""
    out = []
    for face, polys in S.elements():
        lo, hi = S.bbox(polys)
        x0, y0, x1, y1 = lo[0] - 1, lo[1] - 1, hi[0] + 1, hi[1] + 1
        ps = vtk.vtkPlaneSource()
        ps.SetOrigin(*_to3d(face, x0, y0)); ps.SetPoint1(*_to3d(face, x1, y0)); ps.SetPoint2(*_to3d(face, x0, y1))
        m = vtk.vtkPolyDataMapper(); m.SetInputConnection(ps.GetOutputPort())
        a = vtk.vtkActor(); a.SetMapper(m); a.SetTexture(_silk_texture(polys, x0, y0, x1, y1))
        pr = a.GetProperty(); pr.SetAmbient(0.3); pr.SetDiffuse(0.7); pr.SetSpecular(0.0)
        out.append(a)
    return out


def _actor(pd, rgb, alpha=1.0, spec=0.15, amb=0.25):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m)
    pr = a.GetProperty(); pr.SetColor(*rgb); pr.SetOpacity(alpha)
    pr.SetAmbient(amb); pr.SetDiffuse(1.0 - amb * 0.8); pr.SetSpecular(spec); pr.SetSpecularPower(20)
    return a


def scene(items):
    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    for name, shp, col, grp in items:
        pd = _shape_pd(shp)
        if pd is None:
            continue
        powder = name.startswith(POWDER_PARTS)
        if powder:                                                    # 喷粉哑光：环境光多一些，竖直面不发灰
            ren.AddActor(_actor(pd, POWDER, 1.0, 0.03, 0.45))
        else:
            ren.AddActor(_actor(pd, col[:3], col[3]))
    for a in silk_actors():
        ren.AddActor(a)
    ren.SetUseDepthPeeling(True); ren.SetMaximumNumberOfPeels(8)
    return ren


def shot(ren, fname, focal, direction, up, scale, size=(2000, 2000)):
    """平行投影：focal 看向的点，direction 从物体指向相机，scale = 半个视窗高（mm）"""
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(*size); rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    cam = ren.GetActiveCamera(); cam.ParallelProjectionOn()
    d = np.array(direction, float); d /= np.linalg.norm(d)
    cam.SetFocalPoint(*focal); cam.SetPosition(*(np.array(focal) + d * 2000)); cam.SetViewUp(*up)
    cam.SetParallelScale(scale); ren.ResetCameraClippingRange()
    ren.RemoveAllLights()
    lk = vtk.vtkLightKit(); lk.SetKeyLightIntensity(0.85); lk.AddLightsToRenderer(ren)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(fname); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    rw.RemoveRenderer(ren); rw.Finalize()
    print("saved", fname, flush=True)


def main(items=None, out="png"):
    if items is None:
        import assembly as A
        items = A.build()
    ren = scene(items)
    W, H = AP.W, AP.H
    shot(ren, f"{out}/30_silk_front.png", (W / 2, 0, (H - 30) / 2), (0, -1, 0), (0, 0, 1), 250, (1800, 2200))
    az, el = math.radians(28), math.radians(18)
    shot(ren, f"{out}/30_silk_iso.png", (W / 2, 40, (H - 60) / 2),
         (math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)), (0, 0, 1), 270, (2000, 2200))
    yc, zc = AP.slant_pt(38, 0)                                        # 斜面外法向 (0, −cos33, sin33)：相机在前上方垂直斜面
    shot(ren, f"{out}/30_silk_slant.png", (W / 2, yc, zc), (0, -AP.CA, AP.SA), (0, AP.SA, AP.CA), 85, (2600, 1300))
