"""StandardVisualizer for MULTI1D Visualizer v2.3.1

1D 模拟算例标准可视化工具（MULTI-2D 项目规范 v1.0，2026-09-07 定稿）。
独立于主窗口运行逻辑：模块导入零副作用（不创建 QApplication、不强设
matplotlib 后端），可被主程序安全导入，也可单独命令行调用。

默认产物 9 张（无驱动 8 张）到 <case_dir>/viz/：
  heat_{R,PT,TE}_{xc,lc}.png   密度/压强/温度 × 欧拉/拉格朗日热图
  target_layout.png             靶与驱动设计示意（竖条带/初始密度/箭头束）
  grid_layout.png               初始网格划分示意
  laser_waveforms.png | rad_source.png   驱动图（自动识别）

用法（库）:
    from utils.standard_visuals import StandardVisualizer
    sv = StandardVisualizer("<case_dir>")
    sv.run()                     # 全套
    sv.run(shock=True)           # 叠加激波轨迹
    sv.run(vars=("PT",), coords=("euler",))

用法（单独脚本）:
    python3 utils/standard_visuals.py <case_dir> [--shock] [选项]
"""

import os
import re
import sys

import numpy as np

# 脚本直接运行时把包根加入 sys.path（库导入时无副作用）
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)


# ============================================================ data.in parsing
def grab_namelist_float(txt, key, default=None):
    """只认赋值行（头注释 'pimax = 800J/...' 会被正则抢匹配）；剥 ! 注释"""
    for ln in txt.splitlines():
        s = ln.strip()
        if s.startswith(key) and "=" in s:
            raw = s.split("=", 1)[1].split("!")[0].strip().rstrip(",")
            try:
                return float(raw)
            except ValueError:
                pass
    return default


def grab_namelist_vector(txt, key):
    """Read a namelist vector; supports value continuation lines
    (wrapped tables, e.g. long ttab/ptab kept under the 80-char
    namelistblock limit in m150304). Added 2026-09-10 (route 4)."""
    lines = txt.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(key) and "=" in s:
            raw = s.split("=", 1)[1].split("!")[0].replace("/", " ")
            vals = [float(v) for v in raw.split(",") if v.strip()]
            j = i + 1
            while j < len(lines):
                ts = lines[j].strip()
                if (not ts or "=" in lines[j] or ts.startswith('&')
                        or ts.startswith('/') or ts.startswith('!')):
                    break
                try:
                    more = [float(v) for v in ts.split(",") if v.strip()]
                except ValueError:
                    break
                if not more:
                    break
                vals += more
                j += 1
            return vals
    return None


def detect_driver(txt):
    if re.search(r"^&pulse_wkb", txt, re.M):
        return "laser"
    beta_r = grab_namelist_float(txt, "betar", 0.0)
    beta_l = grab_namelist_float(txt, "betal", 0.0)
    if (beta_r and beta_r != 0) or (beta_l and beta_l != 0):
        return "rad"
    return "none"


def read_layers(txt):
    """&layer 块列表 [(nc, thick_cm, r0, material)]。
    块匹配必须锚定行首 '/'——块内注释 'um/cell' 的斜杠会截断非贪婪匹配。"""
    layers = []
    for m in re.finditer(r"&layer(.*?)(?=^\s*/\s*$)", txt, re.S | re.M):
        blk = m.group(1)
        nc = re.search(r"nc\s*=\s*(\d+)", blk)
        th = re.search(r"thick\s*=\s*([0-9.eE+-]+)", blk)
        r0 = re.search(r"r0\s*=\s*([0-9.eE+-]+)", blk)
        mt = re.search(r"material\s*=\s*'([^']+)'", blk)
        if nc and th and r0:
            layers.append((int(nc.group(1)), float(th.group(1)),
                           float(r0.group(1)),
                           mt.group(1) if mt else "?"))
    return layers


