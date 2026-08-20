"""SpatialTab - 空间图标签页
绘制变量随网格编号/位置的变化曲线
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox, QFileDialog, QMenu, QAction,
    QAbstractItemView, QFrame, QToolButton, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import numpy as np

from core.plot_engine import PlotEngine
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class SpatialTab(QWidget):
    """空间图标签页"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.main_window = parent
        self.logger = Logger.get_logger('SpatialTab')

        self.plot_engine = None
        self.selected_times = {}  # {time_idx: {'color': str, 'linestyle': str, 'enabled': bool}}

        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        # 右侧绘图区域
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)

        splitter.setSizes([380, 800])
        main_layout.addWidget(splitter)

    def create_control_panel(self):
        """创建控制面板"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(6)

        # === 变量选择 ===
        var_group = QGroupBox(LanguageManager.get_text('variable_selection'))
        var_layout = QVBoxLayout(var_group)

        # Y轴变量
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel(LanguageManager.get_text('y_variable') + ":"))
        self.var_combo = QComboBox()
        self.var_combo.setMinimumWidth(120)
        self.var_combo.currentIndexChanged.connect(self._on_var_changed)
        y_layout.addWidget(self.var_combo)
        var_layout.addLayout(y_layout)

        # Y 轴变量单位（按变量类型自适应：P→dyn/GPa/Mbar，T→eV/K，V→km/s 等）
        yunit_layout = QHBoxLayout()
        yunit_layout.addWidget(QLabel("Y unit:"))
        self.yunit_combo = QComboBox()
        self.yunit_combo.currentIndexChanged.connect(self._on_yunit_changed)
        yunit_layout.addWidget(self.yunit_combo)
        var_layout.addLayout(yunit_layout)

        # X轴单位选择
        xunit_layout = QHBoxLayout()
        xunit_layout.addWidget(QLabel(LanguageManager.get_text('xunit') + ":"))
        self.xunit_combo = QComboBox()
        self.xunit_combo.addItems(["cm", "um"])
        self.xunit_combo.setCurrentText("um")  # 默认使用um
        xunit_layout.addWidget(self.xunit_combo)
        var_layout.addLayout(xunit_layout)

        # 坐标系选择 (欧拉 XC/X；拉氏 CMC/CMI)
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel(LanguageManager.get_text('coord_system') + ":"))
        self.coord_combo = QComboBox()
        self.coord_combo.addItem("XC (Cell Center, Euler)", "XC")
        self.coord_combo.addItem("X (Cell Edge, Euler)", "X")
        # 拉氏项在 update_data 里按文件可用性动态添加
        self.coord_combo.setCurrentIndex(0)
        self.coord_combo.currentIndexChanged.connect(self._on_coord_system_changed)
        coord_layout.addWidget(self.coord_combo)
        var_layout.addLayout(coord_layout)

        layout.addWidget(var_group)

        # === 时刻选择 ===
        time_group = QGroupBox(LanguageManager.get_text('moments'))
        time_layout = QVBoxLayout(time_group)

        # 时刻列表
        self.time_list = QListWidget()
        self.time_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.time_list.setMinimumHeight(120)
        self.time_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.time_list.customContextMenuRequested.connect(self.show_time_context_menu)
        time_layout.addWidget(self.time_list)

        # 时刻选择按钮行
        time_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(LanguageManager.get_text('select_all'))
        self.select_all_btn.clicked.connect(self.select_all_times)
        time_btn_layout.addWidget(self.select_all_btn)

        self.invert_btn = QPushButton(LanguageManager.get_text('select_inverse'))
        self.invert_btn.clicked.connect(self.invert_selection)
        time_btn_layout.addWidget(self.invert_btn)

        self.clear_btn = QPushButton(LanguageManager.get_text('clear'))
        self.clear_btn.clicked.connect(self.clear_selection)
        time_btn_layout.addWidget(self.clear_btn)

        time_layout.addLayout(time_btn_layout)

        # 删除/取消删除按钮行
        del_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton(LanguageManager.get_text('remove_selected'))
        self.delete_btn.clicked.connect(self.delete_selected)
        del_btn_layout.addWidget(self.delete_btn)

        self.undelete_btn = QPushButton(LanguageManager.get_text('cancel_delete'))
        self.undelete_btn.clicked.connect(self.undelete_selected)
        del_btn_layout.addWidget(self.undelete_btn)

        time_layout.addLayout(del_btn_layout)

        layout.addWidget(time_group)

        # === 样式设置 ===
        style_group = QGroupBox(LanguageManager.get_text('style_settings'))
        style_layout = QVBoxLayout(style_group)

        # 第一行：颜色、线型、显示图例
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel(LanguageManager.get_text('color') + ":"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(Config.COLORS)
        self.color_combo.setCurrentText("black")
        row1_layout.addWidget(self.color_combo)
        row1_layout.addSpacing(10)
        row1_layout.addWidget(QLabel(LanguageManager.get_text('line_style') + ":"))
        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':'])
        self.linestyle_combo.setCurrentIndex(0)
        self.linestyle_combo.setToolTip("Solid / Dashed / Dash-dot / Dotted")
        row1_layout.addWidget(self.linestyle_combo)
        row1_layout.addSpacing(10)
        self.show_legend_cb = QCheckBox(LanguageManager.get_text('show_legend'))
        self.show_legend_cb.setChecked(False)  # 默认关闭
        row1_layout.addWidget(self.show_legend_cb)
        row1_layout.addStretch()
        style_layout.addLayout(row1_layout)

        # 第二行：线宽和应用按钮
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel(LanguageManager.get_text('line_width') + ":"))
        self.linewidth_spin = QDoubleSpinBox()
        self.linewidth_spin.setRange(0.5, 5.0)
        self.linewidth_spin.setValue(1.5)
        self.linewidth_spin.setSingleStep(0.5)
        row2_layout.addWidget(self.linewidth_spin)
        row2_layout.addStretch()
        self.apply_style_btn = QPushButton(LanguageManager.get_text('apply'))
        self.apply_style_btn.clicked.connect(self.apply_style_to_selected)
        row2_layout.addWidget(self.apply_style_btn)
        style_layout.addLayout(row2_layout)

        layout.addWidget(style_group)

        # === 坐标轴设置 ===
        axis_group = QGroupBox(LanguageManager.get_text('axis_settings'))
        axis_layout = QVBoxLayout(axis_group)

        # LOG坐标选项
        log_layout = QHBoxLayout()
        self.log_x_cb = QCheckBox("Log X Axis")
        log_layout.addWidget(self.log_x_cb)
        self.log_y_cb = QCheckBox("Log Y Axis")
        log_layout.addWidget(self.log_y_cb)
        axis_layout.addLayout(log_layout)

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

        # === 绘图按钮 ===
        plot_btn_layout = QHBoxLayout()
        self.plot_btn = QPushButton(LanguageManager.get_text('plot'))
        self.plot_btn.clicked.connect(self.plot_spatial)
        self.plot_btn.setMinimumHeight(32)
        plot_btn_layout.addWidget(self.plot_btn)

        self.clear_plot_btn = QPushButton(LanguageManager.get_text('clear_plot'))
        self.clear_plot_btn.clicked.connect(self.clear_plot)
        self.clear_plot_btn.setMinimumHeight(32)
        plot_btn_layout.addWidget(self.clear_plot_btn)

        layout.addLayout(plot_btn_layout)

        # 保存/导出按钮
        io_btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(LanguageManager.get_text('save_image'))
        self.save_btn.clicked.connect(self.save_figure)
        io_btn_layout.addWidget(self.save_btn)

        self.export_btn = QPushButton(LanguageManager.get_text('export_data'))
        self.export_btn.clicked.connect(self.export_data)
        io_btn_layout.addWidget(self.export_btn)

        layout.addLayout(io_btn_layout)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    def create_plot_panel(self):
        """创建绘图面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建绘图引擎
        self.plot_engine = PlotEngine(parent=panel)
        layout.addWidget(self.plot_engine.canvas)

        return panel

    def update_data(self):
        """更新数据（当文件加载后调用）"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            self.clear_ui()
            return

        # 更新变量列表（阻塞信号避免每个 addItem 都触发 _on_var_changed）
        self.var_combo.blockSignals(True)
        self.var_combo.clear()
        spatial_vars = parser.get_available_spatial_vars()
        for var in spatial_vars:
            display_name = parser.get_variable_display_name(var)
            self.var_combo.addItem(f"{var} - {display_name}", var)
        self.var_combo.blockSignals(False)
        # 手动触发一次让 yunit_combo 同步到第一个变量
        if self.var_combo.count() > 0:
            self._on_var_changed(self.var_combo.currentIndex())

        # 更新时刻列表
        self.time_list.clear()
        self.selected_times.clear()

        times = parser.get_time_array(unit='ns')  # 默认使用ns
        for i, t in enumerate(times):
            item = QListWidgetItem(f"#{i}: {t:.4f} ns")
            item.setData(Qt.UserRole, i)
            item.setSelected(False)
            self.time_list.addItem(item)
            # 默认样式 - 黑色
            self.selected_times[i] = {
                'color': 'black',
                'linestyle': '-',
                'linewidth': 1.5,
                'enabled': True
            }

        self.logger.info(f"已更新空间图数据: {len(spatial_vars)}个变量, {len(times)}个时刻")

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
        # 触发一次 xunit 联动
        self._on_coord_system_changed(self.coord_combo.currentIndex())

    def _on_coord_system_changed(self, idx: int):
        """坐标系切换时联动 xunit_combo：欧拉→cm/um，拉氏→g·um/cm³/g/cm²，编号→index"""
        if idx < 0:
            return
        cs = self.coord_combo.itemData(idx)
        self.xunit_combo.blockSignals(True)
        self.xunit_combo.clear()
        if cs in ('CMC', 'CMI'):
            self.xunit_combo.addItems(['g·um/cm³', 'g/cm^2'])
            self.xunit_combo.setCurrentText('g·um/cm³')
        elif cs in ('NC', 'NI'):
            self.xunit_combo.addItems(['index'])
            self.xunit_combo.setCurrentText('index')
        else:
            self.xunit_combo.addItems(['cm', 'um'])
            self.xunit_combo.setCurrentText('um')
        self.xunit_combo.blockSignals(False)

    def _on_var_changed(self, idx: int):
        """Y 轴变量切换：同步 yunit_combo 的可选项"""
        if idx < 0:
            return
        var = self.var_combo.itemData(idx)
        units = Config.get_var_units(var)
        self.yunit_combo.blockSignals(True)
        self.yunit_combo.clear()
        if units:
            for u in units:
                self.yunit_combo.addItem(u)
            cur = Config.get_current_unit_for_var(var)
            if cur in units:
                self.yunit_combo.setCurrentText(cur)
            else:
                self.yunit_combo.setCurrentText(units[0])
            self.yunit_combo.setEnabled(True)
        else:
            self.yunit_combo.setEnabled(False)
        self.yunit_combo.blockSignals(False)

    def _on_yunit_changed(self):
        """Y 轴单位切换：记到 Config（per-category）"""
        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            return
        var = self.var_combo.itemData(var_idx)
        unit = self.yunit_combo.currentText()
        if not unit:
            return
        Config.set_current_unit_for_var(var, unit)
        Config.save_var_units()

    def clear_ui(self):
        """清空UI"""
        self.var_combo.clear()
        self.time_list.clear()
        self.selected_times.clear()
        if self.plot_engine:
            self.plot_engine.clear()

    def select_all_times(self):
        """全选所有时刻"""
        self.time_list.selectAll()

    def invert_selection(self):
        """反选"""
        for i in range(self.time_list.count()):
            item = self.time_list.item(i)
            item.setSelected(not item.isSelected())

    def clear_selection(self):
        """清除选择"""
        self.time_list.clearSelection()

    def delete_selected(self):
        """删除选中的时刻（不绘制）"""
        for item in self.time_list.selectedItems():
            idx = item.data(Qt.UserRole)
            self.selected_times[idx]['enabled'] = False
            # 用灰色文字表示已删除
            item.setForeground(QBrush(Qt.gray))
            # 添加删除标记
            text = item.text()
            if "(deleted)" not in text:
                item.setText(text + " (deleted)")

        self.main_window.status_label.setText(f"已标记 {len(self.time_list.selectedItems())} 个时刻为不绘制")
        # 自动更新画布
        self.plot_spatial()

    def undelete_selected(self):
        """取消删除选中的时刻"""
        count = 0
        for item in self.time_list.selectedItems():
            idx = item.data(Qt.UserRole)
            if not self.selected_times[idx].get('enabled', True):
                self.selected_times[idx]['enabled'] = True
                item.setForeground(QBrush(Qt.black))
                # 移除删除标记
                text = item.text().replace(" (deleted)", "")
                item.setText(text)
                count += 1

        if count > 0:
            self.main_window.status_label.setText(f"已恢复 {count} 个时刻")
            # 自动更新画布
            self.plot_spatial()

    def show_time_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()

        restore_action = QAction("恢复选中（恢复绘制）", self)
        restore_action.triggered.connect(self.undelete_selected)
        menu.addAction(restore_action)

        menu.exec_(self.time_list.mapToGlobal(position))

    def _set_item_color(self, item, color_name):
        """设置列表项的背景颜色（带透明度）"""
        color_code = Config.get_color_code(color_name)
        color = QColor(color_code)
        color.setAlpha(80)  # 设置透明度
        item.setBackground(QBrush(color))

    def apply_style_to_selected(self):
        """应用样式到选中的时刻"""
        color_name = self.color_combo.currentText()
        ls_idx = self.linestyle_combo.currentIndex()
        linestyle = ['-', '--', '-.', ':'][ls_idx]
        linewidth = self.linewidth_spin.value()

        for item in self.time_list.selectedItems():
            idx = item.data(Qt.UserRole)
            self.selected_times[idx]['color'] = color_name
            self.selected_times[idx]['linestyle'] = linestyle
            self.selected_times[idx]['linewidth'] = linewidth
            # 设置列表项的背景颜色
            self._set_item_color(item, color_name)

        self.main_window.status_label.setText(f"已应用样式到 {len(self.time_list.selectedItems())} 个时刻")
        # 自动更新画布
        self.plot_spatial()

    def plot_spatial(self):
        """绘制空间曲线"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('load_file_first'))
            return

        # 获取选中的时刻
        selected_items = self.time_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('select_at_least_one_moment'))
            return

        # 获取变量
        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            return
        var = self.var_combo.itemData(var_idx)

        # 获取X轴单位
        xunit = self.xunit_combo.currentText()
        coord_system = self.coord_combo.currentData() or 'XC'

        # 收集数据
        x_list = []
        data_list = []
        colors = []
        linestyles = []
        linewidths = []
        labels = []

        times_ns = parser.get_time_array(unit='ns')

        for item in selected_items:
            time_idx = item.data(Qt.UserRole)
            style = self.selected_times.get(time_idx, {})

            # 检查是否被删除
            if not style.get('enabled', True):
                continue

            result = parser.get_spatial_data(var, time_idx, coord_system=coord_system)
            if result:
                grid, values = result
                # X 轴单位换算：
                # - 欧拉 XC/X：parser 返回 cm，xunit='um' 时 ×1e4
                # - 拉氏 CMC/CMI：parser 返回原值（g/cm²），xunit='g·um/cm³' 时 ×1e4
                if xunit == 'um':
                    grid = grid * 1e4
                elif xunit == 'g·um/cm³':
                    grid = grid * 1e4
                # Y 轴变量按其当前单位换算（P→压强 / T→温度 / V→速度 / XC,X→位置 等）
                yunit = Config.get_current_unit_for_var(var)
                if yunit:
                    values = values * Config.get_var_factor(var, yunit)
                x_list.append(grid)
                data_list.append(values)

                # 获取颜色代码
                color_name = style.get('color', 'black')
                color_code = Config.get_color_code(color_name)
                colors.append(color_code)
                linestyles.append(style.get('linestyle', '-'))
                linewidths.append(style.get('linewidth', 1.5))
                labels.append(f"t={times_ns[time_idx]:.3f}ns")

        if not data_list:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('cannot_get_data_deleted'))
            return

        # 获取坐标范围
        xlim = None if self.xlim_auto_cb.isChecked() else (self.xlim_min.value(), self.xlim_max.value())
        ylim = None if self.ylim_auto_cb.isChecked() else (self.ylim_min.value(), self.ylim_max.value())

        # 绘图（每条曲线使用各自的x坐标）
        # Y 轴标签 = "var 描述 (unit)"，与 heatmap 一致
        yunit = Config.get_current_unit_for_var(var)
        ylabel = Config.format_var_label(var, yunit) if yunit else Config.format_var_label(var)
        show_legend = self.show_legend_cb.isChecked()
        # X 轴标签 = "coord_system 描述"，plot_spatial_curves 会自动拼 "(xunit)"
        coord_label_base = f'{coord_system} {Config.VAR_DESCRIPTION.get(coord_system, "")}'.strip()
        self.plot_engine.plot_spatial_curves(
            x=x_list,
            data_list=data_list,
            labels=labels,
            colors=colors,
            linestyles=linestyles,
            linewidths=linewidths,
            xlabel=coord_label_base,
            ylabel=ylabel,
            title='',
            show_legend=show_legend,
            xunit=xunit,
            log_x=self.log_x_cb.isChecked(),
            log_y=self.log_y_cb.isChecked(),
            xlim=xlim,
            ylim=ylim
        )

        self.main_window.status_label.setText(f"已绘制 {len(data_list)} 条曲线")

        # 代码录制钩子
        from utils.code_recorder import CodeRecorder
        recorder = CodeRecorder()
        if recorder.is_recording:
            # 收集实际使用的样式
            time_styles = {}
            for item in selected_items:
                time_idx = item.data(Qt.UserRole)
                style = self.selected_times.get(time_idx, {})
                if style.get('enabled', True):
                    time_styles[str(time_idx)] = {
                        'color': style.get('color', 'black'),
                        'linestyle': style.get('linestyle', '-'),
                        'linewidth': style.get('linewidth', 1.5)
                    }
            recorder.record_spatial_plot(
                var=var,
                time_indices=[item.data(Qt.UserRole) for item in selected_items
                              if self.selected_times.get(item.data(Qt.UserRole), {}).get('enabled', True)],
                styles=time_styles,
                xunit=xunit,
                yunit=yunit,
                coord_system=coord_system,
                log_x=self.log_x_cb.isChecked(),
                log_y=self.log_y_cb.isChecked(),
                xlim=xlim,
                ylim=ylim,
                show_legend=show_legend
            )
            if self.main_window.code_recorder_dialog is not None:
                self.main_window.code_recorder_dialog.update_count()

    def clear_plot(self):
        """清空画布"""
        if self.plot_engine:
            self.plot_engine.clear()

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
        """导出绘图数据为CSV"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, "警告", "请先加载数据文件")
            return

        selected_items = self.time_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_moments_to_export'))
            return

        var_idx = self.var_combo.currentIndex()
        if var_idx < 0:
            return
        var = self.var_combo.itemData(var_idx)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出数据", f"{var}_spatial.csv", "CSV文件 (*.csv)"
        )

        if filepath:
            try:
                import csv
                xunit = self.xunit_combo.currentText()
                coord_system = self.coord_combo.currentData() or 'XC'
                times_ns = parser.get_time_array(unit='ns')
                # Y 轴变量按其当前单位换算（通用）
                yunit = Config.get_current_unit_for_var(var)
                y_factor = Config.get_var_factor(var, yunit) if yunit else 1.0
                y_unit_suffix = f' ({yunit})' if yunit else ''

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)

                    # 写入表头
                    grid_pos = parser.get_grid_positions(unit=xunit, coord_system=coord_system)
                    coord_label_base = f'{coord_system} {Config.VAR_DESCRIPTION.get(coord_system, "")}'.strip()
                    header = [f'{coord_label_base} ({xunit})']
                    for item in selected_items:
                        time_idx = item.data(Qt.UserRole)
                        if self.selected_times[time_idx].get('enabled', True):
                            t_str = f't={times_ns[time_idx]:.4f}ns'
                            if y_unit_suffix:
                                t_str += f' {var}{y_unit_suffix}'
                            header.append(t_str)
                    writer.writerow(header)

                    # 写入数据
                    for i, pos in enumerate(grid_pos):
                        row = [f'{pos:.6e}']
                        for item in selected_items:
                            time_idx = item.data(Qt.UserRole)
                            if self.selected_times[time_idx].get('enabled', True):
                                result = parser.get_spatial_data(var, time_idx, coord_system=coord_system)
                                if result and i < len(result[1]):
                                    val = result[1][i] * y_factor
                                    row.append(f'{val:.6e}')
                                else:
                                    row.append('')
                        writer.writerow(row)

                self.main_window.status_label.setText(f"数据已导出: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
