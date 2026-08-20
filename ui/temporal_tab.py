"""TemporalTab - 时间图标签页
绘制变量随时间的变化曲线
支持全局时间变量和特定网格的时间演化
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox, QFileDialog, QTabWidget,
    QRadioButton, QButtonGroup, QFrame, QScrollArea, QMenu, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import numpy as np

from core.plot_engine import PlotEngine
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class TemporalTab(QWidget):
    """时间图标签页"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.main_window = parent
        self.logger = Logger.get_logger('TemporalTab')

        self.plot_engine = None
        self.selected_cells = {}  # {cell_idx: {'color': str, 'linestyle': str, 'enabled': bool}}

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

        # === 绘图模式选择 ===
        mode_group = QGroupBox(LanguageManager.get_text('plot_mode'))
        mode_layout = QVBoxLayout(mode_group)

        self.mode_button_group = QButtonGroup(self)

        self.global_mode_rb = QRadioButton(LanguageManager.get_text('global_var'))
        self.global_mode_rb.setChecked(True)
        self.mode_button_group.addButton(self.global_mode_rb, 0)
        mode_layout.addWidget(self.global_mode_rb)

        self.cell_mode_rb = QRadioButton(LanguageManager.get_text('cell_time_evolution'))
        self.mode_button_group.addButton(self.cell_mode_rb, 1)
        mode_layout.addWidget(self.cell_mode_rb)

        self.mode_button_group.buttonClicked.connect(self.on_mode_changed)

        layout.addWidget(mode_group)

        # === 全局变量模式 ===
        self.global_widget = QWidget()
        global_layout = QVBoxLayout(self.global_widget)
        global_layout.setContentsMargins(0, 0, 0, 0)

        # 变量选择
        var_group = QGroupBox(LanguageManager.get_text('global_var'))
        var_layout = QVBoxLayout(var_group)
        self.global_var_combo = QComboBox()
        var_layout.addWidget(self.global_var_combo)
        global_layout.addWidget(var_group)

        layout.addWidget(self.global_widget)

        # === 网格模式 ===
        self.cell_widget = QWidget()
        cell_layout = QVBoxLayout(self.cell_widget)
        cell_layout.setContentsMargins(0, 0, 0, 0)

        # 变量选择
        cell_var_group = QGroupBox(LanguageManager.get_text('spatial_var'))
        cell_var_layout = QVBoxLayout(cell_var_group)
        self.cell_var_combo = QComboBox()
        self.cell_var_combo.currentIndexChanged.connect(self._on_cell_var_changed)
        cell_var_layout.addWidget(self.cell_var_combo)

        # Y 轴单位（按变量类型自适应）
        cell_yunit_layout = QHBoxLayout()
        cell_yunit_layout.addWidget(QLabel("Y unit:"))
        self.cell_yunit_combo = QComboBox()
        self.cell_yunit_combo.currentIndexChanged.connect(self._on_cell_yunit_changed)
        cell_yunit_layout.addWidget(self.cell_yunit_combo)
        cell_var_layout.addLayout(cell_yunit_layout)
        cell_layout.addWidget(cell_var_group)

        # 网格选择
        cell_select_group = QGroupBox(LanguageManager.get_text('select_cell'))
        cell_select_layout = QVBoxLayout(cell_select_group)

        # 网格列表
        self.cell_list = QListWidget()
        self.cell_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.cell_list.setMinimumHeight(100)
        self.cell_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cell_list.customContextMenuRequested.connect(self.show_cell_context_menu)
        cell_select_layout.addWidget(self.cell_list)

        # 网格选择按钮
        cell_btn_layout = QHBoxLayout()
        self.cell_select_all_btn = QPushButton(LanguageManager.get_text('select_all'))
        self.cell_select_all_btn.clicked.connect(self.select_all_cells)
        cell_btn_layout.addWidget(self.cell_select_all_btn)

        self.cell_invert_btn = QPushButton(LanguageManager.get_text('select_inverse'))
        self.cell_invert_btn.clicked.connect(self.invert_cell_selection)
        cell_btn_layout.addWidget(self.cell_invert_btn)

        self.cell_clear_btn = QPushButton(LanguageManager.get_text('clear'))
        self.cell_clear_btn.clicked.connect(self.clear_cell_selection)
        cell_btn_layout.addWidget(self.cell_clear_btn)

        cell_select_layout.addLayout(cell_btn_layout)

        # 删除/取消删除按钮
        del_btn_layout = QHBoxLayout()
        self.cell_delete_btn = QPushButton(LanguageManager.get_text('remove_selected'))
        self.cell_delete_btn.clicked.connect(self.delete_selected_cells)
        del_btn_layout.addWidget(self.cell_delete_btn)

        self.cell_undelete_btn = QPushButton(LanguageManager.get_text('cancel_delete'))
        self.cell_undelete_btn.clicked.connect(self.undelete_selected_cells)
        del_btn_layout.addWidget(self.cell_undelete_btn)

        cell_select_layout.addLayout(del_btn_layout)

        # 按 MID 分配颜色（一键给不同材料的网格赋予不同颜色）
        mid_btn_layout = QHBoxLayout()
        self.assign_mid_color_btn = QPushButton(LanguageManager.get_text('assign_mid_color'))
        self.assign_mid_color_btn.clicked.connect(self.assign_colors_by_mid)
        mid_btn_layout.addWidget(self.assign_mid_color_btn)
        cell_select_layout.addLayout(mid_btn_layout)

        cell_layout.addWidget(cell_select_group)

        self.cell_widget.setVisible(False)
        layout.addWidget(self.cell_widget)

        # === 样式设置 ===
        style_group = QGroupBox(LanguageManager.get_text('style_settings'))
        style_layout = QVBoxLayout(style_group)

        # 第一行：时间单位、颜色、线型、显示图例
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel(LanguageManager.get_text('unit') + ":"))
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.addItems(["ns", "s"])
        self.time_unit_combo.setCurrentText("ns")
        row1_layout.addWidget(self.time_unit_combo)
        row1_layout.addSpacing(10)
        row1_layout.addWidget(QLabel(LanguageManager.get_text('color') + ":"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(Config.COLORS)
        self.color_combo.setCurrentText("black")
        row1_layout.addWidget(self.color_combo)
        row1_layout.addSpacing(10)
        row1_layout.addWidget(QLabel(LanguageManager.get_text('line_style') + ":"))
        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':'])
        self.linestyle_combo.setToolTip("Solid / Dashed / Dash-dot / Dotted")
        row1_layout.addWidget(self.linestyle_combo)
        row1_layout.addSpacing(10)
        self.show_legend_cb = QCheckBox(LanguageManager.get_text('show_legend'))
        self.show_legend_cb.setChecked(False)  # 默认关闭
        row1_layout.addWidget(self.show_legend_cb)
        row1_layout.addStretch()
        style_layout.addLayout(row1_layout)

        # 第二行：应用按钮
        row2_layout = QHBoxLayout()
        self.apply_style_btn = QPushButton(LanguageManager.get_text('apply_styles'))
        self.apply_style_btn.clicked.connect(self.apply_style_to_selected)
        row2_layout.addWidget(self.apply_style_btn)
        row2_layout.addStretch()
        style_layout.addLayout(row2_layout)

        layout.addWidget(style_group)

        # === 坐标轴设置 ===
        axis_group = QGroupBox(LanguageManager.get_text('axis_settings'))
        axis_layout = QVBoxLayout(axis_group)

        # 对数坐标
        log_layout = QHBoxLayout()
        self.log_x_cb = QCheckBox(LanguageManager.get_text('log_x_axis'))
        log_layout.addWidget(self.log_x_cb)
        self.log_y_cb = QCheckBox(LanguageManager.get_text('log_y_axis'))
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
        self.plot_btn.clicked.connect(self.plot_temporal)
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

        self.plot_engine = PlotEngine(parent=panel)
        layout.addWidget(self.plot_engine.canvas)

        return panel

    def on_mode_changed(self):
        """切换绘图模式"""
        is_global = self.global_mode_rb.isChecked()
        self.global_widget.setVisible(is_global)
        self.cell_widget.setVisible(not is_global)

    def update_data(self):
        """更新数据"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            self.clear_ui()
            return

        # 更新全局时间变量列表
        self.global_var_combo.clear()
        time_vars = parser.get_available_time_vars()
        for var in time_vars:
            display_name = parser.get_variable_display_name(var)
            self.global_var_combo.addItem(f"{var} - {display_name}", var)

        # 更新空间变量列表（用于网格模式）
        self.cell_var_combo.blockSignals(True)
        self.cell_var_combo.clear()
        spatial_vars = parser.get_available_spatial_vars()
        for var in spatial_vars:
            display_name = parser.get_variable_display_name(var)
            self.cell_var_combo.addItem(f"{var} - {display_name}", var)
        self.cell_var_combo.blockSignals(False)
        if self.cell_var_combo.count() > 0:
            self._on_cell_var_changed(self.cell_var_combo.currentIndex())

        # 更新网格列表
        self.cell_list.clear()
        self.selected_cells.clear()

        n_cells = parser.get_n_cells()
        for i in range(n_cells):
            item = QListWidgetItem(f"Cell #{i}")
            item.setData(Qt.UserRole, i)
            self.cell_list.addItem(item)
            self.selected_cells[i] = {
                'color': 'black',
                'linestyle': '-',
                'linewidth': 1.5,
                'enabled': True
            }

        self.logger.info(f"已更新时间图数据: {len(time_vars)}个全局变量, {n_cells}个网格")

    def clear_ui(self):
        """清空UI"""
        self.global_var_combo.clear()
        self.cell_var_combo.clear()
        self.cell_list.clear()
        self.selected_cells.clear()
        if self.plot_engine:
            self.plot_engine.clear()

    def _on_cell_var_changed(self, idx: int):
        """cell 模式 Y 轴变量切换：同步 yunit_combo"""
        if idx < 0:
            return
        var = self.cell_var_combo.itemData(idx)
        units = Config.get_var_units(var)
        self.cell_yunit_combo.blockSignals(True)
        self.cell_yunit_combo.clear()
        if units:
            for u in units:
                self.cell_yunit_combo.addItem(u)
            cur = Config.get_current_unit_for_var(var)
            if cur in units:
                self.cell_yunit_combo.setCurrentText(cur)
            else:
                self.cell_yunit_combo.setCurrentText(units[0])
            self.cell_yunit_combo.setEnabled(True)
        else:
            self.cell_yunit_combo.setEnabled(False)
        self.cell_yunit_combo.blockSignals(False)

    def _on_cell_yunit_changed(self):
        """cell 模式 Y 轴单位切换：记到 Config（per-category）"""
        var_idx = self.cell_var_combo.currentIndex()
        if var_idx < 0:
            return
        var = self.cell_var_combo.itemData(var_idx)
        unit = self.cell_yunit_combo.currentText()
        if not unit:
            return
        Config.set_current_unit_for_var(var, unit)
        Config.save_var_units()

    def select_all_cells(self):
        """全选网格"""
        self.cell_list.selectAll()

    def invert_cell_selection(self):
        """反选网格"""
        for i in range(self.cell_list.count()):
            item = self.cell_list.item(i)
            item.setSelected(not item.isSelected())

    def clear_cell_selection(self):
        """清除网格选择"""
        self.cell_list.clearSelection()

    def delete_selected_cells(self):
        """删除选中的网格（不绘制）"""
        for item in self.cell_list.selectedItems():
            idx = item.data(Qt.UserRole)
            self.selected_cells[idx]['enabled'] = False
            item.setForeground(QBrush(Qt.gray))
            text = item.text()
            if "(deleted)" not in text:
                item.setText(text + " (deleted)")

        self.main_window.status_label.setText(f"{LanguageManager.get_text('marked_cells_not_plotting')} {len(self.cell_list.selectedItems())} {LanguageManager.get_text('cells_not_plotting')}")
        # 自动更新画布
        self.plot_temporal()

    def undelete_selected_cells(self):
        """取消删除选中的网格"""
        count = 0
        for item in self.cell_list.selectedItems():
            idx = item.data(Qt.UserRole)
            if not self.selected_cells[idx].get('enabled', True):
                self.selected_cells[idx]['enabled'] = True
                item.setForeground(QBrush(Qt.black))
                text = item.text().replace(" (deleted)", "")
                item.setText(text)
                count += 1

        if count > 0:
            self.main_window.status_label.setText(f"{LanguageManager.get_text('restored_cells')} {count} {LanguageManager.get_text('cells')}")
            # 自动更新画布
            self.plot_temporal()

    def show_cell_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()

        restore_action = QAction(LanguageManager.get_text('restore_selected_plot'), self)
        restore_action.triggered.connect(self.undelete_selected_cells)
        menu.addAction(restore_action)

        menu.exec_(self.cell_list.mapToGlobal(position))

    def _set_item_color(self, item, color_name):
        """设置列表项的背景颜色（带透明度）"""
        color_code = Config.get_color_code(color_name)
        color = QColor(color_code)
        color.setAlpha(80)
        item.setBackground(QBrush(color))

    def apply_style_to_selected(self):
        """应用样式"""
        color_name = self.color_combo.currentText()
        ls_idx = self.linestyle_combo.currentIndex()
        linestyle = ['-', '--', '-.', ':'][ls_idx]

        if self.cell_mode_rb.isChecked():
            for item in self.cell_list.selectedItems():
                idx = item.data(Qt.UserRole)
                self.selected_cells[idx]['color'] = color_name
                self.selected_cells[idx]['linestyle'] = linestyle
                # 设置列表项的背景颜色
                self._set_item_color(item, color_name)
            self.main_window.status_label.setText(f"已应用样式到 {len(self.cell_list.selectedItems())} 个网格")
            # 自动更新画布
            self.plot_temporal()
        else:
            self.main_window.status_label.setText(LanguageManager.get_text('global_mode_style_note'))

    def assign_colors_by_mid(self):
        """按材料 MID 给所有网格分配颜色（同一材料同色）。"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                LanguageManager.get_text('load_file_first'))
            return

        mid_array = parser.get_material_ids()
        if mid_array is None:
            QMessageBox.information(self, LanguageManager.get_text('info'),
                                    LanguageManager.get_text('no_mid_data'))
            return

        material_map = parser.get_material_map()
        unique_mids = sorted(set(int(m) for m in mid_array))

        for cell_idx in range(len(mid_array)):
            mid_val = int(mid_array[cell_idx])
            color_name = Config.COLORS[unique_mids.index(mid_val) % len(Config.COLORS)]
            self.selected_cells[cell_idx]['color'] = color_name
            item = self.cell_list.item(cell_idx)
            if item:
                self._set_item_color(item, color_name)

        # 状态栏汇总每种材料的 cell 数
        parts = []
        for mid_val in unique_mids:
            name = material_map.get(mid_val, f'MID={mid_val}')
            count = int(np.sum(mid_array == mid_val))
            parts.append(f"{name}({mid_val}): {count}")
        self.main_window.status_label.setText(
            f"{LanguageManager.get_text('mid_color_assigned')}: {'; '.join(parts)}")

        if self.cell_list.selectedItems():
            self.plot_temporal()

    def plot_temporal(self):
        """绘制时间曲线"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('load_file_first'))
            return

        time_unit = self.time_unit_combo.currentText()
        xlim = None if self.xlim_auto_cb.isChecked() else (self.xlim_min.value(), self.xlim_max.value())
        ylim = None if self.ylim_auto_cb.isChecked() else (self.ylim_min.value(), self.ylim_max.value())

        if self.global_mode_rb.isChecked():
            self._plot_global_temporal(parser, time_unit, xlim, ylim)
        else:
            self._plot_cell_temporal(parser, time_unit, xlim, ylim)

    def _plot_global_temporal(self, parser, time_unit, xlim, ylim):
        """绘制全局时间变量"""
        var_idx = self.global_var_combo.currentIndex()
        if var_idx < 0:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_variable'))
            return

        var = self.global_var_combo.itemData(var_idx)
        result = parser.get_time_series_global(var)

        if not result:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('cannot_get_data'))
            return

        times, values = result
        if time_unit == 'ns':
            times = times * 1e9

        # 压强变量按当前单位换算
        if Config.is_pressure_var(var):
            values = values * Config.get_pressure_factor()
            display_name = Config.format_pressure_label(var)
            yunit = Config.get_pressure_unit()
        else:
            display_name = parser.get_variable_display_name(var)
            yunit = Config.get_current_unit_for_var(var) or ''
        color_name = self.color_combo.currentText()
        color_code = Config.get_color_code(color_name)
        ls_idx = self.linestyle_combo.currentIndex()
        linestyle = ['-', '--', '-.', ':'][ls_idx]

        show_legend = self.show_legend_cb.isChecked()
        self.plot_engine.plot_time_series(
            times=times,
            data_list=[values],
            labels=[var],
            colors=[color_code],
            linestyles=[linestyle],
            ylabel=display_name,
            title='',
            show_legend=show_legend,
            time_unit=time_unit,
            log_x=self.log_x_cb.isChecked(),
            log_y=self.log_y_cb.isChecked(),
            xlim=xlim,
            ylim=ylim
        )

        self.main_window.status_label.setText(f"{LanguageManager.get_text('drawn_curve')} {var} {LanguageManager.get_text('time_evolution_curve')}")

        # 代码录制钩子
        from utils.code_recorder import CodeRecorder
        recorder = CodeRecorder()
        if recorder.is_recording:
            from utils.config import Config as Cfg
            recorder.record_global_temporal(
                var=var,
                time_unit=time_unit,
                color=Cfg.get_color_code(color_name),
                linestyle=linestyle,
                yunit=yunit,
                log_x=self.log_x_cb.isChecked(),
                log_y=self.log_y_cb.isChecked(),
                xlim=xlim,
                ylim=ylim,
                show_legend=show_legend
            )
            if self.main_window.code_recorder_dialog is not None:
                self.main_window.code_recorder_dialog.update_count()

    def _plot_cell_temporal(self, parser, time_unit, xlim, ylim):
        """绘制特定网格的时间演化"""
        selected_items = self.cell_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('select_at_least_one_cell'))
            return

        var_idx = self.cell_var_combo.currentIndex()
        if var_idx < 0:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('select_variable'))
            return

        var = self.cell_var_combo.itemData(var_idx)

        mid_array = parser.get_material_ids()
        material_map = parser.get_material_map()

        data_list = []
        colors = []
        linestyles = []
        labels = []

        for item in selected_items:
            cell_idx = item.data(Qt.UserRole)
            style = self.selected_cells.get(cell_idx, {})

            if not style.get('enabled', True):
                continue

            result = parser.get_time_series_at_cell(var, cell_idx)

            if result:
                times, values = result
                if time_unit == 'ns':
                    times = times * 1e9

                # Y 轴变量按其当前单位换算（通用）
                yunit = Config.get_current_unit_for_var(var)
                if yunit:
                    values = values * Config.get_var_factor(var, yunit)

                data_list.append(values)
                color_name = style.get('color', 'black')
                color_code = Config.get_color_code(color_name)
                colors.append(color_code)
                linestyles.append(style.get('linestyle', '-'))
                if mid_array is not None and cell_idx < len(mid_array):
                    mid_val = int(mid_array[cell_idx])
                    mat_name = material_map.get(mid_val, f'MID={mid_val}')
                    labels.append(f"Cell #{cell_idx} [{mat_name}]")
                else:
                    labels.append(f"Cell #{cell_idx}")

        if not data_list:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('no_data_to_plot'))
            return

        # 使用正确的时间单位获取时间轴
        times = parser.get_time_array(unit=time_unit)

        # Y 轴标签：var + 描述 + (unit)
        yunit = Config.get_current_unit_for_var(var)
        ylabel = Config.format_var_label(var, yunit) if yunit else Config.format_var_label(var)
        show_legend = self.show_legend_cb.isChecked()
        self.plot_engine.plot_time_series(
            times=times,
            data_list=data_list,
            labels=labels,
            colors=colors,
            linestyles=linestyles,
            ylabel=ylabel,
            title='',
            show_legend=show_legend,
            time_unit=time_unit,
            log_x=self.log_x_cb.isChecked(),
            log_y=self.log_y_cb.isChecked(),
            xlim=xlim,
            ylim=ylim
        )

        self.main_window.status_label.setText(f"{LanguageManager.get_text('drawn_curves')} {len(data_list)} {LanguageManager.get_text('curves')}")

        # 代码录制钩子
        from utils.code_recorder import CodeRecorder
        recorder = CodeRecorder()
        if recorder.is_recording:
            cell_styles = {}
            for item in selected_items:
                cell_idx = item.data(Qt.UserRole)
                s = self.selected_cells.get(cell_idx, {})
                if s.get('enabled', True):
                    cell_styles[str(cell_idx)] = {
                        'color': s.get('color', 'black'),
                        'linestyle': s.get('linestyle', '-'),
                        'linewidth': s.get('linewidth', 1.5)
                    }
            enabled_cells = [item.data(Qt.UserRole) for item in selected_items
                             if self.selected_cells.get(item.data(Qt.UserRole), {}).get('enabled', True)]
            recorder.record_cell_temporal(
                var=var,
                cell_indices=enabled_cells,
                styles=cell_styles,
                time_unit=time_unit,
                yunit=yunit,
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
            self, LanguageManager.get_text('save_image_title'), "",
            f"{LanguageManager.get_text('png_files')};;{LanguageManager.get_text('pdf_files')};;{LanguageManager.get_text('all_files')}"
        )
        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            self.plot_engine.save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            self.main_window.status_label.setText(f"{LanguageManager.get_text('image_saved')} {filepath}")

    def export_data(self):
        """导出绘图数据为CSV"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('load_file_first'))
            return

        time_unit = self.time_unit_combo.currentText()

        if self.global_mode_rb.isChecked():
            # 导出全局时间变量
            var_idx = self.global_var_combo.currentIndex()
            if var_idx < 0:
                return
            var = self.global_var_combo.itemData(var_idx)
            result = parser.get_time_series_global(var)

            if not result:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('cannot_get_data'))
                return

            times, values = result
            if time_unit == 'ns':
                times = times * 1e9

            # 压强变量按当前单位换算
            is_p = Config.is_pressure_var(var)
            if is_p:
                values = values * Config.get_pressure_factor()
                var_col = Config.format_pressure_label(var)
            else:
                var_col = var

            filepath, _ = QFileDialog.getSaveFileName(
                self, LanguageManager.get_text('export_data_title'), f"{var}_temporal.csv", LanguageManager.get_text('csv_files')
            )

            if filepath:
                try:
                    import csv
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([f'Time ({time_unit})', var_col])
                        for t, v in zip(times, values):
                            writer.writerow([f'{t:.6e}', f'{v:.6e}'])
                    self.main_window.status_label.setText(f"{LanguageManager.get_text('data_exported')} {filepath}")
                except Exception as e:
                    QMessageBox.critical(self, LanguageManager.get_text('error'), f"{LanguageManager.get_text('export_failed_error')} {e}")
        else:
            # 导出网格时间演化
            selected_items = self.cell_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_cells_to_export'))
                return

            var_idx = self.cell_var_combo.currentIndex()
            if var_idx < 0:
                return
            var = self.cell_var_combo.itemData(var_idx)

            # Y 轴变量按其当前单位换算（通用）
            yunit = Config.get_current_unit_for_var(var)
            y_factor = Config.get_var_factor(var, yunit) if yunit else 1.0
            y_unit_suffix = f' ({yunit})' if yunit else ''

            filepath, _ = QFileDialog.getSaveFileName(
                self, LanguageManager.get_text('export_data_title'), f"{var}_cells.csv", LanguageManager.get_text('csv_files')
            )

            if filepath:
                try:
                    import csv
                    times = parser.get_time_array(unit=time_unit)

                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        header = [f'Time ({time_unit})']
                        for item in selected_items:
                            cell_idx = item.data(Qt.UserRole)
                            if self.selected_cells[cell_idx].get('enabled', True):
                                col_name = f'Cell #{cell_idx}{y_unit_suffix}'
                                header.append(col_name)
                        writer.writerow(header)

                        for i, t in enumerate(times):
                            row = [f'{t:.6e}']
                            for item in selected_items:
                                cell_idx = item.data(Qt.UserRole)
                                if self.selected_cells[cell_idx].get('enabled', True):
                                    result = parser.get_time_series_at_cell(var, cell_idx)
                                    if result and i < len(result[1]):
                                        val = result[1][i] * y_factor
                                        row.append(f'{val:.6e}')
                                    else:
                                        row.append('')
                            writer.writerow(row)

                    self.main_window.status_label.setText(f"{LanguageManager.get_text('data_exported')} {filepath}")
                except Exception as e:
                    QMessageBox.critical(self, LanguageManager.get_text('error'), f"{LanguageManager.get_text('export_failed_error')} {e}")