def _layers_merged(txt):
    """[(nc, thick_um, r0, mat)] 逐段 + 合并段 + 累计界面(um)"""
    layers = read_layers(txt)
    edges = np.cumsum([0.0] + [l[1] for l in layers]) * 1e4
    merged = []
    for nc, th, r0, mat in layers:
        if merged and merged[-1][3] == mat and merged[-1][2] == r0:
            merged[-1] = (merged[-1][0] + nc, merged[-1][1] + th, r0, mat)
        else:
            merged.append((nc, th, r0, mat))
    return layers, merged, edges


def _driver_info(txt, driver):
    """驱动描述 (side, label)；side 'L'/'R' = 入射侧"""
    if driver == "laser":
        wl = grab_namelist_float(txt, "wl")
        pimax = grab_namelist_float(txt, "pimax")
        tt = grab_namelist_vector(txt, "ttab")
        inter = grab_namelist_float(txt, "inter", -1.0)
        side = "L" if inter < 0 else "R"
        lab = "laser"
        if wl:
            lab += " %.0f nm" % (wl * 1e7)
        if pimax:
            lab += ", %.2e W/cm2" % (pimax / 1e7)
        if tt:
            lab += ", %.2g ns" % (max(tt) - min(tt))
        return side, lab
    if driver == "rad":
        beta_r = grab_namelist_float(txt, "betar", 0.0)
        trad = grab_namelist_float(txt, "trad")
        tt = grab_namelist_vector(txt, "ttab")
        side = "R" if (beta_r and beta_r != 0) else "L"
        lab = "rad. source"
        if trad and tt:
            pp = grab_namelist_vector(txt, "ptab")
            if pp:
                lab += " Tr,max %.0f eV" % (max(pp) * trad)
        if tt:
            lab += ", %.2g ns" % (max(tt) - min(tt))
        return side, lab
    return None, ""


# ============================================================ visualizer
VAR_CFG = {
    # 2026-09-07 用户要求全部正常线性色标（log 全动态范围会把靶内部压成
    # 大片纯色"空白"）；R/TE 与 PT 同法用 95% 分位截断上界
    "R":  dict(log=False, unit="R (g/cm^3)"),
    "PT": dict(log=False, unit="PT (GPa)", factor=1e-10),
    "TE": dict(log=False, unit="TE (eV)"),
}


