"""ExtremeFinderDialog - 极值寻找工具
从热图中提取指定坐标线上的分布，并寻找极值点
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QMessageBox, QFileDialog, QWidget, QComboBox,
    QLineEdit, QDoubleSpinBox, QCheckBox, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QTextEdit, QScrollArea, QTabWidget,
    QInputDialog, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
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


class ProfileConfig:
    """Profile配置类"""
    def __init__(self, coord_type='position', coord_value=0.0, xunit='', ranges=None):
        self.coord_type = coord_type  # 'position' 或 'time'
        self.coord_value = coord_value
        self.xunit = xunit
        self.ranges = ranges if ranges else []  # [(min, max), ...]

    def to_dict(self):
        return {
            'coord_type': self.coord_type,
            'coord_value': self.coord_value,
            'xunit': self.xunit,
            'ranges': self.ranges
        }

    @staticmethod
    def from_dict(data):
        return ProfileConfig(
            coord_type=data.get('coord_type', 'position'),
            coord_value=data.get('coord_value', 0.0),
            xunit=data.get('xunit', ''),
            ranges=data.get('ranges', [])
        )


class ExtremeFinderDialog(QDialog):
    """极值寻找工具对话框"""

    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.MULTI1D可视化工具', 'extreme_finder_config.json')

    def __init__(self, data_manager, heatmap_tab, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.heatmap_tab = heatmap_tab
        self.parent = parent
        self.logger = Logger.get_logger('ExtremeFinderDialog')

        # 存储提取的数据
        self.extracted_profiles = []
        # 存储检测到的极值
        self.detected_extremes = []

        self.setWindowTitle(LanguageManager.get_text('extreme_finder_title'))
        self.setMinimumSize(1200, 800)
        # Enable minimize button, taskbar presence, and start maximized
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        self.setup_ui()
        self.load_default_config()
        self.showMaximized()

    def setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        # 右侧绘图区域（带标签页）
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)

        splitter.setSizes([400, 1000])
        main_layout.addWidget(splitter)

    def create_control_panel(self):
        """创建控制面板"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # === 使用说明 ===
        help_group = QGroupBox("Help")
        help_layout = QVBoxLayout(help_group)
        help_label = QLabel(LanguageManager.get_text('extreme_help'))
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addWidget(help_group)

        # === 添加Profile ===
        add_group = QGroupBox("Add Profile")
        add_layout = QVBoxLayout(add_group)

        # 坐标类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(LanguageManager.get_text('extract_type') + ":"))
        self.coord_type_combo = QComboBox()
        self.coord_type_combo.addItems([LanguageManager.get_text('fixed_position'),
                                        LanguageManager.get_text('fixed_time')])
        type_layout.addWidget(self.coord_type_combo)
        add_layout.addLayout(type_layout)

        # 坐标值
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel(LanguageManager.get_text('coord_value') + ":"))
        self.coord_value_edit = QLineEdit()
        self.coord_value_edit.setPlaceholderText(LanguageManager.get_text('coord_value_placeholder'))
        value_layout.addWidget(self.coord_value_edit)
        add_layout.addLayout(value_layout)

        # 添加按钮
        self.add_profile_btn = QPushButton(LanguageManager.get_text('add_profile'))
        self.add_profile_btn.clicked.connect(self.add_profiles)
        self.add_profile_btn.setMinimumHeight(30)
        add_layout.addWidget(self.add_profile_btn)

        layout.addWidget(add_group)

        # === Profile列表与范围设置 ===
        profile_group = QGroupBox(LanguageManager.get_text('profile_list'))
        profile_layout = QVBoxLayout(profile_group)

        # 使用表格显示
        self.profile_table = QTableWidget()
        self.profile_table.setColumnCount(3)
        self.profile_table.setHorizontalHeaderLabels([LanguageManager.get_text('profile_col'),
                                                      LanguageManager.get_text('range_col'),
                                                      LanguageManager.get_text('action_col')])
        self.profile_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.profile_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profile_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.profile_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profile_table.itemChanged.connect(self.on_profile_item_changed)
        self.profile_table.setMinimumHeight(150)
        self.profile_table.setMaximumHeight(200)
        profile_layout.addWidget(self.profile_table)

        # 批量操作按钮
        batch_btn_layout = QHBoxLayout()
        self.remove_profile_btn = QPushButton(LanguageManager.get_text('remove_selected'))
        self.remove_profile_btn.clicked.connect(self.remove_selected_profile)
        batch_btn_layout.addWidget(self.remove_profile_btn)

        self.clear_profiles_btn = QPushButton(LanguageManager.get_text('clear_all'))
        self.clear_profiles_btn.clicked.connect(self.clear_all_profiles)
        batch_btn_layout.addWidget(self.clear_profiles_btn)
        profile_layout.addLayout(batch_btn_layout)

        layout.addWidget(profile_group)

        # === 极值检测选项 ===
        extreme_group = QGroupBox(LanguageManager.get_text('extreme_options'))
        extreme_layout = QVBoxLayout(extreme_group)

        # 第一行：寻找极大值 + 寻找极小值
        row1_layout = QHBoxLayout()
        self.find_max_cb = QCheckBox(LanguageManager.get_text('find_max'))
        self.find_max_cb.setChecked(True)
        row1_layout.addWidget(self.find_max_cb)

        self.find_min_cb = QCheckBox(LanguageManager.get_text('find_min'))
        self.find_min_cb.setChecked(False)
        row1_layout.addWidget(self.find_min_cb)
        extreme_layout.addLayout(row1_layout)

        # 第二行：显示导数曲线 + 显示图例
        row2_layout = QHBoxLayout()
        self.show_derivative_cb = QCheckBox(LanguageManager.get_text('show_derivative'))
        self.show_derivative_cb.setChecked(True)
        row2_layout.addWidget(self.show_derivative_cb)

        self.show_legend_cb = QCheckBox(LanguageManager.get_text('show_legend'))
        self.show_legend_cb.setChecked(True)
        row2_layout.addWidget(self.show_legend_cb)
        extreme_layout.addLayout(row2_layout)

        layout.addWidget(extreme_group)

        # === 配置保存 ===
        config_group = QGroupBox("默认配置")
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

        # === 极值信息显示 ===
        info_group = QGroupBox(LanguageManager.get_text('extreme_info'))
        info_layout = QVBoxLayout(info_group)
        self.extreme_info_text = QTextEdit()
        self.extreme_info_text.setReadOnly(True)
        self.extreme_info_text.setMinimumHeight(80)
        self.extreme_info_text.setMaximumHeight(120)
        self.extreme_info_text.setPlaceholderText("Extreme information will be displayed here after extraction...")
        info_layout.addWidget(self.extreme_info_text)
        layout.addWidget(info_group)

        # === 操作按钮 ===
        btn_layout = QHBoxLayout()
        self.extract_btn = QPushButton(LanguageManager.get_text('extract_and_find'))
        self.extract_btn.clicked.connect(self.extract_profiles)
        self.extract_btn.setMinimumHeight(35)
        btn_layout.addWidget(self.extract_btn)
        layout.addLayout(btn_layout)

        # Save image buttons
        save_layout = QHBoxLayout()
        self.save_current_btn = QPushButton(LanguageManager.get_text('save_image'))
        self.save_current_btn.clicked.connect(self.save_figure)
        self.save_current_btn.setMinimumHeight(28)
        save_layout.addWidget(self.save_current_btn)

        self.save_all_btn = QPushButton(LanguageManager.get_text('save_all_images'))
        self.save_all_btn.clicked.connect(self.save_all_figures)
        self.save_all_btn.setMinimumHeight(28)
        save_layout.addWidget(self.save_all_btn)
        layout.addLayout(save_layout)

        btn_layout2 = QHBoxLayout()
        self.export_btn = QPushButton(LanguageManager.get_text('export_data'))
        self.export_btn.clicked.connect(self.export_data)
        btn_layout2.addWidget(self.export_btn)

        self.close_btn = QPushButton(LanguageManager.get_text('close'))
        self.close_btn.clicked.connect(self.close)
        btn_layout2.addWidget(self.close_btn)

        layout.addLayout(btn_layout2)

        layout.addStretch()

        scroll.setWidget(panel)
        return scroll

    def create_plot_panel(self):
        """创建绘图面板（带标签页）"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 第一个标签页：热图（带标记）
        self.heatmap_widget = QWidget()
        heatmap_layout = QVBoxLayout(self.heatmap_widget)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)
        self.heatmap_plot_engine = PlotEngine(parent=self.heatmap_widget)
        heatmap_layout.addWidget(self.heatmap_plot_engine.canvas)
        self.tab_widget.addTab(self.heatmap_widget, LanguageManager.get_text('heatmap_tab'))

        # 第二个标签页：分布曲线
        self.profile_widget = QWidget()
        profile_layout = QVBoxLayout(self.profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_plot_engine = PlotEngine(parent=self.profile_widget)
        profile_layout.addWidget(self.profile_plot_engine.canvas)
        self.tab_widget.addTab(self.profile_widget, LanguageManager.get_text('profile_curve'))

        # 第三个标签页：导数曲线
        self.derivative_widget = QWidget()
        derivative_layout = QVBoxLayout(self.derivative_widget)
        derivative_layout.setContentsMargins(0, 0, 0, 0)
        self.derivative_plot_engine = PlotEngine(parent=self.derivative_widget)
        derivative_layout.addWidget(self.derivative_plot_engine.canvas)
        self.tab_widget.addTab(self.derivative_widget, LanguageManager.get_text('derivative_curve'))

        layout.addWidget(self.tab_widget)

        # 为所有画布安装全局快捷键（不依赖焦点）
        for eng in [self.heatmap_plot_engine, self.profile_plot_engine,
                    self.derivative_plot_engine]:
            eng.install_global_hotkeys(self)

        return panel

    def get_current_unit(self):
        """获取当前单位"""
        try:
            xunit = self.heatmap_tab.xunit_combo.currentText()
            time_unit = self.heatmap_tab.time_unit_combo.currentText()
            return xunit, time_unit
        except:
            return 'um', 'ns'

    def add_profiles(self):
        """添加一个或多个Profile"""
        text = self.coord_value_edit.text()
        if not text.strip():
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('enter_coord_value'))
            return

        values = []
        for part in text.split(','):
            try:
                values.append(float(part.strip()))
            except ValueError:
                continue

        if not values:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('enter_valid_coord_value'))
            return

        coord_type_idx = self.coord_type_combo.currentIndex()
        coord_type = 'position' if coord_type_idx == 0 else 'time'
        xunit, time_unit = self.get_current_unit()
        unit = xunit if coord_type == 'position' else time_unit

        # 添加到表格
        for val in values:
            self.add_profile_to_table(coord_type, val, unit)

        self.coord_value_edit.clear()

    def add_profile_to_table(self, coord_type, coord_value, unit, ranges=None, block_signals=True):
        """添加一个Profile到表格"""
        # 阻塞信号防止初始化时触发（除非调用者指定不阻塞）
        if block_signals:
            self.profile_table.blockSignals(True)

        row = self.profile_table.rowCount()
        self.profile_table.insertRow(row)

        # Profile名称
        coord_name = LanguageManager.get_text('position_at').replace('=', '') if coord_type == 'position' else LanguageManager.get_text('time_at').replace('=', '')
        name_item = QTableWidgetItem(f"{coord_name}={coord_value:.2f} {unit}")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 不可编辑
        name_item.setData(Qt.UserRole, ProfileConfig(coord_type, coord_value, unit))
        self.profile_table.setItem(row, 0, name_item)

        # 范围
        if ranges:
            range_text = ','.join([f"{r[0]}-{r[1]}" for r in ranges])
        else:
            range_text = LanguageManager.get_text('all_ranges')

        range_item = QTableWidgetItem(range_text)
        range_item.setData(Qt.UserRole, ranges if ranges else [])
        self.profile_table.setItem(row, 1, range_item)

        # 删除按钮
        delete_btn = QPushButton(LanguageManager.get_text('remove'))
        delete_btn.clicked.connect(lambda _, r=row: self.delete_profile_row(r))
        self.profile_table.setCellWidget(row, 2, delete_btn)

        # 恢复信号
        if block_signals:
            self.profile_table.blockSignals(False)

    def delete_profile_row(self, row):
        """删除指定行的Profile"""
        self.profile_table.removeRow(row)

    def on_profile_item_changed(self, item):
        """表格项改变事件"""
        if item.column() != 1:  # 只处理范围列
            return

        try:
            # 检查是否已经阻塞
            was_blocked = self.profile_table.signalsBlocked()
            if not was_blocked:
                self.profile_table.blockSignals(True)

            text = item.text().strip()
            if text == "" or text == "全范围":
                ranges = []
            else:
                ranges = []
                parts = text.split(',')
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    if '-' in part:
                        try:
                            min_val, max_val = part.split('-', 1)
                            min_val = float(min_val.strip())
                            max_val = float(max_val.strip())
                            if min_val < max_val:
                                ranges.append((min_val, max_val))
                        except ValueError:
                            pass
                    else:
                        try:
                            val = float(part)
                            ranges.append((val, val))
                        except ValueError:
                            pass

            # 设置范围数据（setData不会触发itemChanged信号）
            item.setData(Qt.UserRole, ranges)

            # 只恢复信号如果是我们自己阻塞的
            if not was_blocked:
                self.profile_table.blockSignals(False)

        except Exception as e:
            self.logger.error(f"解析范围失败: {e}")
            if not self.profile_table.signalsBlocked():
                self.profile_table.blockSignals(False)

    def remove_selected_profile(self):
        """删除选中的Profile"""
        current_row = self.profile_table.currentRow()
        if current_row >= 0:
            self.profile_table.removeRow(current_row)

    def clear_all_profiles(self):
        """清空所有Profile"""
        self.profile_table.setRowCount(0)
        self.extracted_profiles.clear()
        self.detected_extremes.clear()
        self.profile_plot_engine.clear()
        self.derivative_plot_engine.clear()
        self.heatmap_plot_engine.clear()
        self.extreme_info_text.clear()

    def get_profiles_from_table(self):
        """从表格获取所有Profile配置"""
        profiles = []
        for row in range(self.profile_table.rowCount()):
            name_item = self.profile_table.item(row, 0)
            range_item = self.profile_table.item(row, 1)

            if name_item:
                config = name_item.data(Qt.UserRole)
                if config:
                    # 更新范围
                    if range_item:
                        config.ranges = range_item.data(Qt.UserRole)
                    profiles.append(config)
        return profiles

    def extract_profiles(self):
        """提取指定坐标的分布"""
        try:
            parser = self.data_manager.get_active_parser()
            if not parser:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('load_file_first'))
                return

            profile_configs = self.get_profiles_from_table()
            if not profile_configs:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('add_profile_first'))
                return

            var_idx = self.heatmap_tab.var_combo.currentIndex()
            if var_idx < 0:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('select_var_and_plot_heatmap_first'))
                return

            var = self.heatmap_tab.var_combo.itemData(var_idx)
            xunit = self.heatmap_tab.xunit_combo.currentText()
            time_unit = self.heatmap_tab.time_unit_combo.currentText()
            axis_direction = self.heatmap_tab.axis_combo.currentIndex()

            times = parser.get_time_array(unit=time_unit)
            coord_system = self.heatmap_tab.coord_combo.currentData() or 'XC'
            grid_pos = parser.get_grid_positions(unit=xunit, coord_system=coord_system)
            data_matrix = parser.get_spatial_data_all_times(var)

            if data_matrix.size == 0:
                QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('cannot_get_heatmap_data'))
                return

            if not isinstance(data_matrix, np.ndarray):
                data_matrix = np.array(data_matrix)

            # 提取每个Profile
            self.extracted_profiles = []
            for config in profile_configs:
                if config.coord_type == 'position':
                    profile_data = self._extract_time_profile(
                        config.coord_value, times, grid_pos, data_matrix, var, xunit, time_unit, axis_direction,
                        parser, coord_system
                    )
                else:
                    profile_data = self._extract_position_profile(
                        config.coord_value, times, grid_pos, data_matrix, var, xunit, time_unit, axis_direction,
                        parser, coord_system
                    )

                if profile_data:
                    profile_data['ranges'] = config.ranges
                    # 应用单位换算（与主面板一致）
                    from utils.config import Config as _C2
                    _vu = _C2.get_current_unit_for_var(var)
                    _vf = _C2.get_var_factor(var, _vu) if _vu else 1.0
                    if _vf != 1.0:
                        profile_data['y_data'] = profile_data['y_data'] * _vf
                    self.extracted_profiles.append(profile_data)

            self.detected_extremes = []
            self.plot_all()
            self.plot_heatmap_with_markers()

            # 代码录制钩子
            from utils.code_recorder import CodeRecorder
            recorder = CodeRecorder()
            if recorder.is_recording:
                profiles_data = []
                for config in profile_configs:
                    profiles_data.append({
                        'coord_type': config.coord_type,
                        'coord_value': config.coord_value,
                        'ranges': config.ranges
                    })
                from utils.config import Config
                value_unit = Config.get_current_unit_for_var(var)
                coord_system = self.heatmap_tab.coord_combo.currentData() or 'XC'
                xlim_auto = self.heatmap_tab.xlim_auto_cb.isChecked()
                ylim_auto = self.heatmap_tab.ylim_auto_cb.isChecked()
                heatmap_settings = {
                    'var': var,
                    'xunit': xunit,
                    'coord_system': coord_system,
                    'time_unit': time_unit,
                    'axis_direction': axis_direction,
                    'cmap': self.heatmap_tab.cmap_combo.currentText(),
                    'vmin': self.heatmap_tab.vmin_spin.value(),
                    'vmax': self.heatmap_tab.vmax_spin.value(),
                    'log_color': self.heatmap_tab.log_color_cb.isChecked(),
                    'value_unit': value_unit,
                    'value_factor': Config.get_var_factor(var, value_unit) if value_unit else 1.0,
                    'xlim': None if xlim_auto else (self.heatmap_tab.xlim_min.value(), self.heatmap_tab.xlim_max.value()),
                    'ylim': None if ylim_auto else (self.heatmap_tab.ylim_min.value(), self.heatmap_tab.ylim_max.value()),
                }
                recorder.record_extreme_finder(
                    profiles=profiles_data,
                    find_max=self.find_max_cb.isChecked(),
                    find_min=self.find_min_cb.isChecked(),
                    show_derivative=self.show_derivative_cb.isChecked(),
                    show_legend=self.show_legend_cb.isChecked(),
                    heatmap_settings=heatmap_settings
                )
                if hasattr(self.parent, 'code_recorder_dialog') and self.parent.code_recorder_dialog is not None:
                    self.parent.code_recorder_dialog.update_count()

        except Exception as e:
            self.logger.error(f"提取分布失败: {e}")
            QMessageBox.critical(self, LanguageManager.get_text('error'), f"{LanguageManager.get_text('extract_distribution_failed')}: {e}")

    def _extract_time_profile(self, coord_val, times, grid_pos, data_matrix, var, xunit, time_unit, axis_direction,
                              parser=None, coord_system='XC'):
        """提取固定位置的时间分布"""
        from scipy.interpolate import interp1d

        values = []
        n_times = len(times)
        n_data = len(data_matrix)

        for i in range(n_times):
            if i < n_data:
                row_data = data_matrix[i]
                if not isinstance(row_data, np.ndarray):
                    row_data = np.array(row_data)

                # 使用该时间步自己的坐标
                if parser is not None:
                    gp = parser.get_grid_positions(unit=xunit, coord_system=coord_system, time_idx=i)
                else:
                    gp = grid_pos
                n_points = min(len(gp), len(row_data))
                if n_points >= 2:
                    x_orig = gp[:n_points]
                    y_orig = row_data[:n_points]
                    try:
                        f = interp1d(x_orig, y_orig, kind='linear',
                                    bounds_error=False, fill_value=np.nan)
                        values.append(f(coord_val))
                    except:
                        values.append(np.nan)
                else:
                    values.append(np.nan)
            else:
                values.append(np.nan)

        return {
            'coord_type': 'position',
            'coord_value': coord_val,
            'x_data': times.copy(),
            'y_data': np.array(values),
            'var': var,
            'xunit': time_unit,
            'yunit': '',
            'xlabel': f'Time ({time_unit})',
            'ylabel': f'{var} at pos={coord_val:.2f} {xunit}',
            'axis_direction': axis_direction
        }

    def _extract_position_profile(self, coord_val, times, grid_pos, data_matrix, var, xunit, time_unit, axis_direction,
                                  parser=None, coord_system='XC'):
        """提取固定时间的位置分布"""
        t_min, t_max = np.min(times), np.max(times)
        if coord_val < t_min or coord_val > t_max:
            self.logger.warning(f"时间值 {coord_val} 超出范围 [{t_min}, {t_max}]")
            return None

        time_idx = np.argmin(np.abs(times - coord_val))

        n_data = len(data_matrix)
        if time_idx < n_data:
            row_data = data_matrix[time_idx]
            if not isinstance(row_data, np.ndarray):
                row_data = np.array(row_data)

            # 使用该时间步自己的坐标
            if parser is not None:
                gp = parser.get_grid_positions(unit=xunit, coord_system=coord_system, time_idx=time_idx)
            else:
                gp = grid_pos
            n_points = min(len(gp), len(row_data))
            x_orig = gp[:n_points].copy()
            y_orig = row_data[:n_points].copy()

            return {
                'coord_type': 'time',
                'coord_value': coord_val,
                'x_data': x_orig,
                'y_data': y_orig,
                'var': var,
                'xunit': xunit,
                'yunit': '',
                'xlabel': f'Position ({xunit})',
                'ylabel': f'{var} at t={coord_val:.2f} {time_unit}',
                'axis_direction': axis_direction
            }

        return None

    def find_extrema(self, x_data, y_data, ranges):
        """在指定范围内寻找全局最大值和最小值"""
        valid_mask = ~np.isnan(y_data)
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]

        if len(y_valid) < 1:
            return [], []

        if not ranges:
            # 全范围：找全局最大值和最小值
            max_idx = np.argmax(y_valid)
            min_idx = np.argmin(y_valid)
            maxima = [(x_valid[max_idx], y_valid[max_idx])] if len(y_valid) > 0 else []
            minima = [(x_valid[min_idx], y_valid[min_idx])] if len(y_valid) > 0 else []
        else:
            # 多范围：每个范围内找最大值和最小值
            maxima = []
            minima = []

            for min_val, max_val in ranges:
                mask = (x_valid >= min_val) & (x_valid <= max_val)
                x_range = x_valid[mask]
                y_range = y_valid[mask]

                if len(y_range) > 0:
                    max_idx = np.argmax(y_range)
                    min_idx = np.argmin(y_range)
                    maxima.append((x_range[max_idx], y_range[max_idx]))
                    minima.append((x_range[min_idx], y_range[min_idx]))

        return maxima, minima

    def compute_derivative(self, x_data, y_data):
        """计算导数"""
        valid_mask = ~np.isnan(y_data)
        x_valid = x_data[valid_mask]
        y_valid = y_data[valid_mask]

        if len(y_valid) < 2:
            return np.array([]), np.array([])

        dy = np.gradient(y_valid, x_valid)
        return x_valid, dy

    def plot_all(self):
        """绘制所有图形"""
        self.profile_plot_engine.clear()
        self.derivative_plot_engine.clear()

        if not self.extracted_profiles:
            return

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        show_legend = self.show_legend_cb.isChecked()
        show_derivative = self.show_derivative_cb.isChecked()

        ax = self.profile_plot_engine.ax
        ax.grid(True, linestyle='--', alpha=0.3)

        deriv_ax = self.derivative_plot_engine.ax
        deriv_ax.grid(True, linestyle='--', alpha=0.3)

        # 单位标签
        from utils.config import Config as _Config
        _first_var = self.extracted_profiles[0]['var'] if self.extracted_profiles else ''
        _yunit = _Config.get_current_unit_for_var(_first_var)
        _ylabel = _Config.format_var_label(_first_var, _yunit) if _yunit else _Config.format_var_label(_first_var)

        all_maxima = []
        all_minima = []

        for i, profile in enumerate(self.extracted_profiles):
            color = colors[i % len(colors)]
            x_data = profile['x_data']
            y_data = profile['y_data']
            ranges = profile.get('ranges', [])

            coord_type = profile['coord_type']
            coord_value = profile['coord_value']
            label = f"{coord_type}={coord_value:.2f}"
            ax.plot(x_data, y_data, color=color, linewidth=1.5, label=label)

            maxima, minima = self.find_extrema(x_data, y_data, ranges)

            if self.find_max_cb.isChecked():
                for xm, ym in maxima:
                    ax.plot(xm, ym, 'r^', markersize=8)
                    all_maxima.append((xm, ym, i, coord_type, coord_value))

            if self.find_min_cb.isChecked():
                for xm, ym in minima:
                    ax.plot(xm, ym, 'gv', markersize=8)
                    all_minima.append((xm, ym, i, coord_type, coord_value))

            if show_derivative:
                x_deriv, y_deriv = self.compute_derivative(x_data, y_data)
                if len(x_deriv) > 0:
                    deriv_ax.plot(x_deriv, y_deriv, color=color,
                                   linewidth=1.5, alpha=0.7, label=label)

        if self.extracted_profiles:
            first_profile = self.extracted_profiles[0]
            ax.set_xlabel(first_profile['xlabel'])
            ax.set_ylabel(_ylabel)

        if show_legend:
            ax.legend(loc='best', fontsize=8)
            deriv_ax.legend(loc='best', fontsize=8)

        self.profile_plot_engine.canvas.draw_idle()
        self.derivative_plot_engine.canvas.draw_idle()

        self.detected_extremes = all_maxima + all_minima
        self._update_extreme_info(all_maxima, all_minima)

    def plot_heatmap_with_markers(self):
        """在热图上绘制标记线和极值点

        热图部分直接调用 plot_interpolated_heatmap，与主面板 HeatmapTab.plot_heatmap
        同源 —— 自动具备逐时间步坐标、压强单位换算、coord_system 切换、xlim/ylim
        插值范围、colorbar 标签等全部特性，避免之前本地插值代码与主面板分叉。
        极值标记（白色虚线 + 黄色圆点）在热图之上单独叠加。
        """
        try:
            parser = self.data_manager.get_active_parser()
            if not parser:
                return

            ht = self.heatmap_tab
            var_idx = ht.var_combo.currentIndex()
            if var_idx < 0:
                return

            # 实时读取主面板的全部热图设置
            var = ht.var_combo.itemData(var_idx)
            xunit = ht.xunit_combo.currentText()
            time_unit = ht.time_unit_combo.currentText()
            coord_system = ht.coord_combo.currentData() or 'XC'
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

            # colorbar 标签与压强换算与主面板完全一致
            value_unit = Config.get_current_unit_for_var(var)
            if Config.is_pressure_var(var):
                plot_value_factor = Config.get_pressure_factor()
                colorbar_label = Config.format_pressure_label(var)
            elif value_unit:
                plot_value_factor = Config.get_var_factor(var, value_unit)
                colorbar_label = Config.format_var_label(var, value_unit)
            else:
                plot_value_factor = 1.0
                colorbar_label = parser.get_variable_display_name(var)

            if transpose:
                xlabel = 'Time'
                ylabel = 'Position'
            else:
                xlabel = 'Position'
                ylabel = 'Time'

            # profile 的标记线按物理意义分类：position profile → 位置线，
            # time profile → 时间线。plot_interpolated_heatmap 会处理 transpose
            # 时的轴交换，所以这里只管物理含义即可
            mark_positions = []
            mark_times = []
            for profile in self.extracted_profiles:
                if profile['coord_type'] == 'position':
                    mark_positions.append(profile['coord_value'])
                else:
                    mark_times.append(profile['coord_value'])

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

            # 极值标记：根据 axis_direction 把 (x_val, coord_value) 映射到绘图坐标
            # x_val 是极值在 profile x 轴上的位置（position profile → 时间，time profile → 位置）
            # coord_value 是 profile 的固定值
            extreme_points = []              # (x_plot, y_plot, value)
            extreme_vertical_lines = []      # X 轴值（垂直线）
            extreme_horizontal_lines = []    # Y 轴值（水平线）

            for x_val, y_val, profile_idx, coord_type, coord_value in self.detected_extremes:
                profile = self.extracted_profiles[profile_idx]
                if profile['coord_type'] == 'position':
                    # 固定位置 profile：x_data 是时间，x_val 是时间
                    if transpose:
                        # 横轴时间，纵轴位置
                        extreme_points.append((x_val, coord_value, y_val))
                        extreme_vertical_lines.append(x_val)
                    else:
                        # 横轴位置，纵轴时间
                        extreme_points.append((coord_value, x_val, y_val))
                        extreme_horizontal_lines.append(x_val)
                else:
                    # 固定时间 profile：x_data 是位置，x_val 是位置
                    if transpose:
                        extreme_points.append((coord_value, x_val, y_val))
                        extreme_horizontal_lines.append(x_val)
                    else:
                        extreme_points.append((x_val, coord_value, y_val))
                        extreme_vertical_lines.append(x_val)

            # 在热图之上叠加白色虚线 + 数值标注
            ax = self.heatmap_plot_engine.ax

            for v_line_pos in extreme_vertical_lines:
                ax.axvline(x=v_line_pos, color='white', linestyle='--', linewidth=2, alpha=0.8)
                ylim_cur = ax.get_ylim()
                y_text = ylim_cur[1] * 0.95
                ax.text(v_line_pos, y_text, f'{v_line_pos:.2f}',
                       color='white', fontsize=9, ha='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))

            for h_line_pos in extreme_horizontal_lines:
                ax.axhline(y=h_line_pos, color='white', linestyle='--', linewidth=2, alpha=0.8)
                xlim_cur = ax.get_xlim()
                x_text = xlim_cur[1] * 0.95
                ax.text(x_text, h_line_pos, f'{h_line_pos:.2f}',
                       color='white', fontsize=9, va='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))

            # 极值点（黄色圆点）
            for x_pt, y_pt, _ in extreme_points:
                ax.plot(x_pt, y_pt, 'yo', markersize=6, markeredgecolor='black', markeredgewidth=1.5)

            self.heatmap_plot_engine.canvas.draw_idle()

        except Exception as e:
            self.logger.error(f"绘制热图失败: {e}")

    def _update_extreme_info(self, all_maxima, all_minima):
        """更新极值信息显示"""
        if not all_maxima and not all_minima:
            self.extreme_info_text.setPlainText(LanguageManager.get_text('no_extreme'))
            return

        info_lines = []

        if all_maxima:
            info_lines.append(LanguageManager.get_text('maxima'))
            for xm, ym, idx, ct, cv in all_maxima:
                if ct == 'position':
                    pos_label = LanguageManager.get_text('position_at').replace('=', '')
                    info_lines.append(f"  {pos_label}={cv:.2f}: {LanguageManager.get_text('extreme_at_time').replace('极值在 ', '')} {xm:.4f}, {LanguageManager.get_text('value_equals')} {ym:.4e}")
                else:
                    time_label = LanguageManager.get_text('time_at').replace('=', '')
                    info_lines.append(f"  {time_label}={cv:.2f}: {LanguageManager.get_text('extreme_at_pos').replace('极值在 ', '')} {xm:.4f}, {LanguageManager.get_text('value_equals')} {ym:.4e}")
            info_lines.append("")

        if all_minima:
            info_lines.append(LanguageManager.get_text('minima'))
            for xm, ym, idx, ct, cv in all_minima:
                if ct == 'position':
                    pos_label = LanguageManager.get_text('position_at').replace('=', '')
                    info_lines.append(f"  {pos_label}={cv:.2f}: {LanguageManager.get_text('extreme_at_time').replace('极值在 ', '')} {xm:.4f}, {LanguageManager.get_text('value_equals')} {ym:.4e}")
                else:
                    time_label = LanguageManager.get_text('time_at').replace('=', '')
                    info_lines.append(f"  {time_label}={cv:.2f}: {LanguageManager.get_text('extreme_at_pos').replace('极值在 ', '')} {xm:.4f}, {LanguageManager.get_text('value_equals')} {ym:.4e}")

        self.extreme_info_text.setPlainText("\n".join(info_lines))

    def save_default_config(self):
        """保存为默认配置"""
        try:
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)

            profile_configs = self.get_profiles_from_table()
            config_data = {
                'profiles': [p.to_dict() for p in profile_configs],
                'find_max': self.find_max_cb.isChecked(),
                'find_min': self.find_min_cb.isChecked(),
                'show_derivative': self.show_derivative_cb.isChecked(),
                'show_legend': self.show_legend_cb.isChecked()
            }

            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, LanguageManager.get_text('success'), f"{LanguageManager.get_text('config_saved_to')}:\n{self.CONFIG_FILE}")
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.get_text('error'), f"{LanguageManager.get_text('save_config_failed')}: {e}")

    def load_default_config(self):
        """加载默认配置"""
        if not os.path.exists(self.CONFIG_FILE):
            return

        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 阻塞信号防止加载时触发
            self.profile_table.blockSignals(True)

            # 清空现有表格
            self.profile_table.setRowCount(0)

            # 加载Profiles
            for profile_dict in config_data.get('profiles', []):
                profile = ProfileConfig.from_dict(profile_dict)
                # 外层已阻塞信号，内部不再阻塞
                self.add_profile_to_table(profile.coord_type, profile.coord_value, profile.xunit, profile.ranges, block_signals=False)

            # 恢复信号
            self.profile_table.blockSignals(False)

            # 加载选项
            self.find_max_cb.setChecked(config_data.get('find_max', True))
            self.find_min_cb.setChecked(config_data.get('find_min', False))
            self.show_derivative_cb.setChecked(config_data.get('show_derivative', True))
            self.show_legend_cb.setChecked(config_data.get('show_legend', True))

            self.logger.info("已加载默认配置")

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            self.profile_table.blockSignals(False)

    def _get_default_save_dir(self):
        """获取默认保存目录（数据文件所在目录）"""
        parser = self.data_manager.get_active_parser()
        if parser and hasattr(parser, 'filepath'):
            return os.path.dirname(parser.filepath)
        return ""

    def _get_current_var(self):
        """获取当前变量名"""
        var_idx = self.heatmap_tab.var_combo.currentIndex()
        return self.heatmap_tab.var_combo.itemData(var_idx) if var_idx >= 0 else "data"

    def save_figure(self):
        """保存当前标签页的图片"""
        current_idx = self.tab_widget.currentIndex()
        var = self._get_current_var()
        tab_names = ['heatmap', 'profile', 'derivative']
        tab_name = tab_names[current_idx] if current_idx < len(tab_names) else 'plot'
        default_filename = f"{var}_{tab_name}.png"

        default_dir = self._get_default_save_dir()
        default_path = os.path.join(default_dir, default_filename) if default_dir else default_filename

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('save_image'), default_path,
            "PNG Images (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            engines = [self.heatmap_plot_engine, self.profile_plot_engine, self.derivative_plot_engine]
            engines[current_idx].save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            QMessageBox.information(self, LanguageManager.get_text('success'),
                                   f"{LanguageManager.get_text('image_saved_to')}:\n{filepath}")

    def save_all_figures(self):
        """保存所有标签页的图片"""
        var = self._get_current_var()
        default_dir = self._get_default_save_dir()

        # Use heatmap as the base filename for the dialog
        default_path = os.path.join(default_dir, f"{var}_heatmap.png") if default_dir else f"{var}_heatmap.png"

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('save_all_images'), default_path,
            "PNG Images (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        if not filepath:
            return

        base = os.path.splitext(filepath)[0]
        ext = filepath.split('.')[-1] if '.' in filepath else 'png'

        tab_names = ['heatmap', 'profile', 'derivative']
        engines = [self.heatmap_plot_engine, self.profile_plot_engine, self.derivative_plot_engine]

        saved = []
        for name, engine in zip(tab_names, engines):
            save_path = f"{base}_{name}.{ext}"
            engine.save_figure(save_path, dpi=Config.DEFAULT_SAVE_DPI, format=ext)
            saved.append(os.path.basename(save_path))

        QMessageBox.information(self, LanguageManager.get_text('success'),
                               f"{LanguageManager.get_text('image_saved_to')}:\n" + "\n".join(saved))

    def export_data(self):
        """导出数据"""
        if not self.extracted_profiles:
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('no_data_to_export'))
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('export_data'), "extreme_data.csv",
            "CSV Files (*.csv)"
        )

        if filepath:
            try:
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    header = ['X']
                    for profile in self.extracted_profiles:
                        header.append(f"{profile['coord_type']}={profile['coord_value']:.2f}")
                    writer.writerow(header)

                    all_x = set()
                    for profile in self.extracted_profiles:
                        all_x.update(profile['x_data'])

                    for x in sorted(all_x):
                        row = [f'{x:.6e}']
                        for profile in self.extracted_profiles:
                            idx = np.argmin(np.abs(profile['x_data'] - x))
                            if np.abs(profile['x_data'][idx] - x) < 1e-10:
                                y = profile['y_data'][idx]
                                row.append(f'{y:.6e}' if not np.isnan(y) else '')
                            else:
                                row.append('')
                        writer.writerow(row)

                QMessageBox.information(self, LanguageManager.get_text('success'), f"{LanguageManager.get_text('data_exported_to')}:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
