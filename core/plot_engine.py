"""PlotEngine for MULTI1D Visualizer v2.3.1

Encapsulates all Matplotlib plotting operations.
科研论文规范的绘图样式
"""

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
from scipy.interpolate import interp1d
import numpy as np
from typing import List, Optional, Tuple
from PyQt5.QtCore import Qt as _Qt
from utils.logger import Logger

# IM_tool P-up 图风格 rcParams (serif, no grid, clean)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Computer Modern Roman']
plt.rcParams['mathtext.fontset'] = 'dejavuserif'
plt.rcParams['axes.unicode_minus'] = True
plt.rcParams['font.size'] = 18
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 20
plt.rcParams['xtick.labelsize'] = 16
plt.rcParams['ytick.labelsize'] = 16
plt.rcParams['legend.fontsize'] = 16
plt.rcParams['figure.titlesize'] = 20
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['axes.grid'] = False
plt.rcParams['xtick.major.width'] = 1.2
plt.rcParams['ytick.major.width'] = 1.2
plt.rcParams['xtick.minor.width'] = 0.8
plt.rcParams['ytick.minor.width'] = 0.8
plt.rcParams['xtick.major.size'] = 6
plt.rcParams['ytick.major.size'] = 6
plt.rcParams['xtick.minor.size'] = 4
plt.rcParams['ytick.minor.size'] = 4
plt.rcParams['lines.linewidth'] = 1.2
plt.rcParams['lines.markersize'] = 6
plt.rcParams['legend.frameon'] = False
plt.rcParams['legend.handlelength'] = 1.5


