"""HeatmapTab - 热图标签页
绘制变量在位置-时间平面上的热图分布
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QComboBox, QPushButton,
    QDoubleSpinBox, QCheckBox, QMessageBox, QFileDialog,
    QLineEdit, QSpinBox, QScrollArea
)
from PyQt5.QtCore import Qt
import numpy as np

from core.plot_engine import PlotEngine
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class HeatmapTab(QWidget):
    """热图标签页"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.main_window = parent
        self.logger = Logger.get_logger('HeatmapTab')

        self.plot_engine = None

        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        # 右侧绘图区域
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)

        splitter.setSizes([420, 850])
        main_layout.addWidget(splitter)

    def create_control_panel(self):
        """创建控制面板"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(6)

        # === 变量选择 ===
        var_group = QGroupBox(LanguageManager.get_text('variable'))
        var_layout = QVBoxLayout(var_group)

        var_layout.addWidget(QLabel(f"{LanguageManager.get_text('variable')}:"))
        self.var_combo = QComboBox()
        self.var_combo.currentIndexChanged.connect(self._on_var_changed)
        var_layout.addWidget(self.var_combo)

        layout.addWidget(var_group)

        # === 坐标设置 ===
        coord_group = QGroupBox(LanguageManager.get_text('axis_settings'))
        coord_layout = QVBoxLayout(coord_group)

        # 方向选择（合并到坐标设置中）
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel(LanguageManager.get_text('coord_direction') + ":"))
        self.axis_combo = QComboBox()
        self.axis_combo.addItems([LanguageManager.get_text('time_x_axis'),
                                 LanguageManager.get_text('pos_x_axis')])
        self.axis_combo.setCurrentIndex(0)  # 默认横轴是时间
        axis_layout.addWidget(self.axis_combo)
        coord_layout.addLayout(axis_layout)

        # 位置单位 - 默认um
        xunit_layout = QHBoxLayout()
        xunit_layout.addWidget(QLabel(LanguageManager.get_text('xunit') + ":"))
        self.xunit_combo = QComboBox()
        self.xunit_combo.addItems(["um", "cm"])
        self.xunit_combo.setCurrentText("um")  # 默认um
        xunit_layout.addWidget(self.xunit_combo)
        coord_layout.addLayout(xunit_layout)

        # 坐标系选择 (欧拉 XC/X；拉氏 CMC/CMI)
        cs_layout = QHBoxLayout()
        cs_layout.addWidget(QLabel(LanguageManager.get_text('coord_system') + ":"))
        self.coord_combo = QComboBox()
        self.coord_combo.addItem("XC (Cell Center, Euler)", "XC")
        self.coord_combo.addItem("X (Cell Edge, Euler)", "X")
        # 拉氏项在 update_data 里按文件可用性动态添加
        self.coord_combo.setCurrentIndex(0)
        self.coord_combo.currentIndexChanged.connect(self._on_coord_system_changed)
        cs_layout.addWidget(self.coord_combo)
        coord_layout.addLayout(cs_layout)

        # 时间单位 - 默认ns
        tunit_layout = QHBoxLayout()
        tunit_layout.addWidget(QLabel(LanguageManager.get_text('timeunit') + ":"))
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.addItems(["ns", "s"])
        self.time_unit_combo.setCurrentText("ns")  # 默认ns
        tunit_layout.addWidget(self.time_unit_combo)
        coord_layout.addLayout(tunit_layout)

        # 值单位（colorbar 单位）—— 按当前变量类型自适应
        # 例如 P/PT → dyn/cm²/GPa/Mbar；T/TI/TR → eV/K；V → km/s；R/DENE → g/cm³
        vunit_layout = QHBoxLayout()
        vunit_layout.addWidget(QLabel("Value unit:"))
        self.vunit_combo = QComboBox()
        Config.load_var_units()
        self.vunit_combo.currentIndexChanged.connect(self._on_vunit_changed)
        vunit_layout.addWidget(self.vunit_combo)
        coord_layout.addLayout(vunit_layout)

        layout.addWidget(coord_group)

        # === 颜色映射 ===
        cmap_group = QGroupBox(LanguageManager.get_text('color_settings'))
        cmap_layout = QVBoxLayout(cmap_group)

        cmap_select_layout = QHBoxLayout()
        cmap_select_layout.addWidget(QLabel(LanguageManager.get_text('colormap') + ":"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(Config.COLORMAPS)
        self.cmap_combo.setCurrentText("jet")
        cmap_select_layout.addWidget(self.cmap_combo)
        cmap_layout.addLayout(cmap_select_layout)

        # 对数颜色
        self.log_color_cb = QCheckBox(LanguageManager.get_text('log_color'))
        cmap_layout.addWidget(self.log_color_cb)

        # 颜色范围
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel(f"{LanguageManager.get_text('vmin')}-{LanguageManager.get_text('vmax')}:"))
        self.vmin_spin = QDoubleSpinBox()
        self.vmin_spin.setRange(-1e15, 1e15)
        self.vmin_spin.setValue(0)
        self.vmin_spin.setDecimals(4)
        self.vmin_spin.setMinimumWidth(80)
        range_layout.addWidget(self.vmin_spin)
        range_layout.addWidget(QLabel("-"))
        self.vmax_spin = QDoubleSpinBox()
        self.vmax_spin.setRange(-1e15, 1e15)
        self.vmax_spin.setValue(3)
        self.vmax_spin.setDecimals(4)
        self.vmax_spin.setMinimumWidth(80)
        range_layout.addWidget(self.vmax_spin)
        cmap_layout.addLayout(range_layout)

        # 自动范围按钮
        self.auto_range_btn = QPushButton(LanguageManager.get_text('auto'))
        self.auto_range_btn.clicked.connect(self.auto_color_range)
        cmap_layout.addWidget(self.auto_range_btn)

        layout.addWidget(cmap_group)

        # === 坐标范围 ===
        axis_group = QGroupBox(LanguageManager.get_text('axis_settings'))
        axis_layout = QVBoxLayout(axis_group)

        # X轴范围
        xlim_layout = QHBoxLayout()
        xlim_layout.addWidget(QLabel(f"{LanguageManager.get_text('xlim')}:"))
        self.xlim_min = QDoubleSpinBox()
        self.xlim_min.setRange(-1e15, 1e15)
        self.xlim_min.setValue(0)
        self.xlim_min.setDecimals(2)
        xlim_layout.addWidget(self.xlim_min)
        xlim_layout.addWidget(QLabel("-"))
        self.xlim_max = QDoubleSpinBox()
        self.xlim_max.setRange(-1e15, 1e15)
        self.xlim_max.setValue(0)
        self.xlim_max.setDecimals(2)
        xlim_layout.addWidget(self.xlim_max)
        self.xlim_auto_cb = QCheckBox(LanguageManager.get_text('auto'))
        self.xlim_auto_cb.setChecked(True)
        xlim_layout.addWidget(self.xlim_auto_cb)
        axis_layout.addLayout(xlim_layout)

        # Y轴范围
        ylim_layout = QHBoxLayout()
        ylim_layout.addWidget(QLabel(f"{LanguageManager.get_text('ylim')}:"))
        self.ylim_min = QDoubleSpinBox()
        self.ylim_min.setRange(-1e15, 1e15)
        self.ylim_min.setValue(0)
        self.ylim_min.setDecimals(2)
        ylim_layout.addWidget(self.ylim_min)
        ylim_layout.addWidget(QLabel("-"))
        self.ylim_max = QDoubleSpinBox()
        self.ylim_max.setRange(-1e15, 1e15)
        self.ylim_max.setValue(0)
        self.ylim_max.setDecimals(2)
        ylim_layout.addWidget(self.ylim_max)
        self.ylim_auto_cb = QCheckBox(LanguageManager.get_text('auto'))
        self.ylim_auto_cb.setChecked(True)
        ylim_layout.addWidget(self.ylim_auto_cb)
        axis_layout.addLayout(ylim_layout)

        layout.addWidget(axis_group)

        # === 标记线 ===
        mark_group = QGroupBox("Mark Lines")
        mark_layout = QVBoxLayout(mark_group)

        # 位置标记（标签文字会根据坐标方向动态更新）
        pos_mark_layout = QHBoxLayout()
        self.pos_mark_label = QLabel(LanguageManager.get_text('mark_positions') + ":")
        pos_mark_layout.addWidget(self.pos_mark_label)
        self.pos_mark_edit = QLineEdit()
        self.pos_mark_edit.setPlaceholderText(LanguageManager.get_text('coord_value_placeholder'))
        pos_mark_layout.addWidget(self.pos_mark_edit)
        mark_layout.addLayout(pos_mark_layout)

        # 时间标记（标签文字会根据坐标方向动态更新）
        time_mark_layout = QHBoxLayout()
        self.time_mark_label = QLabel(LanguageManager.get_text('mark_times') + ":")
        time_mark_layout.addWidget(self.time_mark_label)
        self.time_mark_edit = QLineEdit()
        self.time_mark_edit.setPlaceholderText(LanguageManager.get_text('coord_value_placeholder'))
        time_mark_layout.addWidget(self.time_mark_edit)
        mark_layout.addLayout(time_mark_layout)

        layout.addWidget(mark_group)

        # === 绘图按钮 ===
        plot_btn_layout = QHBoxLayout()
        self.plot_btn = QPushButton(LanguageManager.get_text('plot'))
        self.plot_btn.clicked.connect(self.plot_heatmap)
        self.plot_btn.setMinimumHeight(32)
        plot_btn_layout.addWidget(self.plot_btn)

        self.clear_btn = QPushButton(LanguageManager.get_text('clear'))
        self.clear_btn.clicked.connect(self.clear_plot)
        self.clear_btn.setMinimumHeight(32)
        plot_btn_layout.addWidget(self.clear_btn)

        layout.addLayout(plot_btn_layout)

        # 保存按钮
        self.save_btn = QPushButton(LanguageManager.get_text('save_image'))
        self.save_btn.clicked.connect(self.save_figure)
        layout.addWidget(self.save_btn)

        # 导出数据按钮
        self.export_btn = QPushButton(LanguageManager.get_text('export_data'))
        self.export_btn.clicked.connect(self.export_data)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        scroll.setWidget(panel)
        return scroll

    def create_plot_panel(self):
        """创建绘图面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_engine = PlotEngine(parent=panel)
        layout.addWidget(self.plot_engine.canvas)

        return panel

    def update_data(self):
        """更新数据"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            self.clear_ui()
            return

        # 更新变量列表
        self.var_combo.clear()
        spatial_vars = parser.get_available_spatial_vars()
        for var in spatial_vars:
            display_name = parser.get_variable_display_name(var)
            self.var_combo.addItem(f"{var} - {display_name}", var)

        # 多群辐射谱变量：仅当 FREC 存在且 NG>1 时才加（NG=1 画 1 像素热图无意义）
        # I-Left/I-Right 在 NG>1 时是 (n_times, NG) 矩阵，适合用 spectrum 热图展示
        spectrum_vars_added = []
        if parser.first_dict is not None and 'FREC    ' in parser.first_dict:
            ng = len(parser.first_dict['FREC    '])
            if ng > 1 and parser.second_dict and len(parser.second_dict) > 0:
                t0_keys = parser.second_dict[0].keys()
                if 'I-Left  ' in t0_keys:
                    self.var_combo.addItem("I-Left - Boundary Spectrum (Left)", "I-Left")
                    spectrum_vars_added.append('I-Left')
                if 'I-Right ' in t0_keys:
                    self.var_combo.addItem("I-Right - Boundary Spectrum (Right)", "I-Right")
                    spectrum_vars_added.append('I-Right')

        # 设置默认颜色范围
        self.auto_color_range()

        self.logger.info(f"已更新热图数据: {len(spatial_vars)}个变量")

        # 更新坐标系选项
        available_coords = parser.get_available_coord_systems()
        self.coord_combo.blockSignals(True)
        self.coord_combo.clear()
        if 'XC' in available_coords:
            self.coord_combo.addItem("XC (Cell Center, Euler)", "XC")
        if 'X' in available_coords:
            self.coord_combo.addItem("X (Cell Edge, Euler)", "X")
        if 'CMC' in available_coords:
            self.coord_combo.addItem("CMC (Mass Center, Lagrange)", "CMC")
        if 'CMI' in available_coords:
            self.coord_combo.addItem("CMI (Mass Interface, Lagrange)", "CMI")
        if 'NC' in available_coords:
            self.coord_combo.addItem("NC (Cell Number, Lagrange)", "NC")
        if 'NI' in available_coords:
            self.coord_combo.addItem("NI (Interface Number, Lagrange)", "NI")
        if 'LC' in available_coords:
            self.coord_combo.addItem("LC (Lagrangian Cell Center)", "LC")
        if 'LI' in available_coords:
            self.coord_combo.addItem("LI (Lagrangian Interface)", "LI")
        if self.coord_combo.count() == 0:
            self.coord_combo.addItem("Default", "XC")
        self.coord_combo.setCurrentIndex(0)
        self.coord_combo.blockSignals(False)
        # 触发一次单位联动，让 xunit_combo 与第 0 项一致
        self._on_coord_system_changed(self.coord_combo.currentIndex())

    def clear_ui(self):
        """清空UI"""
        self.var_combo.clear()
        if self.plot_engine:
            self.plot_engine.clear()

    def auto_color_range(self):
        """自动计算颜色范围（按当前值单位换算）"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            return

        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            return

        var = self.var_combo.itemData(var_idx)

        # 多群谱变量：从 spectrum 矩阵取范围
        if var in ('I-Left', 'I-Right'):
            result = parser.get_boundary_spectrum(var)
            if result is None:
                return
            _, _, matrix = result
            valid = matrix[~np.isnan(matrix)]
            if valid.size > 0:
                self.vmin_spin.setValue(float(np.min(valid)))
                self.vmax_spin.setValue(float(np.max(valid)))
            return

        data = parser.get_spatial_data_all_times(var)

        if data.size > 0:
            valid_data = data[~np.isnan(data)]
            if valid_data.size > 0:
                # 按变量当前单位做线性换算（温度/压强/速度/位置/密度通用）
                unit = Config.get_current_unit_for_var(var)
                if unit:
                    valid_data = valid_data * Config.get_var_factor(var, unit)
                self.vmin_spin.setValue(float(np.min(valid_data)))
                self.vmax_spin.setValue(float(np.max(valid_data)))

    def _on_var_changed(self, idx: int):
        """变量切换：刷新 vunit_combo 的可选项 + 重算颜色范围"""
        # 1) 颜色范围
        self.auto_color_range()
        # 2) vunit_combo 按变量类别重填
        if idx < 0:
            return
        var = self.var_combo.itemData(idx)
        units = Config.get_var_units(var)
        self.vunit_combo.blockSignals(True)
        self.vunit_combo.clear()
        if units:
            for u in units:
                self.vunit_combo.addItem(u)
            # 还原该类别当前单位
            cur = Config.get_current_unit_for_var(var)
            if cur in units:
                self.vunit_combo.setCurrentText(cur)
            else:
                self.vunit_combo.setCurrentText(units[0])
            self.vunit_combo.setEnabled(True)
        else:
            # 不在任何单位类别（如 EE/EI/F 等），combo 留空禁用
            self.vunit_combo.setEnabled(False)
        self.vunit_combo.blockSignals(False)

    def _on_vunit_changed(self):
        """值单位切换：持久化 + 必要时刷新颜色范围"""
        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            return
        var = self.var_combo.itemData(var_idx)
        unit = self.vunit_combo.currentText()
        if not unit:
            return
        Config.set_current_unit_for_var(var, unit)
        Config.save_var_units()
        # 当前变量有单位类别时，颜色范围需要按新单位重算
        if Config.get_var_units(var):
            self.auto_color_range()

    def _on_coord_system_changed(self, idx: int):
        """坐标系切换时联动 xunit_combo：欧拉→cm/um，拉氏→g·um/cm³/g/cm²，编号→index"""
        if idx < 0:
            return
        cs = self.coord_combo.itemData(idx)
        self.xunit_combo.blockSignals(True)
        self.xunit_combo.clear()
        if cs in ('CMC', 'CMI'):
            # 拉氏质量坐标：单位由 xunit_combo 决定（×1e4 或原值）
            self.xunit_combo.addItems(['g·um/cm³', 'g/cm^2'])
            self.xunit_combo.setCurrentText('g·um/cm³')  # 默认 um 等效
        elif cs in ('NC', 'NI'):
            # cell/interface 编号，纯整数，无单位
            self.xunit_combo.addItems(['index'])
            self.xunit_combo.setCurrentText('index')
        else:
            self.xunit_combo.addItems(['um', 'cm'])
            self.xunit_combo.setCurrentText('um')
        self.xunit_combo.blockSignals(False)

    def plot_heatmap(self):
        """绘制热图"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('load_file_first'))
            return

        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_variable'))
            return

        var = self.var_combo.itemData(var_idx)

        # 多群辐射谱变量走单独分支（坐标系不适用，Y 轴是频率）
        if var in ('I-Left', 'I-Right'):
            self._plot_spectrum_heatmap(parser, var)
            return

        # 获取单位
        xunit = self.xunit_combo.currentText()
        time_unit = self.time_unit_combo.currentText()
        coord_system = self.coord_combo.currentData() or 'XC'

        # 解析标记位置
        mark_positions = self._parse_mark_values(self.pos_mark_edit.text())
        mark_times = self._parse_mark_values(self.time_mark_edit.text())

        # 获取颜色设置
        cmap = self.cmap_combo.currentText()
        vmin = self.vmin_spin.value()
        vmax = self.vmax_spin.value()
        log_color = self.log_color_cb.isChecked()

        # 获取坐标范围
        xlim = None if self.xlim_auto_cb.isChecked() else (self.xlim_min.value(), self.xlim_max.value())
        ylim = None if self.ylim_auto_cb.isChecked() else (self.ylim_min.value(), self.ylim_max.value())

        # 值单位换算：按变量类别（P/PT, T/TI/TR, R/DENE, V, XC/X）取因子
        # vmin/vmax 来自 spinbox，已经是当前单位的显示值（auto_color_range 已换算过）
        # 把 value_factor 传给 PlotEngine，让它把内部读取的原始数据乘以该因子，
        # 这样数据与 vmin/vmax 在同一单位下，颜色刻度才正确
        value_unit = Config.get_current_unit_for_var(var)
        plot_value_factor = Config.get_var_factor(var, value_unit) if value_unit else 1.0
        colorbar_label = Config.format_var_label(var, value_unit) if value_unit \
            else Config.format_var_label(var)

        # 根据方向设置决定标签和是否转置
        # 默认: 横轴是时间，纵轴是坐标 (transpose=True)
        # plot_heatmap 会自动拼 "... (unit)"，所以这里 xlabel/ylabel 传 plain 名字
        coord_label_base = f'{coord_system} {Config.VAR_DESCRIPTION.get(coord_system, "")}'.strip()
        if self.axis_combo.currentIndex() == 0:
            transpose = True
            xlabel = 'Time'
            ylabel = coord_label_base
        else:
            transpose = False
            xlabel = coord_label_base
            ylabel = 'Time'

        # 使用插值热图方法
        # plot_interpolated_heatmap 会根据 transpose 自动处理单位交换
        try:
            self.plot_engine.plot_interpolated_heatmap(
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

            self.main_window.status_label.setText(f"已绘制 {var} 热图")

            # 代码录制钩子
            from utils.code_recorder import CodeRecorder
            recorder = CodeRecorder()
            if recorder.is_recording:
                recorder.record_heatmap(
                    var=var,
                    xunit=xunit,
                    time_unit=time_unit,
                    coord_system=coord_system,
                    cmap=cmap,
                    vmin=vmin,
                    vmax=vmax,
                    log_color=log_color,
                    transpose=transpose,
                    xlim=xlim,
                    ylim=ylim,
                    mark_positions=mark_positions,
                    mark_times=mark_times,
                    value_unit=value_unit,
                    value_factor=plot_value_factor
                )
                if self.main_window.code_recorder_dialog is not None:
                    self.main_window.code_recorder_dialog.update_count()
        except Exception as e:
            self.logger.error(f"绘制热图失败: {e}")
            QMessageBox.warning(self, LanguageManager.get_text('warning'), f"{LanguageManager.get_text('plot_heatmap_failed')}: {e}")

    def _plot_spectrum_heatmap(self, parser, var: str):
        """多群辐射谱热图：横轴时间，纵轴频率群中心（FREC），颜色 = 通量

        NG>1 时才有意义。直接调 plot_heatmap，不走 plot_interpolated_heatmap
        （spectrum 没有逐时间步空间插值的概念）。
        """
        try:
            result = parser.get_boundary_spectrum(var)
            if result is None:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                   f"无法获取 {var} 的多群谱数据（可能 FREC 缺失）")
                return
            times_s, freq_centers, matrix = result  # matrix.shape = (n_times, NG)

            time_unit = self.time_unit_combo.currentText()
            times_plot = times_s * 1e9 if time_unit == 'ns' else times_s

            cmap = self.cmap_combo.currentText()
            vmin = self.vmin_spin.value()
            vmax = self.vmax_spin.value()
            log_color = self.log_color_cb.isChecked()
            xlim = None if self.xlim_auto_cb.isChecked() else (self.xlim_min.value(), self.xlim_max.value())
            ylim = None if self.ylim_auto_cb.isChecked() else (self.ylim_min.value(), self.ylim_max.value())

            # 数据矩阵转置为 (n_freqs, n_times) 以匹配 plot_heatmap 的 (n_y, n_x) 约定
            data_for_plot = matrix.T  # (NG, n_times)

            label = 'Left Boundary' if var == 'I-Left' else 'Right Boundary'
            colorbar_label = f'{var} {label} Spectrum'

            self.plot_engine.plot_heatmap(
                x=times_plot,
                times=freq_centers,
                data=data_for_plot,
                cmap=cmap, vmin=vmin, vmax=vmax, log_color=log_color,
                xlim=xlim, ylim=ylim,
                xlabel='Time', ylabel='Frequency',
                title='',
                colorbar_label=colorbar_label,
                xunit=time_unit, time_unit='Hz',
            )

            self.main_window.status_label.setText(
                f"已绘制 {var} 多群谱热图 (NG={len(freq_centers)})"
            )
        except Exception as e:
            self.logger.error(f"绘制谱热图失败: {e}")
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                               f"{LanguageManager.get_text('plot_heatmap_failed')}: {e}")

    def _parse_mark_values(self, text: str) -> list:
        """解析标记值"""
        if not text.strip():
            return []

        values = []
        for part in text.split(','):
            try:
                values.append(float(part.strip()))
            except ValueError:
                continue
        return values

    def _export_spectrum_csv(self, parser, var: str, time_unit: str):
        """多群谱变量 CSV 导出：每行一个时间步，每列一个频率群"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出谱数据", f"{var}_spectrum.csv", "CSV文件 (*.csv)"
        )
        if not filepath:
            return
        try:
            import csv
            result = parser.get_boundary_spectrum(var)
            if result is None:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                   f"无法获取 {var} 的多群谱数据")
                return
            times_s, freq_centers, matrix = result  # matrix (n_times, NG)
            times_plot = times_s * 1e9 if time_unit == 'ns' else times_s

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                header = [f'Time ({time_unit})']
                for j, fc in enumerate(freq_centers):
                    header.append(f'{var} group{j+1} (FREC={fc:.3e} Hz)')
                writer.writerow(header)
                for i, t in enumerate(times_plot):
                    row = [f'{t:.6e}']
                    for j in range(len(freq_centers)):
                        v = matrix[i, j]
                        row.append(f'{v:.6e}' if np.isfinite(v) else '')
                    writer.writerow(row)
            self.main_window.status_label.setText(f"数据已导出: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def clear_plot(self):
        """清空画布"""
        if self.plot_engine:
            try:
                self.plot_engine.clear()
            except Exception as e:
                self.logger.error(f"清空画布失败: {e}")

    def save_figure(self):
        """保存图片"""
        if not self.plot_engine:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图片", "", "PNG图片 (*.png);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            self.plot_engine.save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            self.main_window.status_label.setText(f"图片已保存: {filepath}")

    def export_data(self):
        """导出热图数据为CSV"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('load_file_first'))
            return

        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_variable'))
            return

        var = self.var_combo.itemData(var_idx)
        xunit = self.xunit_combo.currentText()
        time_unit = self.time_unit_combo.currentText()

        # 多群谱变量的 CSV 导出（时间 × 频率）
        if var in ('I-Left', 'I-Right'):
            self._export_spectrum_csv(parser, var, time_unit)
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出数据", f"{var}_heatmap.csv", "CSV文件 (*.csv)"
        )

        if filepath:
            try:
                import csv
                from scipy.interpolate import interp1d

                times = parser.get_time_array(unit=time_unit)
                coord_system = self.coord_combo.currentData() or 'XC'
                grid_pos = parser.get_grid_positions(unit=xunit, coord_system=coord_system)
                data_matrix = parser.get_spatial_data_all_times(var)

                if data_matrix.size == 0:
                    QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('cannot_get_data'))
                    return

                # 按当前值单位换算（通用）
                value_unit = Config.get_current_unit_for_var(var)
                if value_unit:
                    data_matrix = data_matrix * Config.get_var_factor(var, value_unit)
                    value_col_unit = value_unit
                else:
                    value_col_unit = parser.get_variable_display_name(var)

                # 插值处理
                n_points = 500
                x_min = np.min(grid_pos)
                x_max = np.max(grid_pos)
                x_grid = np.linspace(x_min, x_max, n_points)

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)

                    # 写入表头
                    coord_label_base = f'{coord_system} {Config.VAR_DESCRIPTION.get(coord_system, "")}'.strip()
                    header = [f'{coord_label_base} ({xunit})']
                    for t in times:
                        header.append(f'{var} @ t={t:.4f}{time_unit} ({value_col_unit})')
                    writer.writerow(header)

                    # 插值并写入数据
                    for xi, x in enumerate(x_grid):
                        row = [f'{x:.6e}']
                        for ti in range(len(times)):
                            if ti < len(data_matrix):
                                x_orig = grid_pos[:len(data_matrix[ti])]
                                y_orig = data_matrix[ti]
                                if len(x_orig) >= 2:
                                    try:
                                        f_interp = interp1d(x_orig, y_orig, kind='linear',
                                                           bounds_error=False, fill_value=np.nan)
                                        val = f_interp(x)
                                        row.append(f'{val:.6e}' if not np.isnan(val) else '')
                                    except:
                                        row.append('')
                                else:
                                    row.append('')
                            else:
                                row.append('')
                        writer.writerow(row)

                self.main_window.status_label.setText(f"数据已导出: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
