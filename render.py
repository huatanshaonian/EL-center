"""简单正交投影 + 画家算法渲染（matplotlib），用于布局预览"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import font_manager

def _font():
    for f in font_manager.findSystemFonts():
        if any(k in f for k in ("NotoSansCJK", "wqy", "SourceHanSans", "DroidSansFallback", "msyh", "simhei")):
            return font_manager.FontProperties(fname=f)
    return None

FONT = _font()

def tess(shape, tol=0.4):
    vs, ts = [], []
    off = 0
    for sol in shape.vals():          # 整体取面片，兼容只有曲面壳的厂家模型
        v, t = sol.tessellate(tol, 0.3)
        vs.append(np.array([[p.x, p.y, p.z] for p in v])); ts.append(np.array(t) + off); off += len(v)
    if not vs:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    return np.vstack(vs), np.vstack(ts)

def subdivide(tri, maxlen=10.0):
    out = []
    stack = tri
    for _ in range(8):
        e = np.max(np.stack([np.linalg.norm(stack[:, 1] - stack[:, 0], axis=1),
                             np.linalg.norm(stack[:, 2] - stack[:, 1], axis=1),
                             np.linalg.norm(stack[:, 0] - stack[:, 2], axis=1)]), axis=0)
        small = e <= maxlen
        out.append(stack[small]); big = stack[~small]
        if len(big) == 0:
            break
        a, b, c = big[:, 0], big[:, 1], big[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        stack = np.concatenate([np.stack(x, 1) for x in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
    else:
        out.append(stack)
    return np.concatenate(out)

def view_basis(az, el):
    az, el = np.radians(az), np.radians(el)
    d = np.array([np.cos(el) * np.sin(az), -np.cos(el) * np.cos(az), np.sin(el)])  # 指向观察者
    up = np.array([0, 0, 1.0])
    r = np.cross(up, d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    return r, u, d

def draw(ax, items, az=30, el=20, maxlen=10.0):
    r, u, d = view_basis(az, el)
    light = 0.6 * d + 0.5 * np.array([0.3, -0.4, 0.8]); light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    for name, shp, col, grp in items:
        v, t = tess(shp, 0.2)
        tri = v[t]
        tri = subdivide(tri, maxlen)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1); ok = nn > 1e-12
        tri, n = tri[ok], n[ok] / nn[ok, None]
        if col[3] >= 0.99:
            keep = n @ d > -1e-6; tri, n = tri[keep], n[keep]
        shade = 0.35 + 0.65 * np.clip(np.abs(n @ light), 0, 1)
        rgb = np.clip(np.array(col[:3])[None, :] * shade[:, None], 0, 1)
        polys.append(np.stack([tri @ r, tri @ u], axis=-1)); depth.append((tri @ d).mean(axis=1))
        cols.append(np.hstack([rgb, np.full((len(rgb), 1), col[3])]))
    P = np.concatenate(polys); Dp = np.concatenate(depth); Cc = np.concatenate(cols)
    o = np.argsort(Dp)
    ax.add_collection(PolyCollection(P[o], facecolors=Cc[o], edgecolors=Cc[o], linewidths=0.2))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")

def render(items, fname, az=30, el=20, title="", size=(10, 11), labels=(), xlim=None, ylim=None):
    r, u, d = view_basis(az, el)
    light = 0.6 * d + 0.5 * np.array([0.3, -0.4, 0.8]); light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    for name, shp, col, grp in items:
        v, t = tess(shp)
        if len(t) == 0:
            continue
        tri = v[t]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1); ok = nn > 1e-9
        tri = subdivide(tri[ok])
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1); ok = nn > 1e-12
        tri, n = tri[ok], n[ok] / nn[ok, None]
        alpha = col[3]
        facing = n @ d
        if alpha >= 0.99:
            keep = facing > -1e-6
            tri, n, facing = tri[keep], n[keep], facing[keep]
        shade = 0.35 + 0.65 * np.clip(np.abs(n @ light), 0, 1)
        rgb = np.clip(np.array(col[:3])[None, :] * shade[:, None], 0, 1)
        p2 = np.stack([tri @ r, tri @ u], axis=-1)
        polys.append(p2); depth.append((tri @ d).mean(axis=1))
        cols.append(np.hstack([rgb, np.full((len(rgb), 1), alpha)]))
    P = np.concatenate(polys); Dp = np.concatenate(depth); Cc = np.concatenate(cols)
    order = np.argsort(Dp)
    fig, ax = plt.subplots(figsize=size, dpi=130)
    ax.add_collection(PolyCollection(P[order], facecolors=Cc[order], edgecolors=Cc[order], linewidths=0.3))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    if xlim: ax.set_xlim(*xlim)
    if ylim: ax.set_ylim(*ylim)
    for (x, y, z), txt in labels:
        p = np.array([x, y, z]); ax.annotate(txt, (p @ r, p @ u), fontsize=8, fontproperties=FONT,
                                             color="k", bbox=dict(boxstyle="round,pad=0.2", fc="#ffffe0", ec="#888", lw=0.5, alpha=0.9))
    if title:
        ax.set_title(title, fontproperties=FONT, fontsize=12)
    fig.tight_layout(); fig.savefig(fname, facecolor="white"); plt.close(fig)
