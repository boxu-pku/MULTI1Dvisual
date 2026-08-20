"""ShockDetectorDialog - 冲击波检测工具

检测随时间演变的冲击波波面位置，基于密度分布的导数峰值检测，
并应用连续性约束确保相邻时刻的冲击波位置连续。
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QMessageBox, QFileDialog, QWidget, QComboBox,
    QLineEdit, QDoubleSpinBox, QCheckBox, QSplitter,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSpinBox, QTabWidget, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import numpy as np
import json
import os

from core.plot_engine import PlotEngine
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager
from scipy.signal import find_peaks
from scipy.interpolate import interp1d


def _lowess(x, y, frac=0.05, it=3):
    x, y = np.asarray(x, float), np.asarray(y, float)
    si = np.argsort(x)
    xs, ys = x[si], y[si]
    n = len(xs)
    k = max(3, min(n, int(n * frac)))
    out = ys.copy()
    for i in range(n):
        dists = np.abs(xs - xs[i])
        idx = np.argsort(dists)[:k]
        xl, yl = xs[idx], ys[idx]
        max_d = float(dists[idx[-1]])
        if max_d < 1e-15:
            out[i] = ys[i]
            continue
        u = dists[idx] / max_d
        w = np.clip((1 - u ** 3) ** 3, 0, 1)
        A = np.column_stack([np.ones(k), xl])
        try:
            beta = np.linalg.lstsq((A * w[:, None]).T @ A, (A * w[:, None]).T @ yl, rcond=None)[0]
            out[i] = beta[0] + beta[1] * xs[i]
        except np.linalg.LinAlgError:
            out[i] = ys[i]
    return xs, out


class ShockDetectorDialog(QDialog):
    """冲击波检测工具对话框"""

    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.MULTI1D可视化工具', 'shock_detector_config.json')

    def __init__(self, data_manager, heatmap_tab, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.heatmap_tab = heatmap_tab
        self.parent = parent
        self.logger = Logger.get_logger('ShockDetectorDialog')

        # 存储检测结果
        self.shock_fronts = []  # [(time_idx, position), ...]

        # 当前检测设置
        self.current_var = None
        self.current_xunit = None
        self.current_time_unit = None
        self.current_coord_system = None

        self.setWindowTitle(LanguageManager.get_text('shock_detector_title'))
        self.setMinimumSize(1200, 800)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        self.setup_ui()
        # 不在这里加载配置 - update_data()会在组合框填充后加载
        self.showMaximized()

    def setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧：QStackedWidget — page0=完整控制面板, page1=速度曲线绘图设置
        self.left_stack = QStackedWidget()
        full_scroll = self.create_control_panel()
        self.left_stack.addWidget(full_scroll)
        vel_page = QWidget()
        self._build_velocity_plot_panel(vel_page)
        self.left_stack.addWidget(vel_page)
        self.left_stack.setCurrentIndex(0)
        splitter.addWidget(self.left_stack)

        # 右侧绘图区域
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)

        splitter.setSizes([600, 1000])
        main_layout.addWidget(splitter)

    def create_control_panel(self):
        """创建控制面板"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # === 使用说明 ===
        help_group = QGroupBox(LanguageManager.get_text('help'))
        help_layout = QVBoxLayout(help_group)
        help_label = QLabel(LanguageManager.get_text('shock_help'))
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addWidget(help_group)

        # === 变量选择 ===
        self.var_group = QGroupBox(LanguageManager.get_text('variable_selection'))
        var_layout = QVBoxLayout(self.var_group)

        var_label_layout = QHBoxLayout()
        var_label_layout.addWidget(QLabel(LanguageManager.get_text('variable') + ":"))
        self.var_combo = QComboBox()
        self.var_combo.setMinimumWidth(200)
        var_label_layout.addWidget(self.var_combo)
        var_layout.addLayout(var_label_layout)

        layout.addWidget(self.var_group)

        # === 参考时刻设置 ===
        self.ref_group = QGroupBox(LanguageManager.get_text('reference_time_settings'))
        ref_layout = QVBoxLayout(self.ref_group)

        # 参考时刻表格
        self.ref_times_table = QTableWidget(0, 3)
        self.ref_times_table.setHorizontalHeaderLabels([
            LanguageManager.get_text('time_step'),
            LanguageManager.get_text('time') + ' (ns)',
            LanguageManager.get_text('search_range') + ' (' + LanguageManager.get_text('position') + ')'
        ])
        self.ref_times_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ref_times_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ref_times_table.setSelectionMode(QTableWidget.SingleSelection)
        self.ref_times_table.setMaximumHeight(150)
        self.ref_times_table.verticalHeader().setVisible(False)
        ref_layout.addWidget(self.ref_times_table)

        # 添加参考时刻的输入行
        add_ref_layout = QHBoxLayout()
        add_ref_layout.addWidget(QLabel(LanguageManager.get_text('reference_time') + ":"))
        self.ref_time_combo = QComboBox()
        self.ref_time_combo.setMinimumWidth(150)
        add_ref_layout.addWidget(self.ref_time_combo)
        ref_layout.addLayout(add_ref_layout)

        # 搜索范围输入
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel(LanguageManager.get_text('search_range') + ":"))
        self.range_min_edit = QLineEdit()
        self.range_min_edit.setPlaceholderText(LanguageManager.get_text('min_value'))
        self.range_min_edit.setMinimumWidth(80)
        range_layout.addWidget(self.range_min_edit)
        range_layout.addWidget(QLabel("-"))
        self.range_max_edit = QLineEdit()
        self.range_max_edit.setPlaceholderText(LanguageManager.get_text('max_value'))
        self.range_max_edit.setMinimumWidth(80)
        range_layout.addWidget(self.range_max_edit)
        ref_layout.addLayout(range_layout)

        # 操作按钮
        ref_btn_layout = QHBoxLayout()
        self.add_ref_btn = QPushButton(LanguageManager.get_text('add_ref_time'))
        self.add_ref_btn.clicked.connect(self._add_reference_time)
        ref_btn_layout.addWidget(self.add_ref_btn)
        self.remove_ref_btn = QPushButton(LanguageManager.get_text('remove_ref_time'))
        self.remove_ref_btn.clicked.connect(self._remove_reference_time)
        ref_btn_layout.addWidget(self.remove_ref_btn)
        self.clear_refs_btn = QPushButton(LanguageManager.get_text('clear_all'))
        self.clear_refs_btn.clicked.connect(self._clear_reference_times)
        ref_btn_layout.addWidget(self.clear_refs_btn)
        ref_layout.addLayout(ref_btn_layout)

        layout.addWidget(self.ref_group)

        # === 可视化时刻选择 ===
        vis_group = QGroupBox(LanguageManager.get_text('visualization_settings'))
        vis_layout = QVBoxLayout(vis_group)

        # 选择要可视化的时刻
        vis_time_layout = QHBoxLayout()
        vis_time_layout.addWidget(QLabel(LanguageManager.get_text('visualize_time') + ":"))
        self.vis_time_combo = QComboBox()
        self.vis_time_combo.setMinimumWidth(150)
        self.vis_time_combo.currentIndexChanged.connect(self._on_vis_time_changed)
        vis_time_layout.addWidget(self.vis_time_combo)
        vis_layout.addLayout(vis_time_layout)

        # 自动更新复选框
        self.auto_update_vis_cb = QCheckBox(LanguageManager.get_text('auto_update_visualization'))
        self.auto_update_vis_cb.setChecked(True)
        self.auto_update_vis_cb.setToolTip(LanguageManager.get_text('auto_update_vis_tooltip'))
        vis_layout.addWidget(self.auto_update_vis_cb)

        layout.addWidget(vis_group)

        # === 密度分布曲线范围设置 ===
        self.profile_range_group = QGroupBox(LanguageManager.get_text('profile_range_settings'))
        profile_range_layout = QVBoxLayout(self.profile_range_group)

        # X轴范围（位置）
        profile_x_layout = QHBoxLayout()
        profile_x_layout.addWidget(QLabel("X Range (" + LanguageManager.get_text('position') + "):"))
        self.profile_x_min_edit = QLineEdit()
        self.profile_x_min_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.profile_x_min_edit.setMinimumWidth(80)
        self.profile_x_min_edit.editingFinished.connect(self._on_profile_range_changed)
        profile_x_layout.addWidget(self.profile_x_min_edit)
        profile_x_layout.addWidget(QLabel("-"))
        self.profile_x_max_edit = QLineEdit()
        self.profile_x_max_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.profile_x_max_edit.setMinimumWidth(80)
        self.profile_x_max_edit.editingFinished.connect(self._on_profile_range_changed)
        profile_x_layout.addWidget(self.profile_x_max_edit)
        profile_range_layout.addLayout(profile_x_layout)

        # Y轴范围（密度值）
        profile_y_layout = QHBoxLayout()
        profile_y_layout.addWidget(QLabel("Y Range (" + LanguageManager.get_text('density_value') + "):"))
        self.profile_y_min_edit = QLineEdit()
        self.profile_y_min_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.profile_y_min_edit.setMinimumWidth(80)
        self.profile_y_min_edit.editingFinished.connect(self._on_profile_range_changed)
        profile_y_layout.addWidget(self.profile_y_min_edit)
        profile_y_layout.addWidget(QLabel("-"))
        self.profile_y_max_edit = QLineEdit()
        self.profile_y_max_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.profile_y_max_edit.setMinimumWidth(80)
        self.profile_y_max_edit.editingFinished.connect(self._on_profile_range_changed)
        profile_y_layout.addWidget(self.profile_y_max_edit)
        profile_range_layout.addLayout(profile_y_layout)

        layout.addWidget(self.profile_range_group)

        # === 冲击波速度设置 ===
        velocity_group = QGroupBox(LanguageManager.get_text('velocity_curve'))
        velocity_layout = QVBoxLayout(velocity_group)

        # 时间范围过滤
        vel_time_layout = QHBoxLayout()
        vel_time_layout.addWidget(QLabel(LanguageManager.get_text('velocity_range') + " (ns):"))
        self.velocity_t_min_edit = QLineEdit()
        self.velocity_t_min_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.velocity_t_min_edit.setMinimumWidth(80)
        vel_time_layout.addWidget(self.velocity_t_min_edit)
        vel_time_layout.addWidget(QLabel("-"))
        self.velocity_t_max_edit = QLineEdit()
        self.velocity_t_max_edit.setPlaceholderText(LanguageManager.get_text('auto'))
        self.velocity_t_max_edit.setMinimumWidth(80)
        vel_time_layout.addWidget(self.velocity_t_max_edit)
        velocity_layout.addLayout(vel_time_layout)

        # 平滑控制
        smooth_layout = QHBoxLayout()
        self.velocity_smooth_cb = QCheckBox(LanguageManager.get_text('enable_smoothing'))
        self.velocity_smooth_cb.setChecked(True)
        smooth_layout.addWidget(self.velocity_smooth_cb)
        smooth_layout.addWidget(QLabel(LanguageManager.get_text('window_size') + ":"))
        self.velocity_window_spin = QSpinBox()
        self.velocity_window_spin.setRange(3, 51)
        self.velocity_window_spin.setValue(7)
        self.velocity_window_spin.setSingleStep(2)
        self.velocity_window_spin.setMinimumWidth(60)
        smooth_layout.addWidget(self.velocity_window_spin)
        smooth_layout.addWidget(QLabel(LanguageManager.get_text('poly_order') + ":"))
        self.velocity_poly_spin = QSpinBox()
        self.velocity_poly_spin.setRange(1, 5)
        self.velocity_poly_spin.setValue(2)
        self.velocity_poly_spin.setMinimumWidth(60)
        smooth_layout.addWidget(self.velocity_poly_spin)
        velocity_layout.addLayout(smooth_layout)

        # Hugoniot 参数
        hugoniot_params_layout = QHBoxLayout()
        hugoniot_params_layout.addWidget(QLabel(LanguageManager.get_text('pre_shock_pressure') + ":"))
        self.p0_spin = QDoubleSpinBox()
        self.p0_spin.setRange(0.0, 1e15)
        self.p0_spin.setValue(0.0)
        self.p0_spin.setSuffix(" Pa")
        self.p0_spin.setDecimals(1)
        self.p0_spin.setMinimumWidth(120)
        hugoniot_params_layout.addWidget(self.p0_spin)
        hugoniot_params_layout.addWidget(QLabel(LanguageManager.get_text('pre_shock_density') + ":"))
        self.rho0_spin = QDoubleSpinBox()
        self.rho0_spin.setRange(1e-6, 1000.0)
        self.rho0_spin.setValue(1.0)
        self.rho0_spin.setSuffix(" g/cm³")
        self.rho0_spin.setDecimals(4)
        self.rho0_spin.setSingleStep(0.1)
        self.rho0_spin.setMinimumWidth(120)
        hugoniot_params_layout.addWidget(self.rho0_spin)
        velocity_layout.addLayout(hugoniot_params_layout)

        # ρ₂ 来源模式 + ρ₁ 检测阈值（一阶导数绝对阈值法）
        rho_mode_layout = QHBoxLayout()
        rho_mode_layout.addWidget(QLabel("ρ₂ source:"))
        self.rho_mode_combo = QComboBox()
        self.rho_mode_combo.addItem("Maximum", userData='max')
        self.rho_mode_combo.addItem("Post-shock jump (ρ₁)", userData='rho1')
        self.rho_mode_combo.setMinimumWidth(180)
        self.rho_mode_combo.currentIndexChanged.connect(self._on_rho_mode_changed)
        rho_mode_layout.addWidget(self.rho_mode_combo)

        rho_mode_layout.addWidget(QLabel("|dρ/dx| threshold:"))
        self.rho1_threshold_spin = QDoubleSpinBox()
        self.rho1_threshold_spin.setRange(1e-6, 1e3)
        self.rho1_threshold_spin.setValue(0.01)
        self.rho1_threshold_spin.setDecimals(5)
        self.rho1_threshold_spin.setSingleStep(0.001)
        self.rho1_threshold_spin.setMinimumWidth(110)
        self.rho1_threshold_spin.valueChanged.connect(self._on_rho_mode_changed)
        rho_mode_layout.addWidget(self.rho1_threshold_spin)
        rho_mode_layout.addStretch()
        velocity_layout.addLayout(rho_mode_layout)

        layout.addWidget(velocity_group)

        # === 连续性约束 ===
        continuity_group = QGroupBox(LanguageManager.get_text('continuity_constraint'))
        continuity_layout = QVBoxLayout(continuity_group)

        # 最大位置偏差
        max_dev_layout = QHBoxLayout()
        max_dev_layout.addWidget(QLabel(LanguageManager.get_text('max_position_deviation') + ":"))
        self.max_dev_spin = QDoubleSpinBox()
        self.max_dev_spin.setRange(0.1, 10000.0)
        self.max_dev_spin.setValue(50.0)
        self.max_dev_spin.setSuffix(" um")
        self.max_dev_spin.setMinimumWidth(100)
        max_dev_layout.addWidget(self.max_dev_spin)
        continuity_layout.addLayout(max_dev_layout)

        # 允许检测多条冲击波
        self.multi_shock_cb = QCheckBox(LanguageManager.get_text('allow_multiple_shocks'))
        self.multi_shock_cb.setChecked(False)
        continuity_layout.addWidget(self.multi_shock_cb)

        layout.addWidget(continuity_group)

        # === 检测选项 ===
        detect_group = QGroupBox(LanguageManager.get_text('detection_options'))
        detect_layout = QVBoxLayout(detect_group)

        # 密度变化阈值
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel(LanguageManager.get_text('density_threshold') + ":"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.001, 100.0)
        self.threshold_spin.setValue(0.2)
        self.threshold_spin.setDecimals(3)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setMinimumWidth(100)
        threshold_layout.addWidget(self.threshold_spin)
        detect_layout.addLayout(threshold_layout)

        # 显示选项
        show_layout = QHBoxLayout()
        self.show_derivative_cb = QCheckBox(LanguageManager.get_text('show_derivative_curve'))
        self.show_derivative_cb.setChecked(True)
        show_layout.addWidget(self.show_derivative_cb)

        self.show_trajectory_cb = QCheckBox(LanguageManager.get_text('show_trajectory'))
        self.show_trajectory_cb.setChecked(True)
        show_layout.addWidget(self.show_trajectory_cb)
        detect_layout.addLayout(show_layout)

        layout.addWidget(detect_group)

        # === 配置保存 ===
        config_group = QGroupBox(LanguageManager.get_text('default_config'))
        config_layout = QVBoxLayout(config_group)

        config_btn_layout = QHBoxLayout()
        self.save_config_btn = QPushButton(LanguageManager.get_text('save_config'))
        self.save_config_btn.clicked.connect(self.save_default_config)
        config_btn_layout.addWidget(self.save_config_btn)

        self.load_config_btn = QPushButton(LanguageManager.get_text('load_config'))
        self.load_config_btn.clicked.connect(self.load_default_config)
        config_btn_layout.addWidget(self.load_config_btn)
        config_layout.addLayout(config_btn_layout)

        layout.addWidget(config_group)

        # === 检测结果信息 ===
        info_group = QGroupBox(LanguageManager.get_text('detection_results'))
        info_layout = QVBoxLayout(info_group)
        self.result_info_text = QLabel(LanguageManager.get_text('no_results_yet'))
        self.result_info_text.setWordWrap(True)
        self.result_info_text.setMinimumHeight(60)
        info_layout.addWidget(self.result_info_text)
        layout.addWidget(info_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        self.detect_btn = QPushButton(LanguageManager.get_text('start_detection'))
        self.detect_btn.clicked.connect(self.detect_shock_wave)
        self.detect_btn.setMinimumHeight(35)
        btn_layout.addWidget(self.detect_btn)
        layout.addLayout(btn_layout)

        # Save image buttons
        save_layout = QHBoxLayout()
        self.save_heatmap_btn = QPushButton(LanguageManager.get_text('save_heatmap'))
        self.save_heatmap_btn.clicked.connect(self.save_heatmap_figure)
        self.save_heatmap_btn.setMinimumHeight(28)
        save_layout.addWidget(self.save_heatmap_btn)

        self.save_trajectory_btn = QPushButton(LanguageManager.get_text('save_trajectory'))
        self.save_trajectory_btn.clicked.connect(self.save_trajectory_data)
        self.save_trajectory_btn.setMinimumHeight(28)
        save_layout.addWidget(self.save_trajectory_btn)
        layout.addLayout(save_layout)

        btn_layout2 = QHBoxLayout()
        self.close_btn = QPushButton(LanguageManager.get_text('close'))
        self.close_btn.clicked.connect(self.close)
        btn_layout2.addWidget(self.close_btn)

        layout.addLayout(btn_layout2)

        layout.addStretch()

        scroll.setWidget(panel)
        return scroll

    def create_plot_panel(self):
        """创建绘图面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 第一个标签页：热图（带冲击波轨迹）
        self.heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(self.heatmap_widget)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)
        self.heatmap_plot_engine = PlotEngine(parent=self.heatmap_widget)
        heatmap_layout.addWidget(self.heatmap_plot_engine.canvas)
        self.tab_widget.addTab(self.heatmap_widget, LanguageManager.get_text('heatmap_tab'))

        # 第二个标签页：密度分布曲线
        self.density_widget = QWidget()
        density_layout = QVBoxLayout(self.density_widget)
        density_layout.setContentsMargins(0, 0, 0, 0)
        self.density_plot_engine = PlotEngine(parent=self.density_widget)
        density_layout.addWidget(self.density_plot_engine.canvas)
        self.tab_widget.addTab(self.density_widget, LanguageManager.get_text('density_profile'))

        # 第三个标签页：导数曲线
        self.derivative_widget = QWidget()
        derivative_layout = QVBoxLayout(self.derivative_widget)
        derivative_layout.setContentsMargins(0, 0, 0, 0)
        self.derivative_plot_engine = PlotEngine(parent=self.derivative_widget)
        derivative_layout.addWidget(self.derivative_plot_engine.canvas)
        self.tab_widget.addTab(self.derivative_widget, LanguageManager.get_text('derivative_curve'))

        # 第四个标签页：冲击波速度
        self.velocity_widget = QWidget()
        velocity_layout = QVBoxLayout(self.velocity_widget)
        velocity_layout.setContentsMargins(0, 0, 0, 0)
        self.velocity_plot_engine = PlotEngine(parent=self.velocity_widget)
        velocity_layout.addWidget(self.velocity_plot_engine.canvas)
        self.tab_widget.addTab(self.velocity_widget, LanguageManager.get_text('velocity_curve'))

        # 第五个标签页：Hugoniot关系
        self.hugoniot_widget = QWidget()
        hugoniot_layout = QVBoxLayout(self.hugoniot_widget)
        hugoniot_layout.setContentsMargins(0, 0, 0, 0)
        self.hugoniot_plot_engine = PlotEngine(parent=self.hugoniot_widget)
        hugoniot_layout.addWidget(self.hugoniot_plot_engine.canvas)
        self.tab_widget.addTab(self.hugoniot_widget, LanguageManager.get_text('hugoniot_relation'))

        layout.addWidget(self.tab_widget)
        self.tab_widget.currentChanged.connect(self._on_main_tab_changed)

        # 为所有画布安装全局快捷键（不依赖焦点）
        for eng in [self.heatmap_plot_engine, self.density_plot_engine,
                    self.derivative_plot_engine, self.velocity_plot_engine,
                    self.hugoniot_plot_engine]:
            eng.install_global_hotkeys(self)

        return panel

    def _on_main_tab_changed(self, idx):
        """右侧 tab 切换时切换左侧面板"""
        self.left_stack.setCurrentIndex(1 if idx == 3 else 0)

    def _build_velocity_plot_panel(self, panel):
        """紧凑的绘图设置面板（速度曲线 tab 专用）"""
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ---- 曲线样式（单行：线宽 + 颜色 + 线型 + 标记）----
        style_group = QGroupBox("Plot Style")
        sg = QVBoxLayout(style_group)
        sg.setContentsMargins(4, 4, 4, 4)
        sg.setSpacing(2)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Lw:"))
        self.vel_lw = QDoubleSpinBox(); self.vel_lw.setRange(0.5, 5); self.vel_lw.setValue(2); self.vel_lw.setSingleStep(0.25); self.vel_lw.setMinimumWidth(60)
        row1.addWidget(self.vel_lw)
        row1.addWidget(QLabel("Color:"))
        self.vel_color = QComboBox()
        for c in ['blue', 'red', 'green', 'orange', 'purple', 'black', 'brown', 'cyan']:
            self.vel_color.addItem(c, Config.get_color_code(c))
        self.vel_color.setMinimumWidth(90)
        row1.addWidget(self.vel_color)
        row1.addWidget(QLabel("Ls:"))
        self.vel_ls = QComboBox()
        for ls in ['-', '--', '-.', ':']:
            self.vel_ls.addItem(ls)
        self.vel_ls.setMinimumWidth(55)
        row1.addWidget(self.vel_ls)
        row1.addWidget(QLabel("M:"))
        self.vel_marker = QComboBox()
        for m in ['', 'o', 's', '^', 'v', 'D', 'P', '*', 'x']:
            self.vel_marker.addItem(m if m else 'None', m)
        self.vel_marker.setMinimumWidth(60)
        row1.addWidget(self.vel_marker)
        row1.addStretch()
        sg.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Ms:"))
        self.vel_ms = QDoubleSpinBox(); self.vel_ms.setRange(0, 20); self.vel_ms.setValue(6); self.vel_ms.setMinimumWidth(60)
        row2.addWidget(self.vel_ms)
        row2.addWidget(QLabel("Grid:"))
        self.vel_grid = QComboBox()
        self.vel_grid.addItems(['on', 'off']); self.vel_grid.setCurrentText('on')
        self.vel_grid.setMinimumWidth(55)
        row2.addWidget(self.vel_grid)
        row2.addWidget(QLabel("Frac:"))
        self.vel_frac = QDoubleSpinBox(); self.vel_frac.setRange(0.01, 0.5); self.vel_frac.setValue(0.05); self.vel_frac.setDecimals(3); self.vel_frac.setSingleStep(0.01); self.vel_frac.setMinimumWidth(65)
        row2.addWidget(self.vel_frac)
        row2.addStretch()
        sg.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Sm Lw:"))
        self.sm_lw = QDoubleSpinBox(); self.sm_lw.setRange(0.5, 5); self.sm_lw.setValue(1.5); self.sm_lw.setSingleStep(0.25); self.sm_lw.setMinimumWidth(55)
        row3.addWidget(self.sm_lw)
        row3.addWidget(QLabel("Clr:"))
        self.sm_color = QComboBox()
        for c in ['red', 'blue', 'green', 'orange', 'purple', 'black', 'brown', 'cyan']:
            self.sm_color.addItem(c, Config.get_color_code(c))
        self.sm_color.setMinimumWidth(80)
        row3.addWidget(self.sm_color)
        row3.addWidget(QLabel("Ls:"))
        self.sm_ls = QComboBox()
        for ls in ['--', '-', '-.', ':']: self.sm_ls.addItem(ls)
        self.sm_ls.setMinimumWidth(50)
        row3.addWidget(self.sm_ls)
        row3.addWidget(QLabel("Smooth"))
        row3.addStretch(); sg.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Vl Lw:"))
        self.vl_lw = QDoubleSpinBox(); self.vl_lw.setRange(0.5, 5); self.vl_lw.setValue(2); self.vl_lw.setSingleStep(0.25); self.vl_lw.setMinimumWidth(55)
        row4.addWidget(self.vl_lw)
        row4.addWidget(QLabel("Clr:"))
        self.vl_color = QComboBox()
        for c in ['red', 'blue', 'green', 'orange', 'purple', 'black', 'brown', 'cyan']:
            self.vl_color.addItem(c, Config.get_color_code(c))
        self.vl_color.setMinimumWidth(80)
        row4.addWidget(self.vl_color)
        row4.addWidget(QLabel("Ls:"))
        self.vl_ls = QComboBox()
        for ls in ['-', '--', '-.', ':']: self.vl_ls.addItem(ls)
        self.vl_ls.setMinimumWidth(50)
        row4.addWidget(self.vl_ls)
        row4.addWidget(QLabel("Velocity"))
        row4.addStretch(); sg.addLayout(row4)

        layout.addWidget(style_group)

        # ---- 坐标轴范围（紧凑排列）----
        rg = QGroupBox("Axis Range"); rl = QVBoxLayout(rg); rl.setContentsMargins(4, 4, 4, 4); rl.setSpacing(2)
        def _arow(parent, label, a, b):
            h = QHBoxLayout(); h.addWidget(QLabel(label))
            mn = QLineEdit(); mn.setPlaceholderText("auto"); mn.setMinimumWidth(65)
            mx = QLineEdit(); mx.setPlaceholderText("auto"); mx.setMinimumWidth(65)
            setattr(self, a, mn); setattr(self, b, mx)
            h.addWidget(mn); h.addWidget(QLabel("~")); h.addWidget(mx); h.addStretch(); parent.addLayout(h)
        _arow(rl, "X:",   "vel_x_min", "vel_x_max")
        _arow(rl, "Pos:", "vel_pos_y_min", "vel_pos_y_max")
        _arow(rl, "Max:", "vel_max_y_min", "vel_max_y_max")
        _arow(rl, "Vel:", "vel_vel_y_min", "vel_vel_y_max")
        layout.addWidget(rg)

        # ---- 标题 ----
        tg = QGroupBox("Title"); tl = QVBoxLayout(tg); tl.setContentsMargins(4, 4, 4, 4)
        hr = QHBoxLayout()
        self.vel_title = QLineEdit(); self.vel_title.setPlaceholderText("auto")
        hr.addWidget(self.vel_title); hr.addStretch(); tl.addLayout(hr); layout.addWidget(tg)

        # ---- 应用按钮 ----
        self.vel_apply_btn = QPushButton("Apply")
        self.vel_apply_btn.clicked.connect(self._replot_velocity)
        self.vel_apply_btn.setMinimumHeight(32)
        layout.addWidget(self.vel_apply_btn)

        layout.addStretch()

    def _replot_velocity(self):
        """Helper: re‑plot velocity curve with current style/range settings"""
        parser = self.data_manager.get_active_parser()
        if parser and parser.is_loaded() and hasattr(self, 'shock_fronts') and self.shock_fronts:
            self._plot_velocity_curve(parser)
        """Helper: re‑plot velocity curve with current style/range settings"""
        parser = self.data_manager.get_active_parser()
        if parser:
            self._plot_velocity_curve(parser)

    def update_data(self):
        """更新数据（从主界面热图继承设置）"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            return

        # 更新变量下拉框
        self.var_combo.clear()
        variables = parser.get_available_spatial_vars()
        for var in variables:
            display_var = var.strip()
            self.var_combo.addItem(display_var, var)

        # 如果有热图设置，同步选择
        if hasattr(self.heatmap_tab, 'var_combo') and self.heatmap_tab.var_combo.count() > 0:
            current_idx = self.heatmap_tab.var_combo.currentIndex()
            if current_idx >= 0:
                current_var = self.heatmap_tab.var_combo.itemData(current_idx)
                # 在下拉框中查找相同变量
                for i in range(self.var_combo.count()):
                    if self.var_combo.itemData(i) == current_var:
                        self.var_combo.setCurrentIndex(i)
                        break

        # 更新参考时刻下拉框
        self.ref_time_combo.clear()
        self.vis_time_combo.clear()
        times = parser.get_time_array(unit='ns')
        for i, t in enumerate(times):
            self.ref_time_combo.addItem(f"Step {i}: {t:.2f} ns", i)
            self.vis_time_combo.addItem(f"Step {i}: {t:.2f} ns", i)

        # 默认选择中间时刻作为参考
        if len(times) > 0:
            mid_idx = len(times) // 2
            self.ref_time_combo.setCurrentIndex(mid_idx)
            self.vis_time_combo.setCurrentIndex(mid_idx)

            # 设置密度分布曲线的默认范围（第一帧的位置范围）
            # 使用热图标签页的单位和坐标系设置
            xunit = self.heatmap_tab.xunit_combo.currentText() if hasattr(self.heatmap_tab, 'xunit_combo') else 'um'
            coord_system = self.heatmap_tab.coord_combo.currentData() if hasattr(self.heatmap_tab, 'coord_combo') else 'XC'

            first_grid = parser.get_grid_positions(unit=xunit, coord_system=coord_system, time_idx=0)
            if first_grid is not None and len(first_grid) > 0:
                x_min_default = np.min(first_grid)
                x_max_default = np.max(first_grid)
                # 只有在输入框为空时才设置默认值
                if not self.profile_x_min_edit.text().strip():
                    self.profile_x_min_edit.setText(f"{x_min_default:.1f}")
                if not self.profile_x_max_edit.text().strip():
                    self.profile_x_max_edit.setText(f"{x_max_default:.1f}")

        # 在组合框填充后加载配置（暂时禁用以排查问题）
        # self.load_default_config()

    def _on_vis_time_changed(self):
        """可视化时刻改变时的回调"""
        if self.current_var and hasattr(self, 'shock_fronts') and self.shock_fronts:
            # 如果已经有检测结果，重新绘制可视化曲线
            self._plot_profiles_and_derivatives_for_single_time()

    def _on_profile_range_changed(self):
        """密度分布曲线范围改变时的回调"""
        if self.current_var and hasattr(self, 'shock_fronts') and self.shock_fronts:
            # 如果已经有检测结果，重新绘制可视化曲线
            self._plot_profiles_and_derivatives_for_single_time()

    def _add_reference_time(self):
        """添加参考时刻到表格"""
        ref_idx = self.ref_time_combo.currentData()
        if ref_idx is None:
            return

        # 检查是否已存在
        for row in range(self.ref_times_table.rowCount()):
            item = self.ref_times_table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == ref_idx:
                # 已存在，更新搜索范围
                range_min = self.range_min_edit.text().strip()
                range_max = self.range_max_edit.text().strip()
                self.ref_times_table.setItem(row, 2, QTableWidgetItem(f"{range_min} ~ {range_max}"))
                return

        parser = self.data_manager.get_active_parser()
        if not parser:
            return

        times = parser.get_time_array(unit='ns')
        if ref_idx >= len(times):
            return

        row = self.ref_times_table.rowCount()
        self.ref_times_table.insertRow(row)

        # 时间步列
        time_item = QTableWidgetItem(f"Step {ref_idx}")
        time_item.setData(Qt.UserRole, ref_idx)
        time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
        self.ref_times_table.setItem(row, 0, time_item)

        # 时间列（只读）
        time_val_item = QTableWidgetItem(f"{times[ref_idx]:.2f}")
        time_val_item.setFlags(time_val_item.flags() & ~Qt.ItemIsEditable)
        self.ref_times_table.setItem(row, 1, time_val_item)

        # 搜索范围列
        range_min = self.range_min_edit.text().strip()
        range_max = self.range_max_edit.text().strip()
        self.ref_times_table.setItem(row, 2, QTableWidgetItem(f"{range_min} ~ {range_max}"))

    def _remove_reference_time(self):
        """移除选中的参考时刻"""
        row = self.ref_times_table.currentRow()
        if row >= 0:
            self.ref_times_table.removeRow(row)

    def _clear_reference_times(self):
        """清空所有参考时刻"""
        self.ref_times_table.setRowCount(0)

    def _get_reference_times(self):
        """从表格获取所有参考时刻，按时间索引排序

        Returns:
            [(time_idx, search_min_cm, search_max_cm), ...] 按time_idx排序
            search_min/max为None表示未指定
        """
        parser = self.data_manager.get_active_parser()
        if not parser:
            return []

        xunit = self.heatmap_tab.xunit_combo.currentText() if hasattr(self.heatmap_tab, 'xunit_combo') else 'um'
        refs = []
        for row in range(self.ref_times_table.rowCount()):
            item = self.ref_times_table.item(row, 0)
            if item is None:
                continue
            time_idx = item.data(Qt.UserRole)
            if time_idx is None:
                continue

            # 解析搜索范围
            search_min_cm = None
            search_max_cm = None
            range_item = self.ref_times_table.item(row, 2)
            if range_item is not None:
                text = range_item.text().strip()
                if '~' in text:
                    parts = text.split('~')
                    if len(parts) == 2:
                        try:
                            s_min = float(parts[0].strip())
                            s_max = float(parts[1].strip())
                            if xunit == 'um':
                                s_min = s_min / 1e4
                                s_max = s_max / 1e4
                            search_min_cm = s_min
                            search_max_cm = s_max
                        except ValueError:
                            pass

            refs.append((time_idx, search_min_cm, search_max_cm))

        refs.sort(key=lambda x: x[0])
        return refs

    def _plot_profiles_and_derivatives_for_single_time(self):
        """绘制单个选定时刻的密度分布和导数曲线"""
        self.density_plot_engine.clear()
        self.derivative_plot_engine.clear()

        parser = self.data_manager.get_active_parser()
        if not parser or not self.current_var:
            return

        vis_time_idx = self.vis_time_combo.currentData()
        if vis_time_idx is None:
            return

        times = parser.get_time_array(unit=self.current_time_unit)
        data_matrix = parser.get_spatial_data_all_times(self.current_var)

        if not isinstance(data_matrix, np.ndarray):
            data_matrix = np.array(data_matrix)

        if vis_time_idx >= len(data_matrix):
            return

        # 获取该时刻的数据
        row_data = data_matrix[vis_time_idx]
        if not isinstance(row_data, np.ndarray):
            row_data = np.array(row_data)

        grid = parser.get_grid_positions(unit=self.current_xunit,
                                       coord_system=self.current_coord_system,
                                       time_idx=vis_time_idx)
        n_points = min(len(grid), len(row_data))
        x_data = grid[:n_points]
        y_data = row_data[:n_points]

        # 压强变量按当前单位换算
        is_pressure = Config.is_pressure_var(self.current_var)
        if is_pressure:
            y_data = y_data * Config.get_pressure_factor()
            profile_ylabel = Config.format_pressure_label(self.current_var)
            profile_deriv_ylabel = f'd({Config.format_pressure_label(self.current_var)})/dx'
        else:
            profile_ylabel = self.current_var
            profile_deriv_ylabel = f'd({self.current_var})/dx'

        # 解析用户设置的范围
        xlim = None
        ylim = None

        x_min_text = self.profile_x_min_edit.text().strip()
        x_max_text = self.profile_x_max_edit.text().strip()
        if x_min_text and x_max_text:
            try:
                xlim = (float(x_min_text), float(x_max_text))
            except ValueError:
                pass

        y_min_text = self.profile_y_min_edit.text().strip()
        y_max_text = self.profile_y_max_edit.text().strip()
        if y_min_text and y_max_text:
            try:
                ylim = (float(y_min_text), float(y_max_text))
            except ValueError:
                pass

        # 绘制密度分布
        density_ax = self.density_plot_engine.ax
        density_ax.grid(True, linestyle='--', alpha=0.3)
        density_ax.plot(x_data, y_data, 'b-', linewidth=2, label=f"t={times[vis_time_idx]:.2f}")
        density_ax.set_xlabel(f'Position ({self.current_xunit})')
        density_ax.set_ylabel(profile_ylabel)
        density_ax.set_title(f'{profile_ylabel} at t={times[vis_time_idx]:.2f} {self.current_time_unit}')
        density_ax.legend(loc='best')

        # 应用X范围
        if xlim is not None:
            density_ax.set_xlim(xlim)

        # 应用Y范围
        if ylim is not None:
            density_ax.set_ylim(ylim)

        # 绘制导数
        dy = np.gradient(y_data, x_data)
        derivative_ax = self.derivative_plot_engine.ax
        derivative_ax.grid(True, linestyle='--', alpha=0.3)
        derivative_ax.plot(x_data, dy, 'r-', linewidth=2, alpha=0.8, label=f"t={times[vis_time_idx]:.2f}")
        derivative_ax.set_xlabel(f'Position ({self.current_xunit})')
        derivative_ax.set_ylabel(profile_deriv_ylabel)
        derivative_ax.set_title(f'Derivative at t={times[vis_time_idx]:.2f} {self.current_time_unit}')
        derivative_ax.legend(loc='best')

        # 导数图也应用相同的X范围
        if xlim is not None:
            derivative_ax.set_xlim(xlim)

        # 标记该时刻检测到的冲击波位置（如果有）
        for t_idx, pos in self.shock_fronts:
            if t_idx == vis_time_idx:
                # 在密度图上标记
                if self.current_xunit == 'um':
                    pos_plot = pos * 1e4
                else:
                    pos_plot = pos

                y_at_pos = np.interp(pos_plot, x_data, y_data) if len(x_data) > 0 else 0
                density_ax.plot(pos_plot, y_at_pos, 'g^', markersize=12,
                              label=f'Detected: {pos_plot:.1f}')
                density_ax.legend(loc='best')

                # 在导数图上标记
                dy_at_pos = np.interp(pos_plot, x_data, dy) if len(x_data) > 0 else 0
                derivative_ax.plot(pos_plot, dy_at_pos, 'g^', markersize=12,
                                  label=f'Detected: {pos_plot:.1f}')
                derivative_ax.legend(loc='best')
                break

        # 标记该时刻 ρ₁ 检测位置（一阶导数绝对阈值法）
        # 导数图上加 ±threshold 水平虚线作为参考；密度图 + 导数图都加 magenta 下三角
        if len(y_data) > 0 and len(x_data) > 0:
            threshold = self.rho1_threshold_spin.value()
            derivative_ax.axhline(threshold, color='m', linestyle=':', alpha=0.5, linewidth=1)
            derivative_ax.axhline(-threshold, color='m', linestyle=':', alpha=0.5, linewidth=1)
            rho1_idx = self._find_rho1_index(y_data, x_data, threshold)
            if 0 <= rho1_idx < len(x_data):
                x_at = x_data[rho1_idx]
                y_at = float(y_data[rho1_idx])
                density_ax.plot(x_at, y_at, 'mv', markersize=12,
                              label=f'ρ₁={y_at:.3f}')
                density_ax.legend(loc='best')
                if 0 <= rho1_idx < len(dy):
                    derivative_ax.plot(x_at, dy[rho1_idx], 'mv', markersize=12,
                                     label=f'ρ₁@{x_at:.1f}')
                    derivative_ax.legend(loc='best')

        self.density_plot_engine.canvas.draw_idle()
        self.derivative_plot_engine.canvas.draw_idle()
        self.density_plot_engine._full_view = (density_ax.get_xlim(), density_ax.get_ylim())
        self.derivative_plot_engine._full_view = (derivative_ax.get_xlim(), derivative_ax.get_ylim())

    def detect_shock_wave(self):
        """检测冲击波"""
        try:
            parser = self.data_manager.get_active_parser()
            if not parser:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                   LanguageManager.get_text('load_file_first'))
                return

            # 获取参数：var/coord_system 等所有设置都以主面板 heatmap_tab 为唯一
            # 数据源，避免 shock detector 缓存与主面板实时值分叉
            ht = self.heatmap_tab
            ht_var_idx = ht.var_combo.currentIndex()
            if ht_var_idx < 0:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                   LanguageManager.get_text('select_variable_first'))
                return
            var = ht.var_combo.itemData(ht_var_idx)
            xunit = ht.xunit_combo.currentText()
            time_unit = ht.time_unit_combo.currentText()
            coord_system = ht.coord_combo.currentData() or 'XC'

            # 同步显示用 var_combo（让用户在 UI 上看到的与实际检测的变量一致）
            for i in range(self.var_combo.count()):
                if self.var_combo.itemData(i) == var:
                    if self.var_combo.currentIndex() != i:
                        self.var_combo.blockSignals(True)
                        self.var_combo.setCurrentIndex(i)
                        self.var_combo.blockSignals(False)
                    break

            # 保存当前设置
            self.current_var = var
            self.current_xunit = xunit
            self.current_time_unit = time_unit
            self.current_coord_system = coord_system

            # 获取数据
            times = parser.get_time_array(unit=time_unit)
            data_matrix = parser.get_spatial_data_all_times(var)

            if not isinstance(data_matrix, np.ndarray):
                data_matrix = np.array(data_matrix)

            if data_matrix.size == 0:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                   LanguageManager.get_text('cannot_get_data'))
                return

            # 获取检测参数
            threshold = self.threshold_spin.value()
            # max_deviation从UI获取，单位是um，需要转换为cm用于算法
            max_deviation_cm = self.max_dev_spin.value() / 1e4  # um to cm

            allow_multiple = self.multi_shock_cb.isChecked()

            # Compute heatmap's x_grid range (in cm) for grid-based filtering.
            # Same logic as heatmap: use first frame's grid range as the fixed x_grid.
            # Shock positions outside this range correspond to white (NaN) heatmap regions.
            gp_first = parser.get_grid_positions(unit='cm', coord_system=coord_system, time_idx=0)
            if gp_first is not None and len(gp_first) > 0:
                self._heatmap_x_range_cm = (float(np.min(gp_first)), float(np.max(gp_first)))
            else:
                self._heatmap_x_range_cm = None

            # 获取参考时刻列表（从表格），如果为空则使用默认
            reference_times = self._get_reference_times()
            if not reference_times:
                # 默认使用中间时刻，无搜索范围限制
                ref_time_idx = self.ref_time_combo.currentData()
                if ref_time_idx is None:
                    ref_time_idx = len(times) // 2
                reference_times = [(ref_time_idx, None, None)]

            # 执行冲击波检测
            self.shock_fronts = self._detect_shock_fronts(
                parser, var, times, data_matrix, xunit, coord_system,
                threshold, max_deviation_cm, reference_times, allow_multiple
            )

            # 绘制结果
            self.plot_all()

            # 更新结果信息
            self._update_result_info()

        except Exception as e:
            self.logger.error(f"检测冲击波失败: {e}")
            QMessageBox.critical(self, LanguageManager.get_text('error'),
                               f"{LanguageManager.get_text('detection_failed')}: {e}")

    def _detect_shock_fronts(self, parser, var, times, data_matrix, xunit,
                            coord_system, threshold, max_deviation,
                            reference_times, allow_multiple):
        """执行冲击波检测算法 - 支持多个参考时刻的连续性约束引导检测

        Args:
            reference_times: [(time_idx, search_min_cm, search_max_cm), ...] 已按time_idx排序
        """
        n_times = len(times)
        n_data = len(data_matrix)

        # 第一步：确定每个参考时刻的冲击波位置（锚点）
        anchors = []  # [(time_idx, position_cm), ...]
        for ref_time_idx, search_min_cm, search_max_cm in reference_times:
            if ref_time_idx >= n_data:
                ref_time_idx = n_data - 1

            ref_row_data = data_matrix[ref_time_idx]
            if not isinstance(ref_row_data, np.ndarray):
                ref_row_data = np.array(ref_row_data)

            ref_grid = parser.get_grid_positions(unit='cm', coord_system=coord_system, time_idx=ref_time_idx)
            n_points = min(len(ref_grid), len(ref_row_data))
            ref_x_data = ref_grid[:n_points]
            ref_y_data = ref_row_data[:n_points]

            search_range = None
            if search_min_cm is not None and search_max_cm is not None:
                search_range = (search_min_cm, search_max_cm)

            ref_shock_pos = self._find_shock_in_range(ref_x_data, ref_y_data, threshold, search_range)

            if ref_shock_pos is not None:
                anchors.append((ref_time_idx, ref_shock_pos))
            else:
                self.logger.warning(f"参考时刻 {ref_time_idx} 未找到冲击波")

        if not anchors:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                               LanguageManager.get_text('no_peaks_found_at_ref_time'))
            return []

        # 按time_idx排序（已排序但确保一致性）
        anchors.sort(key=lambda x: x[0])

        # 第二步：分段追踪
        shock_fronts = dict()  # time_idx -> position_cm

        # 辅助函数：从start到end追踪（start < end为正向，start > end为反向）
        def track_segment(start_idx, start_pos, end_idx, end_pos=None):
            """追踪从start_idx到end_idx的冲击波轨迹"""
            segment = {}
            prev_pos = start_pos
            step = 1 if end_idx > start_idx else -1

            for i in range(start_idx + step, end_idx + step, step):
                if i < 0 or i >= n_data:
                    continue

                row_data = data_matrix[i]
                if not isinstance(row_data, np.ndarray):
                    row_data = np.array(row_data)

                grid = parser.get_grid_positions(unit='cm', coord_system=coord_system, time_idx=i)
                n_points = min(len(grid), len(row_data))
                x_data = grid[:n_points]
                y_data = row_data[:n_points]

                search_min = prev_pos - max_deviation
                search_max = prev_pos + max_deviation

                shock_pos = self._find_shock_in_range(x_data, y_data, threshold, (search_min, search_max))

                if shock_pos is not None:
                    segment[i] = shock_pos
                    prev_pos = shock_pos
                else:
                    effective_range = self._get_effective_range(x_data, y_data)
                    if effective_range is not None and effective_range[0] <= prev_pos <= effective_range[1]:
                        segment[i] = prev_pos

            return segment

        # 处理每个锚点之间的段落
        for ai, (anchor_idx, anchor_pos) in enumerate(anchors):
            # 锚点本身
            shock_fronts[anchor_idx] = anchor_pos

            # 正向追踪到下一个锚点
            if ai < len(anchors) - 1:
                next_idx, next_pos = anchors[ai + 1]
                segment = track_segment(anchor_idx, anchor_pos, next_idx - 1)
                for k, v in segment.items():
                    if k not in shock_fronts:
                        shock_fronts[k] = v
            else:
                # 最后一个锚点：向后追踪到时间终点
                segment = track_segment(anchor_idx, anchor_pos, n_data - 1)
                for k, v in segment.items():
                    if k not in shock_fronts:
                        shock_fronts[k] = v

            # 反向追踪到时间起点（仅第一个锚点）
            if ai == 0:
                segment = track_segment(anchor_idx, anchor_pos, 0)
                for k, v in segment.items():
                    if k not in shock_fronts:
                        shock_fronts[k] = v

        # 转换为排序列表
        result = sorted(shock_fronts.items(), key=lambda x: x[0])
        return result

    def _get_effective_range(self, x_data, y_data):
        """Determine valid data range using heatmap interpolation grid logic.

        The heatmap uses a fixed x_grid (from first frame's grid range) and
        interp1d with bounds_error=False, fill_value=np.nan. For each timestep,
        valid range = intersection of x_grid range and per-timestep x_orig range.
        This matches exactly where the heatmap shows data vs white (NaN) regions.

        Returns:
            (valid_min, valid_max) in cm, or None if no valid range
        """
        if len(x_data) < 2:
            return None

        x_orig_min = float(np.min(x_data))
        x_orig_max = float(np.max(x_data))

        # Intersect with heatmap's fixed x_grid range
        if hasattr(self, '_heatmap_x_range_cm') and self._heatmap_x_range_cm is not None:
            grid_min, grid_max = self._heatmap_x_range_cm
            valid_min = max(x_orig_min, grid_min)
            valid_max = min(x_orig_max, grid_max)
        else:
            valid_min = x_orig_min
            valid_max = x_orig_max

        if valid_min >= valid_max:
            return None

        return (valid_min, valid_max)

    def _find_shock_in_range(self, x_data, y_data, threshold, search_range):
        """在指定范围内寻找冲击波位置（密度变化率最大的点）

        步骤：
        1. 计算有效数据范围（热图网格范围与当前时刻数据范围的交集）
        2. 检测前：搜索范围与有效数据范围取交集
        3. 在交集内找最大梯度
        4. 检测后：位置是否在有效数据范围内

        Returns:
            冲击波位置（cm），如果没找到返回None
        """
        if len(x_data) < 3 or len(y_data) < 3:
            return None

        # Step 0: 计算该时刻的有效数据范围
        effective_range = self._get_effective_range(x_data, y_data)
        if effective_range is None:
            return None
        eff_min, eff_max = effective_range

        # Step 1: 检测前判断 - 搜索范围与有效数据范围取交集
        if search_range is None:
            search_min = eff_min
            search_max = eff_max
        else:
            search_min = max(search_range[0], eff_min)
            search_max = min(search_range[1], eff_max)
            if search_min >= search_max:
                return None

        # Step 2: 只在有效数据范围内计算梯度
        mask = (x_data >= search_min) & (x_data <= search_max)
        x_sub = x_data[mask]
        y_sub = y_data[mask]

        if len(x_sub) < 3:
            return None

        # 归一化并计算梯度
        y_min, y_max = np.min(y_sub), np.max(y_sub)
        if y_max - y_min < 1e-10:
            return None

        y_normalized = (y_sub - y_min) / (y_max - y_min)
        dy = np.abs(np.gradient(y_normalized, x_sub))

        max_idx = np.argmax(dy)
        if dy[max_idx] < threshold * 0.01:
            return None

        shock_pos = x_sub[max_idx]

        # Step 3: 检测后判断 - 位置必须在有效数据范围内
        if shock_pos < eff_min or shock_pos > eff_max:
            return None

        return shock_pos

    def _get_rho_mode(self) -> str:
        """当前 ρ₂ 提取模式：'max' 或 'rho1'"""
        if not hasattr(self, 'rho_mode_combo'):
            return 'max'
        data = self.rho_mode_combo.currentData()
        return data if data else 'max'

    def _rho_label_en(self) -> str:
        """返回当前模式对应的英文标签前缀"""
        return 'Post-jump' if self._get_rho_mode() == 'rho1' else 'Max'

    def _on_rho_mode_changed(self):
        """切换 ρ₂ 来源或阈值时重画（要求激波已检测）"""
        parser = self.data_manager.get_active_parser()
        if not parser or not self.current_var or not self.shock_fronts:
            return
        self._plot_velocity_curve(parser)
        self._plot_hugoniot_relation()

    def _find_rho1_index(self, row: np.ndarray, x_data: np.ndarray, threshold: float) -> int:
        """一阶导数绝对阈值法找 ρ₁ 在原 row 中的索引

        1. dy = np.gradient(row, x_data)，取绝对值
        2. peak_idx = argmax(|dy|)  激波跳变中心（一阶导数峰值）
        3. 从 peak_idx+1 向右扫，找第一个 |dy| < threshold 的索引
        4. 返回该索引（-1 表示失败）

        threshold 单位与 dy 一致：(row 单位) / (x_data 单位)，
        与导数图显示的数值对齐，方便用户看图校准。
        """
        valid_mask = np.isfinite(row) & np.isfinite(x_data)
        if not np.any(valid_mask):
            return -1
        y = row[valid_mask]
        x = x_data[valid_mask]
        valid_indices = np.where(valid_mask)[0]
        n = len(y)
        if n < 4:
            return -1
        dy = np.gradient(y, x)
        abs_dy = np.abs(dy)
        peak_idx = int(np.argmax(abs_dy))
        if abs_dy[peak_idx] <= threshold:
            return -1  # 全程无明显跳变
        # 从 peak_idx+1 向右找第一个 |dy| < threshold
        below = np.where(abs_dy[peak_idx + 1:] < threshold)[0]
        if len(below) == 0:
            return -1  # 一直没降到阈值以下
        k = peak_idx + 1 + int(below[0])
        return int(valid_indices[k])

    def _extract_rho_value(self, row: np.ndarray, x_data: np.ndarray,
                           mode: str, threshold: float) -> float:
        """根据模式提取代表值

        mode='max'  → np.nanmax(row)
        mode='rho1' → 一阶导数绝对阈值法找跳变后 ρ₁
        """
        if mode == 'rho1':
            idx = self._find_rho1_index(row, x_data, threshold)
            if idx < 0:
                return np.nan
            return float(row[idx])
        return float(np.nanmax(row))

    def _plot_velocity_curve(self, parser):
        """绘制冲击波位置、最大物理量和速度曲线（三子图，共享X轴）

        上图：冲击波波面位置 vs 时间
        中图：最大物理量（如密度峰值）vs 时间
        下图：冲击波速度 vs 时间（位置差分 + 平滑）
        """
        self.velocity_plot_engine.clear()

        if not self.shock_fronts or len(self.shock_fronts) < 2:
            return

        # 获取时间数组（ns）
        times_ns = parser.get_time_array(unit='ns')

        # 提取轨迹数据
        t_arr = np.array([times_ns[idx] for idx, _ in self.shock_fronts])
        pos_arr_cm = np.array([pos for _, pos in self.shock_fronts])
        time_indices = [idx for idx, _ in self.shock_fronts]

        # 位置转换为显示单位
        if self.current_xunit == 'um':
            pos_arr = pos_arr_cm * 1e4
            pos_unit = 'um'
        else:
            pos_arr = pos_arr_cm
            pos_unit = 'cm'

        # 时间范围过滤
        t_min_text = self.velocity_t_min_edit.text().strip()
        t_max_text = self.velocity_t_max_edit.text().strip()
        filter_mask = None
        if t_min_text and t_max_text:
            try:
                t_min = float(t_min_text)
                t_max = float(t_max_text)
                filter_mask = (t_arr >= t_min) & (t_arr <= t_max)
                t_arr = t_arr[filter_mask]
                pos_arr_cm = pos_arr_cm[filter_mask]
                pos_arr = pos_arr[filter_mask]
                time_indices = [time_indices[i] for i in range(len(filter_mask)) if filter_mask[i]]
            except ValueError:
                pass

        if len(t_arr) < 2:
            return

        # 提取每个时刻的物理量代表值（最大值 / 跳变后 ρ₁，由 combo 决定）
        var_name = self.current_var.strip() if self.current_var else ''
        data_matrix = parser.get_spatial_data_all_times(self.current_var)
        if not isinstance(data_matrix, np.ndarray):
            data_matrix = np.array(data_matrix)
        coord_system = self.current_coord_system
        rho_mode = self._get_rho_mode()
        threshold = self.rho1_threshold_spin.value()

        max_vals = []
        for idx in time_indices:
            if idx < len(data_matrix):
                row = data_matrix[idx]
                if not isinstance(row, np.ndarray):
                    row = np.array(row)
                gp = parser.get_grid_positions(unit='cm', coord_system=coord_system, time_idx=idx)
                n_pts = min(len(gp), len(row))
                # ρ₁ 算法的 threshold 与导数图同单位（current_xunit）
                gp_plot = gp * 1e4 if self.current_xunit == 'um' else gp
                max_vals.append(self._extract_rho_value(row[:n_pts], gp_plot[:n_pts],
                                                       rho_mode, threshold))
            else:
                max_vals.append(np.nan)
        max_vals = np.array(max_vals)

        # 计算原始速度：d(position_cm) / d(time_ns)
        velocity_cm_per_ns = np.gradient(pos_arr_cm, t_arr)
        velocity_km_per_s = velocity_cm_per_ns * 1e4

        # 平滑速度：LOWESS → 等间距网格 → 数值微分
        velocity_smoothed = velocity_km_per_s.copy()
        self._pos_equi = None
        if len(pos_arr_cm) >= 5:
            try:
                frac = self.vel_frac.value() if hasattr(self, 'vel_frac') else 0.05
                t_sorted, pos_lowess = _lowess(t_arr, pos_arr_cm, frac=frac, it=3)
                # 生成 0.1 ns 等间距时间轴
                t_min, t_max = t_arr.min(), t_arr.max()
                t_equi = np.arange(t_min, t_max + 0.1, 0.1)
                # 插值到等间距网格
                _f = interp1d(t_sorted, pos_lowess, kind='linear',
                              bounds_error=False, fill_value='extrapolate')
                pos_equi = _f(t_equi)
                # 在等间距网格上微分
                vel_equi_cm_per_ns = np.gradient(pos_equi, t_equi)
                # 插值回原始时间点
                _vf = interp1d(t_equi, vel_equi_cm_per_ns, kind='linear',
                               bounds_error=False, fill_value='extrapolate')
                velocity_smoothed = _vf(t_arr) * 1e4
                # 保存等间距平滑位置（已转显示单位）
                _pos_unit_factor = 1e4 if self.current_xunit == 'um' else 1.0
                self._t_equi = t_equi
                self._pos_equi = pos_equi * _pos_unit_factor
            except Exception as e:
                self.logger.warning(f"LOWESS 平滑失败 ({e})，回退到原始速度")

        # 三子图
        fig = self.velocity_plot_engine.fig
        fig.clear()
        ax_pos, ax_max, ax_vel = fig.subplots(3, 1, sharex=True)
        # 更新 axes 引用，确保交互功能（缩放/快捷键）操作的是当前 axes
        self.velocity_plot_engine.ax = ax_pos

        # 从简化面板读取风格设置
        _lw = self.vel_lw.value() if hasattr(self, 'vel_lw') else 2.0
        _color = self.vel_color.currentData() if hasattr(self, 'vel_color') else '#1f77b4'
        _ls = self.vel_ls.currentText() if hasattr(self, 'vel_ls') else '-'
        _mk_raw = self.vel_marker.currentData() if hasattr(self, 'vel_marker') else ''
        _mk = _mk_raw if _mk_raw else ''
        _ms = self.vel_ms.value() if hasattr(self, 'vel_ms') else 6
        # 平滑叠加线风格
        _sm_lw = self.sm_lw.value() if hasattr(self, 'sm_lw') else 1.5
        _sm_color = self.sm_color.currentData() if hasattr(self, 'sm_color') else '#d62728'
        _sm_ls = self.sm_ls.currentText() if hasattr(self, 'sm_ls') else '--'
        # 速度曲线风格
        _vl_lw = self.vl_lw.value() if hasattr(self, 'vl_lw') else 2.0
        _vl_color = self.vl_color.currentData() if hasattr(self, 'vl_color') else '#d62728'
        _vl_ls = self.vl_ls.currentText() if hasattr(self, 'vl_ls') else '-'
        # 公共
        _grid_on = (self.vel_grid.currentText() == 'on') if hasattr(self, 'vel_grid') else True
        _title = self.vel_title.text().strip() if hasattr(self, 'vel_title') else ''
        if not _title:
            _title = f'Shock Front Trajectory & Velocity ({var_name})'

        # 上图：波面位置（raw + LOWESS 平滑）
        ax_pos.plot(t_arr, pos_arr, color=_color, linewidth=_lw, linestyle=_ls,
                    marker=_mk, markersize=_ms, label=f'Position ({pos_unit})')
        if hasattr(self, '_pos_equi') and self._pos_equi is not None:
            ax_pos.plot(self._t_equi, self._pos_equi, color=_sm_color, linewidth=_sm_lw,
                        linestyle=_sm_ls, alpha=0.7, label='Smoothed')
        ax_pos.set_ylabel(f'Position ({pos_unit})')
        ax_pos.set_title(_title)
        if _grid_on: ax_pos.grid(True, linestyle='--', alpha=0.3)
        ax_pos.legend(loc='best')

        # 中图：物理量代表值
        rho_label = self._rho_label_en()
        ax_max.plot(t_arr, max_vals, color=_color, linewidth=_lw, linestyle=_ls,
                    marker=_mk, markersize=_ms, label=f'{rho_label} {var_name}')
        ax_max.set_ylabel(f'{rho_label} {var_name}')
        if _grid_on: ax_max.grid(True, linestyle='--', alpha=0.3)
        ax_max.legend(loc='best')

        # 下图：速度（只有平滑后曲线）
        ax_vel.plot(t_arr, velocity_smoothed, color=_vl_color, linewidth=_vl_lw, linestyle=_vl_ls,
                    marker=_mk, markersize=_ms, label='Smoothed')
        ax_vel.set_xlabel('Time (ns)')
        ax_vel.set_ylabel('Velocity (km/s)')
        if _grid_on: ax_vel.grid(True, linestyle='--', alpha=0.3)
        ax_vel.legend(loc='best')

        # 应用用户设置的坐标轴范围
        def _get_lim(text):
            try: return float(text)
            except: return None
        xl = _get_lim(self.vel_x_min.text()); xr = _get_lim(self.vel_x_max.text())
        if xl is not None or xr is not None:
            ax_pos.set_xlim(xl, xr)
        for ax, ymin_attr, ymax_attr in [
            (ax_pos, 'vel_pos_y_min', 'vel_pos_y_max'),
            (ax_max, 'vel_max_y_min', 'vel_max_y_max'),
            (ax_vel, 'vel_vel_y_min', 'vel_vel_y_max'),
        ]:
            yl = _get_lim(getattr(self, ymin_attr).text())
            yr = _get_lim(getattr(self, ymax_attr).text())
            if yl is not None or yr is not None:
                ax.set_ylim(yl, yr)

        fig.tight_layout()
        self.velocity_plot_engine.canvas.draw_idle()
        self.velocity_plot_engine._full_view = (ax_pos.get_xlim(), ax_pos.get_ylim())

        # 保存供 Hugoniot 计算使用
        self._hugoniot_data = (t_arr, max_vals, velocity_smoothed)

    def _plot_hugoniot_relation(self):
        """利用 Hugoniot 关系计算冲击后压强 vs 压缩比

        P = P₀ + ρ₀·D²·(1 - ρ₀/ρ₂) = P₀ + ρ₀·D²·(1 - 1/压缩比)
        D: 冲击波速度 (km/s → cm/s)
        ρ₂: 冲击后密度 (g/cm³)
        """
        self.hugoniot_plot_engine.clear()

        if not hasattr(self, '_hugoniot_data') or self._hugoniot_data is None:
            return

        t_arr, max_rho2, velocity_km_s = self._hugoniot_data
        if len(t_arr) < 2:
            return

        P0 = self.p0_spin.value()          # Pa
        rho0 = self.rho0_spin.value()       # g/cm³

        if rho0 <= 0:
            return

        # 过滤无效数据
        valid = np.isfinite(max_rho2) & np.isfinite(velocity_km_s) & (max_rho2 > 0)
        t_arr = t_arr[valid]
        max_rho2 = max_rho2[valid]
        velocity_km_s = velocity_km_s[valid]

        if len(t_arr) < 1:
            return

        # 压缩比
        compression_ratio = max_rho2 / rho0

        # 冲击波速度 D: km/s → m/s
        D_m_s = velocity_km_s * 1e3

        # ρ₀: g/cm³ → kg/m³
        rho0_kg_m3 = rho0 * 1e3

        # P = P₀ + ρ₀·D²·(1 - 1/压缩比)  [kg/m³ · (m/s)² = Pa]
        P2_Pa = P0 + rho0_kg_m3 * D_m_s**2 * (1.0 - 1.0 / compression_ratio)

        # 转换为 TPa
        P2_TPa = P2_Pa / 1e12

        # 绘图
        fig = self.hugoniot_plot_engine.fig
        fig.clear()
        ax = fig.add_subplot(111)
        self.hugoniot_plot_engine.ax = ax

        ax.plot(compression_ratio, P2_TPa, 'b-', linewidth=2, label='Hugoniot')
        ax.plot(compression_ratio, P2_TPa, 'ro', markersize=3, alpha=0.6)
        ax.set_xlabel(f'Compression Ratio (ρ₂/ρ₀)')
        ax.set_ylabel('Post-shock Pressure (TPa)')
        ax.set_title(f'Hugoniot P-ρ Curve (P₀={P0:.1f} Pa, ρ₀={rho0:.4f} g/cm³)')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='best')

        fig.tight_layout()
        self.hugoniot_plot_engine.canvas.draw_idle()
        self.hugoniot_plot_engine._full_view = (ax.get_xlim(), ax.get_ylim())

    def plot_all(self):
        """绘制所有图形"""
        parser = self.data_manager.get_active_parser()
        if not parser or not self.current_var:
            return

        # 获取数据
        times = parser.get_time_array(unit=self.current_time_unit)
        data_matrix = parser.get_spatial_data_all_times(self.current_var)

        if not isinstance(data_matrix, np.ndarray):
            data_matrix = np.array(data_matrix)

        # 绘制热图
        self._plot_heatmap_with_trajectory(parser, times, data_matrix)

        # 绘制选定时刻的密度分布和导数
        if self.show_derivative_cb.isChecked():
            self._plot_profiles_and_derivatives_for_single_time()

        # 绘制冲击波速度曲线
        if self.shock_fronts:
            self._plot_velocity_curve(parser)
            self._plot_hugoniot_relation()

    def _plot_heatmap_with_trajectory(self, parser, times, data_matrix):
        """绘制热图和冲击波轨迹

        热图部分实时读取 heatmap_tab 的所有设置（变量、单位、坐标系、色阶、
        标记线等），与主面板数据源完全一致；trajectory 叠加层独立使用检测
        时缓存的 cm 位置 + 当前的显示单位换算。这样无论用户在主面板里调什么，
        shock detector 的热图都会与主面板严格对齐，避免之前因 current_* 缓存
        与 heatmap_tab 实时值混用导致的不一致。
        """
        self.heatmap_plot_engine.clear()

        # 实时读取主面板的全部热图设置（与主面板 plot_heatmap 同源）
        ht = self.heatmap_tab
        var_idx = ht.var_combo.currentIndex()
        var = ht.var_combo.itemData(var_idx) if var_idx >= 0 else self.current_var
        xunit = ht.xunit_combo.currentText()
        time_unit = ht.time_unit_combo.currentText()
        coord_system = ht.coord_combo.currentData() or 'XC'

        # 同步显示用的 var_combo（避免与实际绘制的变量不一致）
        if var is not None:
            for i in range(self.var_combo.count()):
                if self.var_combo.itemData(i) == var:
                    if self.var_combo.currentIndex() != i:
                        self.var_combo.blockSignals(True)
                        self.var_combo.setCurrentIndex(i)
                        self.var_combo.blockSignals(False)
                    break

        axis_direction = ht.axis_combo.currentIndex()
        transpose = (axis_direction == 0)

        cmap = ht.cmap_combo.currentText()
        vmin = ht.vmin_spin.value()
        vmax = ht.vmax_spin.value()
        log_color = ht.log_color_cb.isChecked()

        xlim = None if ht.xlim_auto_cb.isChecked() else \
            (ht.xlim_min.value(), ht.xlim_max.value())
        ylim = None if ht.ylim_auto_cb.isChecked() else \
            (ht.ylim_min.value(), ht.ylim_max.value())

        # 主面板的标记线（之前丢失，导致两图视觉不一致）
        mark_positions = ht._parse_mark_values(ht.pos_mark_edit.text())
        mark_times = ht._parse_mark_values(ht.time_mark_edit.text())

        if transpose:
            xlabel = 'Time'
            ylabel = 'Position'
        else:
            xlabel = 'Position'
            ylabel = 'Time'

        # colorbar 标签与主面板完全一致
        if Config.is_pressure_var(var):
            plot_value_factor = Config.get_pressure_factor()
            colorbar_label = Config.format_pressure_label(var)
        else:
            plot_value_factor = 1.0
            colorbar_label = parser.get_variable_display_name(var)

        # 直接调用 plot_interpolated_heatmap，参数与主面板完全一致
        self.heatmap_plot_engine.plot_interpolated_heatmap(
            parser=parser,
            var=var,
            n_interp_points=500,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            log_color=log_color,
            xlim=xlim,
            ylim=ylim,
            xlabel=xlabel,
            ylabel=ylabel,
            title='',
            colorbar_label=colorbar_label,
            xunit=xunit,
            time_unit=time_unit,
            coord_system=coord_system,
            mark_positions=mark_positions,
            mark_times=mark_times,
            transpose=transpose,
            value_factor=plot_value_factor
        )

        # 绘制冲击波轨迹
        # trajectory 的 cm 位置是检测时缓存的（针对 self.current_coord_system）；
        # 显示时用主面板当前的 xunit/time_unit 做单位换算，确保和热图坐标轴对齐
        if self.show_trajectory_cb.isChecked() and self.shock_fronts:
            ax = self.heatmap_plot_engine.ax

            trajectory_x = []
            trajectory_y = []

            for time_idx, pos in self.shock_fronts:
                if time_idx >= len(times):
                    continue

                t = times[time_idx]

                if time_idx >= len(data_matrix):
                    continue

                row_data = data_matrix[time_idx]
                if not isinstance(row_data, np.ndarray):
                    row_data = np.array(row_data)

                grid = parser.get_grid_positions(unit='cm', coord_system=self.current_coord_system, time_idx=time_idx)
                if grid is None or len(grid) < 2:
                    continue

                n_points = min(len(grid), len(row_data))
                x_data = grid[:n_points]
                y_data = row_data[:n_points]

                # 使用相同的有效范围判断
                effective_range = self._get_effective_range(x_data, y_data)
                if effective_range is None:
                    continue
                data_min, data_max = effective_range

                if pos < data_min or pos > data_max:
                    continue

                # pos 是 cm 单位，用主面板当前 xunit 换算（与热图坐标轴一致）
                if xunit == 'um':
                    p = pos * 1e4  # cm to um
                else:
                    p = pos  # cm, no conversion

                if transpose:
                    trajectory_x.append(t)
                    trajectory_y.append(p)
                else:
                    trajectory_x.append(p)
                    trajectory_y.append(t)

            # 绘制轨迹线
            ax.plot(trajectory_x, trajectory_y, 'r-', linewidth=2.5, alpha=0.9,
                   label='Shock Front')

            # 绘制轨迹点
            ax.plot(trajectory_x, trajectory_y, 'ro', markersize=4, alpha=0.7)

            ax.legend(loc='best', fontsize=10)

        self.heatmap_plot_engine.canvas.draw_idle()

    def _update_result_info(self):
        """更新结果信息显示"""
        if not self.shock_fronts:
            self.result_info_text.setText(LanguageManager.get_text('no_shock_detected'))
            return

        times = self.data_manager.get_active_parser().get_time_array(unit=self.current_time_unit)

        first_t, first_pos = self.shock_fronts[0]
        last_t, last_pos = self.shock_fronts[-1]

        n_points = len(self.shock_fronts)

        info = LanguageManager.get_text('shock_detected_info').format(
            n=n_points,
            first_t=times[first_t],
            first_p=first_pos * 1e4 if self.current_xunit == 'cm' else first_pos,
            last_t=times[last_t],
            last_p=last_pos * 1e4 if self.current_xunit == 'cm' else last_pos
        )

        self.result_info_text.setText(info)

    def save_default_config(self):
        """保存为默认配置"""
        try:
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)

            # 保存参考时刻列表
            ref_times_data = []
            for row in range(self.ref_times_table.rowCount()):
                item = self.ref_times_table.item(row, 0)
                if item is None:
                    continue
                time_idx = item.data(Qt.UserRole)
                range_item = self.ref_times_table.item(row, 2)
                range_text = range_item.text() if range_item else ""
                ref_times_data.append({
                    'time_idx': time_idx,
                    'range': range_text
                })

            config_data = {
                'variable_idx': self.var_combo.currentIndex(),
                'ref_times': ref_times_data,
                'range_min': self.range_min_edit.text(),
                'range_max': self.range_max_edit.text(),
                'max_deviation': self.max_dev_spin.value(),
                'allow_multiple': self.multi_shock_cb.isChecked(),
                'threshold': self.threshold_spin.value(),
                'show_derivative': self.show_derivative_cb.isChecked(),
                'show_trajectory': self.show_trajectory_cb.isChecked(),
                'velocity_t_min': self.velocity_t_min_edit.text(),
                'velocity_t_max': self.velocity_t_max_edit.text(),
                'velocity_smooth': self.velocity_smooth_cb.isChecked(),
                'velocity_window': self.velocity_window_spin.value(),
                'velocity_poly': self.velocity_poly_spin.value(),
                'hugoniot_p0': self.p0_spin.value(),
                'hugoniot_rho0': self.rho0_spin.value()
            }

            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, LanguageManager.get_text('success'),
                                   f"{LanguageManager.get_text('config_saved')}:\n{self.CONFIG_FILE}")
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.get_text('error'),
                               f"{LanguageManager.get_text('save_config_failed')}: {e}")

    def load_default_config(self):
        """加载默认配置"""
        if not os.path.exists(self.CONFIG_FILE):
            return

        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 安全地设置索引，确保不超出范围
            var_idx = config_data.get('variable_idx', 0)
            if var_idx >= 0 and var_idx < self.var_combo.count():
                self.var_combo.setCurrentIndex(var_idx)

            self.range_min_edit.setText(config_data.get('range_min', ''))
            self.range_max_edit.setText(config_data.get('range_max', ''))
            self.max_dev_spin.setValue(config_data.get('max_deviation', 50.0))
            self.multi_shock_cb.setChecked(config_data.get('allow_multiple', False))
            self.threshold_spin.setValue(config_data.get('threshold', 0.2))
            self.show_derivative_cb.setChecked(config_data.get('show_derivative', True))
            self.show_trajectory_cb.setChecked(config_data.get('show_trajectory', True))
            self.velocity_t_min_edit.setText(config_data.get('velocity_t_min', ''))
            self.velocity_t_max_edit.setText(config_data.get('velocity_t_max', ''))
            self.velocity_smooth_cb.setChecked(config_data.get('velocity_smooth', True))
            self.velocity_window_spin.setValue(config_data.get('velocity_window', 7))
            self.velocity_poly_spin.setValue(config_data.get('velocity_poly', 2))
            self.p0_spin.setValue(config_data.get('hugoniot_p0', 0.0))
            self.rho0_spin.setValue(config_data.get('hugoniot_rho0', 1.0))

            # 恢复参考时刻表格
            ref_times_data = config_data.get('ref_times', [])
            if ref_times_data:
                parser = self.data_manager.get_active_parser()
                if parser:
                    times = parser.get_time_array(unit='ns')
                    self.ref_times_table.setRowCount(0)
                    for ref_data in ref_times_data:
                        time_idx = ref_data.get('time_idx', 0)
                        range_text = ref_data.get('range', '')
                        if time_idx < len(times):
                            row = self.ref_times_table.rowCount()
                            self.ref_times_table.insertRow(row)
                            time_item = QTableWidgetItem(f"Step {time_idx}")
                            time_item.setData(Qt.UserRole, time_idx)
                            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                            self.ref_times_table.setItem(row, 0, time_item)
                            time_val_item = QTableWidgetItem(f"{times[time_idx]:.2f}")
                            time_val_item.setFlags(time_val_item.flags() & ~Qt.ItemIsEditable)
                            self.ref_times_table.setItem(row, 1, time_val_item)
                            self.ref_times_table.setItem(row, 2, QTableWidgetItem(range_text))

            # 兼容旧配置格式（单参考时刻）
            elif 'ref_time_idx' in config_data:
                ref_idx = config_data.get('ref_time_idx', 0)
                if ref_idx >= 0 and ref_idx < self.ref_time_combo.count():
                    self.ref_time_combo.setCurrentIndex(ref_idx)
                range_min = config_data.get('range_min', '')
                range_max = config_data.get('range_max', '')
                if range_min or range_max:
                    self.range_min_edit.setText(range_min)
                    self.range_max_edit.setText(range_max)

            self.logger.info("已加载默认配置")

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")

    def save_heatmap_figure(self):
        """保存热图"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            return

        var = self.current_var if self.current_var else "heatmap"
        default_dir = os.path.dirname(parser.filepath) if hasattr(parser, 'filepath') else ""
        default_path = os.path.join(default_dir, f"{var}_shock_detection.png") if default_dir else f"{var}_shock_detection.png"

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('save_heatmap'), default_path,
            "PNG Images (*.png);;PDF Files (*.pdf);;All Files (*)"
        )

        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            self.heatmap_plot_engine.save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            QMessageBox.information(self, LanguageManager.get_text('success'),
                                   f"{LanguageManager.get_text('image_saved')}: {filepath}")

    def save_trajectory_data(self):
        """保存冲击波轨迹数据（位置、速度、密度、压强、压缩比）"""
        if not self.shock_fronts:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                               LanguageManager.get_text('no_trajectory_to_save'))
            return

        parser = self.data_manager.get_active_parser()
        default_dir = os.path.dirname(parser.filepath) if hasattr(parser, 'filepath') else ""
        default_path = os.path.join(default_dir, "shock_trajectory.csv") if default_dir else "shock_trajectory.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('save_trajectory'), default_path,
            "CSV Files (*.csv)"
        )

        if filepath:
            try:
                import csv
                times_ns = parser.get_time_array(unit='ns')
                times_display = parser.get_time_array(unit=self.current_time_unit)
                var_name = self.current_var.strip() if self.current_var else ''
                data_matrix = parser.get_spatial_data_all_times(self.current_var)
                if not isinstance(data_matrix, np.ndarray):
                    data_matrix = np.array(data_matrix)

                P0 = self.p0_spin.value()
                rho0 = self.rho0_spin.value()

                # 获取速度数据（与 _plot_velocity_curve 相同逻辑）
                t_arr = np.array([times_ns[idx] for idx, _ in self.shock_fronts])
                pos_arr_cm = np.array([pos for _, pos in self.shock_fronts])
                time_indices = [idx for idx, _ in self.shock_fronts]

                # 时间范围过滤
                t_min_text = self.velocity_t_min_edit.text().strip()
                t_max_text = self.velocity_t_max_edit.text().strip()
                if t_min_text and t_max_text:
                    try:
                        t_min = float(t_min_text)
                        t_max = float(t_max_text)
                        fmask = (t_arr >= t_min) & (t_arr <= t_max)
                        t_arr = t_arr[fmask]
                        pos_arr_cm = pos_arr_cm[fmask]
                        time_indices = [time_indices[i] for i in range(len(fmask)) if fmask[i]]
                    except ValueError:
                        pass

                # 计算平滑速度
                velocity_smoothed = np.gradient(pos_arr_cm, t_arr) * 1e4  # km/s
                if self.velocity_smooth_cb.isChecked() and len(pos_arr_cm) >= 5:
                    from scipy.signal import savgol_filter
                    window = self.velocity_window_spin.value()
                    poly = self.velocity_poly_spin.value()
                    if window % 2 == 0:
                        window += 1
                    if window > len(pos_arr_cm):
                        window = len(pos_arr_cm) if len(pos_arr_cm) % 2 == 1 else len(pos_arr_cm) - 1
                    if window >= 3 and poly < window:
                        dt = np.mean(np.diff(t_arr))
                        vel_cm_ns = savgol_filter(pos_arr_cm, window, poly, deriv=1, delta=dt)
                        velocity_smoothed = vel_cm_ns * 1e4

                # 每个时刻密度代表值（最大值或跳变后 ρ₁）
                rho_mode = self._get_rho_mode()
                threshold = self.rho1_threshold_spin.value()
                max_rho2 = []
                for idx in time_indices:
                    if idx < len(data_matrix):
                        row = data_matrix[idx]
                        if not isinstance(row, np.ndarray):
                            row = np.array(row)
                        gp = parser.get_grid_positions(unit='cm', coord_system=self.current_coord_system, time_idx=idx)
                        n_pts = min(len(gp), len(row))
                        gp_plot = gp * 1e4 if self.current_xunit == 'um' else gp
                        max_rho2.append(self._extract_rho_value(row[:n_pts], gp_plot[:n_pts],
                                                               rho_mode, threshold))
                    else:
                        max_rho2.append(np.nan)
                max_rho2 = np.array(max_rho2)

                # Hugoniot 计算
                D_m_s = velocity_smoothed * 1e3
                rho0_kg_m3 = rho0 * 1e3
                compression = np.where(max_rho2 > 0, max_rho2 / rho0, np.nan)
                P2_Pa = np.where(np.isfinite(compression) & (compression > 1),
                                 P0 + rho0_kg_m3 * D_m_s**2 * (1.0 - 1.0 / compression), np.nan)

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Time_Index',
                        f'Time (ns)',
                        f'Position ({self.current_xunit})',
                        'Position (cm)',
                        f'Velocity (km/s)',
                        f'{self._rho_label_en()} {var_name} (g/cm3)',
                        'Compression Ratio (rho2/rho0)',
                        'Post-shock Pressure (Pa)',
                        'Post-shock Pressure (TPa)'
                    ])

                    for i, idx in enumerate(time_indices):
                        pos_cm = pos_arr_cm[i]
                        if self.current_xunit == 'um':
                            pos_disp = pos_cm * 1e4
                        else:
                            pos_disp = pos_cm
                        vel = velocity_smoothed[i] if i < len(velocity_smoothed) else ''
                        rho2 = max_rho2[i] if i < len(max_rho2) else ''
                        cr = compression[i] if i < len(compression) else ''
                        p_pa = P2_Pa[i] if i < len(P2_Pa) else ''
                        p_tpa = P2_Pa[i] / 1e12 if (i < len(P2_Pa) and np.isfinite(P2_Pa[i])) else ''
                        writer.writerow([idx, f'{t_arr[i]:.4f}', f'{pos_disp:.4f}',
                                        f'{pos_cm:.6e}', f'{vel:.4f}', f'{rho2:.6e}' if rho2 != '' else '',
                                        f'{cr:.4f}' if cr != '' else '',
                                        f'{p_pa:.6e}' if p_pa != '' else '',
                                        f'{p_tpa:.4f}' if p_tpa != '' else ''])

                QMessageBox.information(self, LanguageManager.get_text('success'),
                                       f"{LanguageManager.get_text('trajectory_saved')}: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, LanguageManager.get_text('error'),
                                   f"{LanguageManager.get_text('save_failed')}: {e}")