class PlotEngine:
    """绘图引擎，封装所有Matplotlib操作，符合科研论文规范"""

    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(parent)
        self.canvas.setFocusPolicy(_Qt.StrongFocus)
        self.ax = self.fig.add_subplot(111)
        self.colorbar = None
        self.logger = Logger.get_logger('PlotEngine')
        self._coord_text = None
        self._heatmap_data = None  # (x_array, y_array, data_matrix) for value lookup
        self._blit_bg = None       # cached background for fast cursor redraw
        self._init_style()
        self._init_interaction()
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('axes_leave_event', self._on_mouse_leave)
        # Invalidate blit cache whenever the canvas does a full redraw
        self.canvas.mpl_connect('draw_event', self._on_canvas_draw)

    def _init_style(self):
        """初始化 IM_tool P-up 图风格"""
        for s in ['top', 'right', 'left', 'bottom']:
            self.ax.spines[s].set_visible(True)
            self.ax.spines[s].set_linewidth(1.2)
        self.ax.tick_params(
            axis='both', which='major', direction='in',
            top=False, right=False,
            width=1.2, length=6,
        )
        self.ax.tick_params(
            axis='both', which='minor', direction='in',
            top=False, right=False,
            width=0.8, length=4,
        )
        import matplotlib.ticker as _ticker
        self.ax.xaxis.set_major_locator(_ticker.MaxNLocator(nbins=6))
        self.ax.yaxis.set_major_locator(_ticker.MaxNLocator(nbins=6))
        self.ax.minorticks_on()

    @staticmethod
    def latex_unit(unit: str) -> str:
        if not unit:
            return unit
        s = unit
        s = s.replace('um', '$\\mu$m')
        s = s.replace('·', '$\\cdot$')
        import re
        s = re.sub(r'\^(\d+)', r'$^{\1}$', s)
        return s

    # ========== 画布交互（框选缩放 + 快捷键）==========

    def _init_interaction(self):
        """初始化交互状态并连接事件"""
        self._zoom_press = None       # (xdata, ydata) or None
        self._zoom_rect = None        # Rectangle artist for rubber band
        self._zoom_blit_bg = None     # cached axes background for rubber-band blit
        self._nav_stack = []          # list of (xlim, ylim)
        self._full_view = None        # (xlim, ylim) — full data view
        self._zoom_enabled = True

        self.canvas.mpl_connect('button_press_event', self._on_zoom_press)
        self.canvas.mpl_connect('button_release_event', self._on_zoom_release)
        self.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)

    def _on_zoom_press(self, event):
        if not self._zoom_enabled or event.inaxes != self.ax or event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        self._zoom_press = (event.xdata, event.ydata)
        self._zoom_blit_bg = None  # captured lazily on first motion

    def _update_zoom_rubber(self, event):
        if self._zoom_press is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        x0, y0 = self._zoom_press
        x1, y1 = event.xdata, event.ydata
        w, h = x1 - x0, y1 - y0

        if self._zoom_rect is None:
            # 首次更新：创建矩形并捕获不含矩形的背景
            self._zoom_rect = Rectangle(
                (x0, y0), w, h,
                fill=True, facecolor='gray', alpha=0.15,
                edgecolor='black', linestyle='--', linewidth=1,
                zorder=1000
            )
            self.canvas.draw()
            self._zoom_blit_bg = self.canvas.copy_from_bbox(self.ax.bbox)
            self.ax.add_patch(self._zoom_rect)
        else:
            self._zoom_rect.set_xy((x0, y0))
            self._zoom_rect.set_width(w)
            self._zoom_rect.set_height(h)
            self._zoom_rect.set_visible(True)

        # Blit only the rubber band on top of saved background
        if self._zoom_blit_bg is not None:
            self.canvas.restore_region(self._zoom_blit_bg)
            self.ax.draw_artist(self._zoom_rect)
            self.canvas.blit(self.ax.bbox)

    def _on_zoom_release(self, event):
        if self._zoom_press is None:
            return
        x0, y0 = self._zoom_press
        # 清除橡皮筋框
        if self._zoom_rect is not None:
            try:
                self._zoom_rect.remove()
            except Exception:
                pass
            self._zoom_rect = None
        self._zoom_press = None
        self._zoom_blit_bg = None

        if event.xdata is None or event.ydata is None:
            self.canvas.draw_idle()
            return

        x1, y1 = event.xdata, event.ydata
        dx, dy = abs(x1 - x0), abs(y1 - y0)

        # 忽略极小拖拽（避免误触）
        if dx < 1e-10 or dy < 1e-10:
            self.canvas.draw_idle()
            return

        # 保存当前视图用于后退
        self._nav_stack.append((self.ax.get_xlim(), self.ax.get_ylim()))

        # 缩放到框选范围
        self.ax.set_xlim(min(x0, x1), max(x0, x1))
        self.ax.set_ylim(min(y0, y1), max(y0, y1))
        self.canvas.draw_idle()

    def _on_key_press(self, event):
        if event.key == 'a' or event.key == 'A':
            self._zoom_home()
        elif event.key == 'h' or event.key == 'H':
            self._zoom_back()

    def _on_scroll(self, event):
        if not self._zoom_enabled or event.inaxes != self.ax:
            return

        self._nav_stack.append((self.ax.get_xlim(), self.ax.get_ylim()))

        scale = 1.3 if event.button == 'up' else 1 / 1.3
        cx, cy = event.xdata, event.ydata
        xlim = list(self.ax.get_xlim())
        ylim = list(self.ax.get_ylim())

        xlim[0] = cx - (cx - xlim[0]) * scale
        xlim[1] = cx + (xlim[1] - cx) * scale
        ylim[0] = cy - (cy - ylim[0]) * scale
        ylim[1] = cy + (ylim[1] - cy) * scale

        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.canvas.draw_idle()

    def _zoom_home(self):
        """恢复到完整数据视图（'a' 键）"""
        self.logger.info(f"[ZoomHome] called, _full_view={self._full_view}")
        if self._full_view is not None:
            self.ax.set_xlim(self._full_view[0])
            self.ax.set_ylim(self._full_view[1])
        else:
            self.ax.relim()
            self.ax.autoscale_view()
        self._nav_stack.clear()
        self.canvas.draw()  # 同步绘制，立即生效

    def _zoom_back(self):
        """回退到上一个视图（'h' 键）"""
        if self._nav_stack:
            xlim, ylim = self._nav_stack.pop()
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.canvas.draw_idle()

    def focus_canvas(self):
        """将键盘焦点设置到画布，确保快捷键生效"""
        self.canvas.setFocus()

    def install_global_hotkeys(self, parent):
        """在 parent 控件上安装全局快捷键（不依赖 canvas 焦点）
        
        'a' / 'A' → 恢复完整数据视图
        'h' / 'H' → 回退到上一个视图
        """
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtCore import QTimer

        def _defer(fn):
            QTimer.singleShot(0, fn)

        self._shortcuts = []
        for seq in (_Qt.Key_A, "a", "A"):
            sc = QShortcut(seq, parent, lambda fn=self._zoom_home: _defer(fn),
                           context=_Qt.WindowShortcut)
            self._shortcuts.append(sc)
        for seq in (_Qt.Key_H, "h", "H"):
            sc = QShortcut(seq, parent, lambda fn=self._zoom_back: _defer(fn),
                           context=_Qt.WindowShortcut)
            self._shortcuts.append(sc)

    def clear(self):
        """清除画布"""
        # 先移除colorbar
        if self.colorbar:
            try:
                self.colorbar.remove()
            except:
                pass
            self.colorbar = None

        # 清除axes
        self.ax.clear()

        # 重置光标追踪状态
        self._coord_text = None
        self._heatmap_data = None
        self._blit_bg = None

        # 重新初始化样式
        self._init_style()

        # 重置交互状态
        self._full_view = None

        # 重绘
        self.canvas.draw_idle()

    # ========== 空间曲线绘制 ==========

    def plot_spatial_curves(
        self,
        x: np.ndarray,
        data_list: List[np.ndarray],
        labels: List[str] = None,
        colors: List[str] = None,
        linestyles: List[str] = None,
        linewidths: List[float] = None,
        xlabel: str = 'Position',
        ylabel: str = 'Value',
        title: str = '',
        show_legend: bool = False,
        xunit: str = 'cm',
        log_x: bool = False,
        log_y: bool = False,
        xlim: Tuple[float, float] = None,
        ylim: Tuple[float, float] = None
    ):
        """
        绘制多条空间曲线

        :param x: x轴数据 (网格位置)
        :param data_list: y轴数据列表 (每条曲线一个数组)
        :param labels: 每条曲线的标签
        :param colors: 颜色列表
        :param linestyles: 线型列表
        :param linewidths: 线宽列表
        :param show_legend: 是否显示图例
        :param xunit: x轴单位
        :param log_x: 是否使用对数X轴
        :param log_y: 是否使用对数Y轴
        :param xlim: x轴范围
        :param ylim: y轴范围
        """
        self.clear()

        n_curves = len(data_list)
        for i, y in enumerate(data_list):
            color = colors[i] if colors and i < len(colors) else None
            ls = linestyles[i] if linestyles and i < len(linestyles) else '-'
            lw = linewidths[i] if linewidths and i < len(linewidths) else 1.5
            label = labels[i] if labels and i < len(labels) else None

            xi = x[i] if isinstance(x, list) else x
            xi = xi[:len(y)]
            n = len(xi)
            marker = 'o' if n < 2 else ''
            ms = 6 if n < 2 else 0
            self.ax.plot(xi, y, color=color, linestyle=ls, linewidth=lw,
                         marker=marker, markersize=ms, label=label)

        self.ax.set_xlabel(f'{xlabel} ({self.latex_unit(xunit)})')
        self.ax.set_ylabel(self.latex_unit(ylabel))
        if title:
            self.ax.set_title(title)

        if log_x:
            self.ax.set_xscale('log')
        if log_y:
            self.ax.set_yscale('log')

        if xlim:
            self.ax.set_xlim(xlim)
        if ylim:
            self.ax.set_ylim(ylim)

        if show_legend:
            self.ax.legend(frameon=False)

        self.fig.tight_layout()
        self.canvas.draw_idle()
        if self._full_view is None:
            self._full_view = (self.ax.get_xlim(), self.ax.get_ylim())

    # ========== 时间序列绘制 ==========

    def plot_time_series(
        self,
        times: np.ndarray,
        data_list: List[np.ndarray],
        labels: List[str] = None,
        colors: List[str] = None,
        linestyles: List[str] = None,
        linewidths: List[float] = None,
        ylabel: str = 'Value',
        title: str = '',
        show_legend: bool = False,
        time_unit: str = 'ns',
        log_y: bool = False,
        log_x: bool = False,
        xlim: Tuple[float, float] = None,
        ylim: Tuple[float, float] = None
    ):
        """
        绘制多条时间序列曲线

        :param times: 时间数组
        :param data_list: 数值数组列表
        :param labels: 每条曲线的标签
        :param log_y: 是否使用对数Y轴
        :param log_x: 是否使用对数X轴
        :param time_unit: 时间单位
        :param xlim: x轴范围
        :param ylim: y轴范围
        """
        self.clear()

        for i, y in enumerate(data_list):
            color = colors[i] if colors and i < len(colors) else None
            ls = linestyles[i] if linestyles and i < len(linestyles) else '-'
            lw = linewidths[i] if linewidths and i < len(linewidths) else 1.5
            label = labels[i] if labels and i < len(labels) else None

            t = times[:len(y)]
            n = len(t)
            marker = 'o' if n < 2 else ''
            ms = 6 if n < 2 else 0
            self.ax.plot(t, y, color=color, linestyle=ls, linewidth=lw,
                         marker=marker, markersize=ms, label=label)

        if log_x:
            self.ax.set_xscale('log')
        if log_y:
            self.ax.set_yscale('log')

        if xlim:
            self.ax.set_xlim(xlim)
        if ylim:
            self.ax.set_ylim(ylim)

        self.ax.set_xlabel(f'Time ({self.latex_unit(time_unit)})')
        self.ax.set_ylabel(self.latex_unit(ylabel))
        if title:
            self.ax.set_title(title)

        if show_legend:
            self.ax.legend(frameon=False)

        self.canvas.draw_idle()
        if self._full_view is None:
            self._full_view = (self.ax.get_xlim(), self.ax.get_ylim())

    # ========== 热图绘制 ==========

    def plot_heatmap(
        self,
        x: np.ndarray,
        times: np.ndarray,
        data: np.ndarray,  # shape: (n_times, n_x)
        cmap: str = 'jet',
        vmin: float = None,
        vmax: float = None,
        log_color: bool = False,
        xlim: Tuple[float, float] = None,
        ylim: Tuple[float, float] = None,
        xlabel: str = 'Position',
        ylabel: str = 'Time',
        title: str = '',
        colorbar_label: str = 'Value',
        xunit: str = 'um',
        time_unit: str = 'ns',
        mark_positions: List[float] = None,
        mark_times: List[float] = None,
        mark_colors: List[str] = None
    ):
        """
        绘制时空热图

        :param x: x轴坐标数组（位置或时间，取决于调用方）
        :param times: y轴坐标数组（时间或位置，取决于调用方）
        :param data: 数据矩阵 (n_times × n_x)
        :param cmap: 颜色映射
        :param vmin: 颜色最小值
        :param vmax: 颜色最大值
        :param log_color: 是否使用对数颜色
        :param xlim: x轴范围 (min, max)
        :param ylim: y轴范围 (min, max)
        :param mark_positions: x轴标记线列表
        :param mark_times: y轴标记线列表
        :param mark_colors: 标记线颜色列表
        """
        # 先清除之前的colorbar
        if self.colorbar:
            try:
                self.colorbar.remove()
            except:
                pass
            self.colorbar = None

        # 清除axes内容但保持位置
        self.ax.clear()
        self._coord_text = None  # text was removed by clear
        self._blit_bg = None
        self.ax.grid(False)  # 热图不需要网格

        # 重新设置边框样式
        self.ax.spines['top'].set_visible(True)
        self.ax.spines['right'].set_visible(True)
        self.ax.spines['left'].set_linewidth(0.8)
        self.ax.spines['bottom'].set_linewidth(0.8)
        self.ax.spines['top'].set_linewidth(0.8)
        self.ax.spines['right'].set_linewidth(0.8)
        self.ax.tick_params(direction='in', width=0.8, length=4, top=True, right=True)

        # 创建网格
        X, T = np.meshgrid(x, times)

        # 处理NaN值
        data = np.array(data)

        # 检查数据形状是否与网格匹配，如果不匹配则转置
        # meshgrid 产生的形状是 (len(times), len(x))
        # data 应该也是这个形状
        if data.shape != (len(times), len(x)):
            data = data.T

        valid_mask = ~np.isnan(data)

        if not np.any(valid_mask):
            self.logger.warning("热图数据全为NaN，无法绘制")
            return

        # 自动计算vmin/vmax如果未指定
        if vmin is None:
            vmin = np.nanmin(data)
        if vmax is None:
            vmax = np.nanmax(data)

        # 绘制热图
        if log_color:
            # LogNorm 要求 vmin > 0。若用户/数据给出的 vmin 非正（压强初始为 0、
            # 速度有负值等），自动用数据里的最小正值替换，避免静默回退到线性。
            # 非正的数据值会被 LogNorm 当作 under-range（显示为 colormap 最底色）。
            positive_data = data[np.isfinite(data) & (data > 0)]
            if positive_data.size > 0:
                auto_pos_min = float(positive_data.min())
            else:
                auto_pos_min = 1e-10
            if vmin is None or vmin <= 0:
                old_vmin = vmin
                vmin = auto_pos_min
                self.logger.info(
                    f"log_color: 原 vmin={old_vmin} 非正，自动调整为数据最小正值 {vmin:.3e}"
                )
            if vmax is None or vmax <= vmin:
                vmax = max(vmin * 10, float(np.nanmax(data)))
            norm = LogNorm(vmin=max(vmin, 1e-10), vmax=vmax)
            mesh = self.ax.pcolormesh(X, T, data, cmap=cmap, shading='gouraud', norm=norm)
        else:
            mesh = self.ax.pcolormesh(X, T, data, cmap=cmap, shading='gouraud',
                                     vmin=vmin, vmax=vmax)

        # 添加颜色条 - 使用固定的fraction和pad参数避免变窄
        self.colorbar = self.fig.colorbar(mesh, ax=self.ax, fraction=0.046, pad=0.04)
        self.colorbar.set_label(colorbar_label)
        self.colorbar.ax.tick_params(labelsize=9)

        # 添加位置标记线
        if mark_positions:
            mark_colors_list = mark_colors if mark_colors else ['white'] * len(mark_positions)
            for pos, color in zip(mark_positions, mark_colors_list):
                self.ax.axvline(x=pos, color=color, linestyle='--', linewidth=1.5, alpha=0.8)

        # 添加时间标记线
        if mark_times:
            for t in mark_times:
                self.ax.axhline(y=t, color='red', linestyle='--', linewidth=2, alpha=0.9)

        # 设置坐标范围
        if xlim:
            self.ax.set_xlim(xlim[0], xlim[1])
        if ylim:
            self.ax.set_ylim(ylim[0], ylim[1])

        # 设置坐标轴标签（确保单位和标签匹配）
        self.ax.set_xlabel(f'{xlabel} ({xunit})')
        self.ax.set_ylabel(f'{ylabel} ({time_unit})')
        if title:
            self.ax.set_title(title)

        # Store data for cursor value lookup
        self._heatmap_data = (x, times, data)

        self.canvas.draw_idle()
        if self._full_view is None:
            self._full_view = (self.ax.get_xlim(), self.ax.get_ylim())

    def plot_interpolated_heatmap(
        self,
        parser,
        var: str,
        n_interp_points: int = 500,
        time_unit: str = 'ns',
        xunit: str = 'um',
        coord_system: str = 'XC',
        **kwargs
    ):
        """
        绘制插值后的热图 (处理网格数不一致的情况)

        :param parser: Fort10Parser实例
        :param var: 变量名
        :param n_interp_points: 插值后的X轴点数
        :param time_unit: 时间单位 ('s' 或 'ns')
        :param xunit: 位置单位 ('cm' / 'um')；拉氏坐标下原值返回，仅作轴标签
        :param coord_system: 'XC'(质心, 欧拉) / 'X'(边界, 欧拉) /
                              'CMC'(质量坐标 cell center, 拉氏) / 'CMI'(质量坐标 cell edge, 拉氏)
        :param kwargs: 其他热图参数；可选 value_factor 用于对原始数据做线性缩放
                       (例如压强从 dyn/cm² 换算到 GPa 时传 1e-10)
        """
        transpose = kwargs.get('transpose', False)

        if not parser.is_loaded():
            self.logger.warning("解析器未加载数据")
            return

        # 获取原始数据
        times = parser.get_time_array(unit=time_unit)
        grid_pos = parser.get_grid_positions(unit=xunit, coord_system=coord_system)
        data_matrix = parser.get_spatial_data_all_times(var)

        if data_matrix.size == 0:
            self.logger.warning(f"无法获取变量 {var} 的数据")
            return

        # 单位换算（如压强）：对原始数据线性缩放，与外部传入的 vmin/vmax 单位保持一致
        value_factor = kwargs.pop('value_factor', 1.0)
        if value_factor is not None and value_factor != 1.0:
            data_matrix = data_matrix * value_factor

        # 从 kwargs 中提取并移除 transpose 参数
        transpose = kwargs.pop('transpose', False)

        # 从 kwargs 中提取标记线参数
        mark_positions = kwargs.pop('mark_positions', None)
        mark_times = kwargs.pop('mark_times', None)

        # 提取用户设置的坐标范围
        xlim = kwargs.get('xlim', None)
        ylim = kwargs.get('ylim', None)

        # ===== 拉格朗日坐标分支（CMC / CMI / NC / NI）=====
        # 拉氏坐标 time-invariant，每个 cell 永远在固定的标签上，
        # 不需要逐时间步空间插值。直接把 data_matrix 喂给 pcolormesh 即可。
        is_lagrangian = coord_system in ('CMC', 'CMI', 'NC', 'NI')
        if is_lagrangian:
            # 对齐 cell 数（CMC 长度 vs data_matrix 列数）
            n_cells_pos = len(grid_pos)
            n_cells_data = data_matrix.shape[1] if data_matrix.ndim > 1 else len(data_matrix[0])
            n_cells = min(n_cells_pos, n_cells_data)
            grid_pos = grid_pos[:n_cells]
            data_matrix = data_matrix[:, :n_cells]

            if transpose:
                # 横轴时间，纵轴质量坐标。对时间方向插值到均匀 t_grid（与欧拉分支保持一致）
                t_min = np.min(times)
                t_max = np.max(times)
                t_grid = np.linspace(t_min, t_max, n_interp_points)

                interp_data = []
                for j in range(n_cells):
                    if len(times) >= 2:
                        f = interp1d(times, data_matrix[:, j], kind='linear',
                                    bounds_error=False, fill_value=np.nan)
                        interp_data.append(f(t_grid))
                    else:
                        interp_data.append(np.full(n_interp_points, np.nan))
                # interp_data shape: (n_cells, n_times) → 转置成 (n_times, n_cells)
                interp_data = np.array(interp_data).T

                self.plot_heatmap(t_grid, grid_pos, interp_data,
                                xunit=time_unit, time_unit=xunit,
                                mark_positions=mark_times,
                                mark_times=mark_positions,
                                **kwargs)
            else:
                # 横轴质量坐标，纵轴时间。直接画，pcolormesh 会处理非均匀 CMC
                self.plot_heatmap(grid_pos, times, data_matrix,
                                xunit=xunit, time_unit=time_unit,
                                mark_positions=mark_positions,
                                mark_times=mark_times,
                                **kwargs)
            return

        # ===== 欧拉坐标分支（XC / X）—— 逐时间步空间插值 =====
        if transpose:
            # 横轴是时间，纵轴是位置
            # 确定位置范围（Y轴）用于插值
            if ylim is not None:
                # 用户设置了位置范围，优先使用
                all_min, all_max = ylim
            else:
                # 使用第一帧的位置范围
                gp_first = parser.get_grid_positions(unit=xunit, coord_system=coord_system, time_idx=0)
                if gp_first is not None and len(gp_first) > 0:
                    all_min, all_max = np.min(gp_first), np.max(gp_first)
                else:
                    all_min, all_max = np.min(grid_pos), np.max(grid_pos)

            x_grid = np.linspace(all_min, all_max, n_interp_points)

            interp_data = []
            for i in range(len(times)):
                if i < len(data_matrix):
                    gp = parser.get_grid_positions(unit=xunit, coord_system=coord_system,
                                                   time_idx=i)
                    n_pts = min(len(gp), len(data_matrix[i]))
                    x_orig = gp[:n_pts]
                    y_orig = data_matrix[i][:n_pts]

                    if len(x_orig) >= 2:
                        f = interp1d(x_orig, y_orig, kind='linear',
                                    bounds_error=False, fill_value=np.nan)
                        interp_data.append(f(x_grid))
                    else:
                        interp_data.append(np.full(n_interp_points, np.nan))
                else:
                    interp_data.append(np.full(n_interp_points, np.nan))

            # interp_data shape: (n_times, n_positions)
            interp_data = np.array(interp_data)
            # 转置用于显示：横轴时间，纵轴位置
            interp_display = interp_data.T  # (n_positions, n_times)

            # 对时间方向也插值到均匀网格
            t_min = np.min(times)
            t_max = np.max(times)
            t_grid = np.linspace(t_min, t_max, n_interp_points)

            interp_final = []
            for i in range(len(x_grid)):
                t_orig = times[:interp_display.shape[1]]
                y_orig = interp_display[i]
                if len(t_orig) >= 2:
                    f = interp1d(t_orig, y_orig, kind='linear',
                                bounds_error=False, fill_value=np.nan)
                    interp_final.append(f(t_grid))
                else:
                    interp_final.append(np.full(n_interp_points, np.nan))
            interp_final = np.array(interp_final)

            # 绘制热图：横轴是时间(t_grid)，纵轴是位置(x_grid)
            self.plot_heatmap(t_grid, x_grid, interp_final,
                            xunit=time_unit, time_unit=xunit,
                            mark_positions=mark_times,
                            mark_times=mark_positions,
                            **kwargs)
        else:
            # 横轴是位置，纵轴是时间
            # 确定位置范围（X轴）用于插值
            if xlim is not None:
                # 用户设置了位置范围，优先使用
                all_min, all_max = xlim
            else:
                # 使用第一帧的位置范围
                gp_first = parser.get_grid_positions(unit=xunit, coord_system=coord_system, time_idx=0)
                if gp_first is not None and len(gp_first) > 0:
                    all_min, all_max = np.min(gp_first), np.max(gp_first)
                else:
                    all_min, all_max = np.min(grid_pos), np.max(grid_pos)

            x_grid = np.linspace(all_min, all_max, n_interp_points)

            # 对每个时间步使用该步自己的坐标进行插值
            interp_data = []
            for i in range(len(times)):
                if i < len(data_matrix):
                    gp = parser.get_grid_positions(unit=xunit, coord_system=coord_system,
                                                   time_idx=i)
                    n_pts = min(len(gp), len(data_matrix[i]))
                    x_orig = gp[:n_pts]
                    y_orig = data_matrix[i][:n_pts]

                    if len(x_orig) >= 2:
                        f = interp1d(x_orig, y_orig, kind='linear',
                                    bounds_error=False, fill_value=np.nan)
                        interp_data.append(f(x_grid))
                    else:
                        interp_data.append(np.full(n_interp_points, np.nan))
                else:
                    interp_data.append(np.full(n_interp_points, np.nan))

            interp_data = np.array(interp_data)

            # 绘制热图：横轴是位置，纵轴是时间
            # 此时标记线保持原义：位置标记线用于垂直线（X轴），时间标记线用于水平线（Y轴）
            self.plot_heatmap(x_grid, times, interp_data,
                            xunit=xunit, time_unit=time_unit,
                            mark_positions=mark_positions,
                            mark_times=mark_times,
                            **kwargs)

    # ========== 鼠标坐标追踪 ==========

    def _on_canvas_draw(self, event):
        """Invalidate blit cache on any full canvas redraw"""
        self._blit_bg = None

    def _on_mouse_move(self, event):
        """鼠标移动时在画布右上角显示坐标（使用blitting加速）"""
        # 框选拖拽中：更新橡皮筋，跳过光标标签
        if self._zoom_press is not None:
            # 避免 blit 缓存干扰橡皮筋
            self._blit_bg = None
            self._update_zoom_rubber(event)
            return

        if event.inaxes != self.ax or event.xdata is None:
            if self._coord_text is not None and self._coord_text.get_visible():
                self._coord_text.set_visible(False)
                self._blit_redraw()
            return

        x, y = event.xdata, event.ydata

        if self._heatmap_data is not None:
            xarr, yarr, data = self._heatmap_data
            z = self._lookup_heatmap_value(xarr, yarr, data, x, y)
            if z is not None and not np.isnan(z):
                text = f'x = {x:>12.4g}\ny = {y:>12.4g}\nz = {z:>12.4e}'
            else:
                text = f'x = {x:>12.4g}\ny = {y:>12.4g}'
        else:
            text = f'x = {x:>12.4g}\ny = {y:>12.4g}'

        # Lazily create text annotation (in figure coordinates, not axes)
        if self._coord_text is None:
            self._coord_text = self.fig.text(
                0.98, 0.98, '', transform=self.fig.transFigure,
                fontsize=9, va='top', ha='right', family='monospace',
                bbox=dict(boxstyle='round,pad=0.3',
                          facecolor='white', alpha=0.85, edgecolor='#999'),
                zorder=100
            )

        self._coord_text.set_text(text)
        self._coord_text.set_visible(True)
        self._blit_redraw()

    def _on_mouse_leave(self, event):
        """鼠标离开画布时隐藏坐标"""
        if self._coord_text is not None and self._coord_text.get_visible():
            self._coord_text.set_visible(False)
            self._blit_redraw()

    def _blit_redraw(self):
        """使用blitting快速重绘光标文本（不重绘整个图形）"""
        if self._blit_bg is None:
            # Capture a clean background without the text
            if self._coord_text is not None:
                self._coord_text.set_visible(False)
            self.canvas.draw()
            self._blit_bg = self.canvas.copy_from_bbox(self.fig.bbox)

        self.canvas.restore_region(self._blit_bg)
        if self._coord_text is not None and self._coord_text.get_visible():
            self.fig.draw_artist(self._coord_text)
        self.canvas.blit(self.fig.bbox)

    def _lookup_heatmap_value(self, xarr, yarr, data, x, y):
        """查找热图在(x, y)处的值（最近邻）"""
        try:
            ix = np.argmin(np.abs(xarr - x))
            iy = np.argmin(np.abs(yarr - y))
            return float(data[iy, ix])
        except (IndexError, ValueError):
            return np.nan

    # ========== 图像保存 ==========

    def save_figure(self, filepath: str, dpi: int = 300, format: str = 'png'):
        """保存当前图像"""
        try:
            self.fig.savefig(filepath, dpi=dpi, format=format, bbox_inches='tight')
            self.logger.info(f"图像已保存至: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"保存图像失败: {e}")
            return False

    def resize(self, width: int, height: int):
        """调整画布大小"""
        self.fig.set_size_inches(width, height)
        self.canvas.draw_idle()