class StandardVisualizer:
    """1D 算例标准可视化（规范 v1.0）。

    :param case_dir:  算例目录（含 data.in 与 fort.10）
    :param outdir:    输出目录，默认 <case_dir>/viz
    :param driver:    'auto'（默认，由 data.in 判定）| 'laser' | 'rad' | 'none'
    """

    def __init__(self, case_dir, outdir=None, driver="auto"):
        self.case = os.path.abspath(case_dir)
        self.outdir = outdir or os.path.join(self.case, "viz")
        os.makedirs(self.outdir, exist_ok=True)
        self.txt = open(os.path.join(self.case, "data.in")).read()
        self.driver = (detect_driver(self.txt) if driver == "auto"
                       else driver)
        f10 = os.path.join(self.case, "fort.10")
        self.parser = self._make_parser(f10)
        self._eng = None

    # ---- lazy Qt/PlotEngine（不影响主窗口：实例已存在则复用） ----
    @staticmethod
    def _make_parser(f10):
        from core.ife_parser import IFEParser
        parser = IFEParser(f10)
        assert parser.parse(), "fort.10 parse failed: " + f10
        return parser

    def _engine(self):
        if self._eng is None:
            from PyQt5.QtWidgets import QApplication
            from core.plot_engine import PlotEngine
            if QApplication.instance() is None:      # 主窗口已跑则复用
                QApplication([])
            self._eng = PlotEngine()
        return self._eng

    # ---- data access (parser API) ----
    def _t_ns(self):
        return np.asarray(self.parser.get_time_array(unit="ns"))

    def _field(self, var):
        return np.asarray(self.parser.get_spatial_data_all_times(var))

    def _global(self, var):
        r = self.parser.get_time_series_global(var)
        return (np.asarray(r[0]) * 1e9, np.asarray(r[1])) if r else (None, None)

    def _grid(self, coord, time_idx=None):
        return np.asarray(self.parser.get_grid_positions(
            unit="um", coord_system=coord, time_idx=time_idx))

    # ---- shock tracking ----
    def shock_track(self, x0_um, rho_th, xmax_um):
        t = self._t_ns()
        R = self._field("R")
        xs = np.full(len(t), np.nan)
        for i in range(len(t)):
            xc = self._grid("XC", time_idx=i)
            m = (xc > x0_um) & (xc < xmax_um) & (R[i] > rho_th)
            if m.any():
                xs[i] = xc[int(np.max(np.nonzero(m)[0]))]
        return t, xs

    # ---- heatmaps ----
    def make_heatmaps(self, vars_=("R", "PT", "TE"),
                      coords=("euler", "lag"), shock=None,
                      ranges=None):
        """六张数据热图。ranges: {'PT': (vmin, vmax), ...} 覆盖默认色标"""
        ranges = ranges or {}
        import matplotlib.patheffects as pe
        stroke = [pe.withStroke(linewidth=3, foreground="black")]
        eng = self._engine()
        coord_map = {  # 拉格朗日 = LC（初始格心）；CMC 是质量坐标、NC 格号
            "euler": ("XC", "xc", "XC (um)"),
            "lag": ("LC", "lc", "LC (um)")}
        for var in vars_:
            cfg = VAR_CFG[var]
            mat = self._field(var)
            vmin, vmax = ranges.get(var, self._default_range(var, mat, cfg))
            for ckey in coords:
                coord, tag, ylabel = coord_map[ckey]
                fname = "heat_%s_%s.png" % (var, tag)
                title = "%s: %s (%s)" % (
                    os.path.basename(self.case), var,
                    "Euler" if ckey == "euler" else "Lagrangian")
                eng.plot_interpolated_heatmap(
                    parser=self.parser, var=var, n_interp_points=600,
                    cmap="jet", xlabel="Time", ylabel=ylabel, title=title,
                    time_unit="ns", coord_system=coord, transpose=True,
                    vmin=vmin, vmax=vmax, log_color=cfg["log"],
                    value_factor=cfg.get("factor", 1.0),
                    colorbar_label=cfg["unit"])
                if shock is not None and ckey == "euler":
                    t, xs = shock
                    m = ~np.isnan(xs)
                    eng.ax.plot(t[m], xs[m], color="w", lw=2.0, zorder=5,
                                path_effects=stroke)
                ok = eng.save_figure(os.path.join(self.outdir, fname), dpi=180)
                assert ok, "save_figure failed: " + fname
                print("saved", fname)

    @staticmethod
    def _default_range(var, mat, cfg):
        """线性 95% 分位截断（极值常为烧蚀面/冕区尖峰，会压没主体结构）；
        PT 保留少量负值下界显示，R/TE 下界为 0（2026-09-07 全线性定稿）"""
        vmax = np.nanpercentile(mat, 95) * cfg.get("factor", 1.0)
        if vmax <= 0:
            vmax = np.nanmax(mat) * cfg.get("factor", 1.0)
        if var == "PT":
            return (-vmax / 20.0, vmax)
        return (0.0, vmax)

    # ---- target schematic ----
    def layout_figure(self):
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import matplotlib.patches as mpatches
        import matplotlib.patheffects as pe
        stroke = [pe.withStroke(linewidth=3, foreground="black")]

        layers, merged, edges = _layers_merged(self.txt)
        tot = edges[-1]
        R0 = self._field("R")[0]

        fig, ax = plt.subplots(figsize=(8.5, 7.0))
        order = np.argsort([l[2] for l in merged])
        rank = np.empty(len(merged), dtype=int)
        rank[order] = np.arange(len(merged))
        n = max(len(merged) - 1, 1)
        cmap = plt.get_cmap("jet")
        for k, (_, th, r0, mat) in enumerate(merged):
            ax.add_patch(mpatches.Rectangle(
                (edges[k], 0.0), th * 1e4, 1.0,
                facecolor=cmap(0.12 + 0.76 * rank[k] / n), edgecolor="none"))
        ax.add_patch(mpatches.Rectangle((edges[0], 0.0), tot, 1.0,
                                        fill=False, edgecolor="k", lw=2.8))
        for k in range(len(merged) + 1):
            xe = edges[k] if k < len(merged) else edges[-1]
            ax.plot([xe, xe], [0.0, 1.0], color="w", lw=1.8)
        narrow = []
        for k, (_, th, r0, mat) in enumerate(merged):
            cx = 0.5 * (edges[k] + edges[k + 1])
            label = "%s  %.1f um" % (mat, th * 1e4)
            if th * 1e4 > 0.05 * tot:
                ax.text(cx, 0.5, label, rotation=90, ha="center",
                        va="center", fontsize=11, color="w",
                        path_effects=stroke)
            else:
                narrow.append((cx, label))
        for i, (cx, label) in enumerate(narrow):
            ytxt = 1.07 + 0.09 * (i % 2)
            ax.annotate(label, xy=(cx, 1.0), xytext=(cx, ytxt),
                        ha="center", va="bottom", fontsize=9.5, color="k",
                        arrowprops=dict(arrowstyle="-", color="0.3",
                                        lw=0.8, shrinkA=0, shrinkB=0))
        side, dlab = _driver_info(self.txt, self.driver)
        if side:
            ys = np.linspace(0.05, 0.95, 9)
            if side == "L":
                xt, xh = -0.085 * tot, -0.008 * tot
                xlab = xt - 0.025 * tot
            else:
                xt, xh = 1.085 * tot, 1.008 * tot
                xlab = xt + 0.025 * tot
            for y in ys:
                ax.annotate("", xy=(xh, y), xytext=(xt, y),
                            arrowprops=dict(arrowstyle="-|>", lw=3.0,
                                            mutation_scale=28,
                                            color="crimson"))
            ax.text(xlab, 0.5, dlab, rotation=90, ha="center", va="center",
                    fontsize=10.5, color="crimson")
        lo = -0.16 * tot if side == "L" else -0.03 * tot
        hi = 1.16 * tot if side == "R" else 1.03 * tot
        ax.set_xlim(lo, hi)
        ax.set_ylim(-0.06, 1.20 if narrow else 1.06)
        ax.set_axis_off()
        ax.set_title("%s: target & drive schematic" %
                     os.path.basename(self.case), fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(self.outdir, "target_layout.png"), dpi=180)
        plt.close(fig)
        print("saved target_layout.png | %d layers, drive=%s(%s)"
              % (len(merged), self.driver, side))

    # ---- grid schematic ----
    def grid_figure(self):
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        layers, merged, edges = _layers_merged(self.txt)
        tot = edges[-1]
        X0 = self._grid("X", time_idx=0)

        fig, ax = plt.subplots(figsize=(8.5, 7.0))
        order = np.argsort([l[2] for l in merged])
        rank = np.empty(len(merged), dtype=int)
        rank[order] = np.arange(len(merged))
        n = max(len(merged) - 1, 1)
        cmap = plt.get_cmap("jet")
        for k, (_, th, r0, mat) in enumerate(merged):
            ax.add_patch(mpatches.Rectangle(
                (edges[k], 0.0), th * 1e4, 1.0,
                facecolor=cmap(0.12 + 0.76 * rank[k] / n), alpha=0.35,
                edgecolor="none"))
        for y in X0:
            ax.plot([y, y], [0.0, 1.0], color="0.25", lw=0.55, alpha=0.9)
        for k in range(len(merged) + 1):
            xe = edges[k] if k < len(merged) else edges[-1]
            ax.plot([xe, xe], [0.0, 1.0], color="k", lw=2.2)
        ax.add_patch(mpatches.Rectangle((edges[0], 0.0), tot, 1.0,
                                        fill=False, edgecolor="k", lw=2.8))
        xe = np.cumsum([0.0] + [l[1] for l in layers]) * 1e4
        narrow = []
        for k, (nc, th, r0, mat) in enumerate(layers):
            cx = 0.5 * (xe[k] + xe[k + 1])
            label = "%s\nnc=%d, dx=%.3g um" % (mat, nc, th * 1e4 / nc)
            if th * 1e4 > 0.05 * tot:
                ax.text(cx, 0.5, label, rotation=90, ha="center",
                        va="center", fontsize=10, color="k")
            else:
                narrow.append((cx, label.replace("\n", " ")))
        for i, (cx, label) in enumerate(narrow):
            ytxt = 1.07 + 0.10 * (i % 2)
            ax.annotate(label, xy=(cx, 1.0), xytext=(cx, ytxt),
                        ha="center", va="bottom", fontsize=9, color="k",
                        arrowprops=dict(arrowstyle="-", color="0.3",
                                        lw=0.8, shrinkA=0, shrinkB=0))
        ax.set_xlim(-0.04 * tot, 1.04 * tot)
        ax.set_ylim(-0.06, 1.22 if narrow else 1.06)
        ax.set_axis_off()
        ax.set_title("%s: initial grid layout (%d cells)" %
                     (os.path.basename(self.case),
                      sum(l[0] for l in layers)), fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(self.outdir, "grid_layout.png"), dpi=180)
        plt.close(fig)
        print("saved grid_layout.png")

    # ---- driver figures ----
    def laser_figure(self):
        import matplotlib.pyplot as plt
        pimax = grab_namelist_float(self.txt, "pimax")
        tt = grab_namelist_vector(self.txt, "ttab")
        pp = grab_namelist_vector(self.txt, "ptab")
        assert None not in (pimax, tt, pp), "data.in 缺 pulse 参数"
        t10, L = self._global("LASER")
        _, D = self._global("DELAS")
        t10 = t10 * 1e-9 * 1e9                      # s -> ns (api 返回 s)
        dt = np.diff(t10)
        inc = np.diff(L) / dt * 1e2
        ab = np.diff(D) / dt * 1e2
        tm = 0.5 * (t10[1:] + t10[:-1])

        t_end = max(tt[-1] * 1.5, 0.1)
        fig, ax = plt.subplots(figsize=(8.2, 5.4))
        tg = np.linspace(0, t_end, 1501)
        ig = np.interp(tg, tt, pp) * pimax / 1e7
        scale = 10.0 ** np.floor(np.log10(max(ig.max(), 1e-30)))
        ax.plot(tg, ig / scale, "k-", lw=2,
                label="incident (data.in nominal)")
        m = tm <= t_end
        ax.plot(tm[m], inc[m] / scale, ":", color="tab:blue", lw=1.6,
                label="incident (fort.10 LASER diff)")
        ax.plot(tm[m], ab[m] / scale, "--", color="tab:red", lw=1.4,
                label="absorbed (fort.10 DELAS diff)")
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Laser intensity (10$^{%d}$ W/cm$^2$)"
                      % np.log10(scale))
        ax.set_title("%s: laser waveform" % os.path.basename(self.case))
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(self.outdir, "laser_waveforms.png"), dpi=180)
        plt.close(fig)
        print("saved laser_waveforms.png | incident %.1f J/cm2, absorbed "
              "%.1f (%.1f%%), peak %.3g W/cm2"
              % (L[-1] / 1e7, D[-1] / 1e7,
                 100 * D[-1] / max(L[-1], 1e-30),
                 np.nanmax(inc[tm <= tt[-1]]) if (tm <= tt[-1]).any() else 0))

    def rad_figure(self):
        import matplotlib.pyplot as plt
        tt = grab_namelist_vector(self.txt, "ttab")
        pp = grab_namelist_vector(self.txt, "ptab")
        trad = grab_namelist_float(self.txt, "trad")
        beta_r = grab_namelist_float(self.txt, "betar", 0.0)
        assert None not in (tt, pp, trad), "data.in 缺辐射驱动参数"
        t10 = self._t_ns()
        TR = self._field("TR")
        src = TR[:, -1] if (beta_r and beta_r != 0) else TR[:, 0]

        t_end = max(tt[-1] * 1.2, 1.0)
        fig, ax = plt.subplots(figsize=(8.2, 5.4))
        tg = np.linspace(0, t_end, 1501)
        nominal = np.interp(tg, tt, pp) * trad
        ax.plot(tg, nominal, "k-", lw=2, label="nominal Tr(t) (data.in)")
        m = t10 <= t_end
        ax.plot(t10[m], src[m], ".", color="tab:red", ms=3,
                label="fort.10 TR at source boundary")
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Radiation temperature (eV)")
        ax.set_title("%s: radiation source" % os.path.basename(self.case))
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(self.outdir, "rad_source.png"), dpi=180)
        plt.close(fig)
        print("saved rad_source.png | nominal Tr max %.1f eV, TR boundary "
              "max %.1f eV" % (nominal.max(), src.max()))

    # ---- orchestrator ----
    def run(self, vars_=("R", "PT", "TE"), coords=("euler", "lag"),
            shock=False, shock_rho=None, shock_x0=None, shock_xmax=None,
            no_driver=False, ranges=None):
        """全套出图（规范 v1.0 默认 9 张）"""
        print("case=%s driver=%s" % (self.case, self.driver))
        traj = None
        if shock:
            layers = read_layers(self.txt)
            assert layers, "&layer 解析失败"
            edges = np.cumsum([0] + [l[1] for l in layers]) * 1e4
            deepest = len(layers) - 1
            x0 = shock_x0 if shock_x0 is not None else edges[deepest]
            xmax = (shock_xmax if shock_xmax is not None
                    else edges[deepest + 1])
            rho_th = (shock_rho if shock_rho is not None
                      else layers[deepest][2] * 1.2)
            traj = self.shock_track(x0, rho_th, xmax)
            t, xs = traj
            m = ~np.isnan(xs) & (t > 0.3)
            if m.sum() > 5:
                v = np.polyfit(t[m], xs[m], 1)[0]
                print("shock track: %.1f km/s avg (fit %.2f-%.2f ns, "
                      "rho_th=%.2f)" % (v, t[m].min(), t[m].max(), rho_th))
        self.make_heatmaps(vars_=vars_, coords=coords, shock=traj,
                           ranges=ranges)
        self.layout_figure()
        self.grid_figure()
        if not no_driver:
            if self.driver == "laser":
                self.laser_figure()
            elif self.driver == "rad":
                self.rad_figure()
        print("ALL DONE ->", self.outdir)
        return self.outdir


# ============================================================ CLI
def main():
    import argparse
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # 仅独立 CLI 时
    ap = argparse.ArgumentParser(
        description="1D case standard visuals (spec v1.0)")
    ap.add_argument("case")
    ap.add_argument("--vars", default="R,PT,TE")
    ap.add_argument("--coords", default="euler,lag")
    ap.add_argument("--shock", action="store_true")
    ap.add_argument("--shock-rho", type=float, default=None)
    ap.add_argument("--shock-x0", type=float, default=None)
    ap.add_argument("--shock-xmax", type=float, default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--no-driver", action="store_true")
    ap.add_argument("--driver", default="auto",
                    choices=["auto", "laser", "rad", "none"])
    args = ap.parse_args()

    sv = StandardVisualizer(args.case, outdir=args.outdir,
                            driver=args.driver)
    sv.run(vars_=tuple(v.strip().upper() for v in args.vars.split(",")),
           coords=tuple(c.strip().lower() for c in args.coords.split(",")),
           shock=args.shock, shock_rho=args.shock_rho,
           shock_x0=args.shock_x0, shock_xmax=args.shock_xmax,
           no_driver=args.no_driver)


if __name__ == "__main__":
    main()
