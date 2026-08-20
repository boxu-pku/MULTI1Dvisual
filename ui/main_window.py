"""MainWindow for MULTI1D Visualizer v2.3

主窗口，包含菜单栏、工具栏、标签页等
"""

import sys
import os

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu,
    QAction, QFileDialog, QStatusBar, QDialog,
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolBar, QFrame, QSplitter, QComboBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from ui.spatial_tab import SpatialTab
from ui.temporal_tab import TemporalTab
from ui.heatmap_tab import HeatmapTab
from core.data_manager import DataManager
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class MainWindow(QMainWindow):
    """主窗口类"""

    data_loaded = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.logger = Logger.get_logger('MainWindow')

        # 加载语言配置
        LanguageManager.load_language_config()

        # 当前样式设置
        self.current_color = Config.COLORS[0]
        self.current_linestyle = '-'
        self.current_linewidth = 1.5

        # 保持工具对话框的引用（防止被垃圾回收）
        self.annotation_dialog = None
        self.heatmap_profile_dialog = None
        self.extreme_finder_dialog = None
        self.code_recorder_dialog = None
        self.shock_detector_dialog = None

        # 初始化UI
        self.setup_ui()
        self.setup_menubar()
        self.setup_toolbar()
        self.setup_connections()
        self.apply_style()
        self.load_user_settings()

    def setup_ui(self):
        """设置UI布局"""
        self.setWindowTitle(f"{LanguageManager.get_text('app_name')} v{Config.APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 文件信息栏
        file_info_bar = self.create_file_info_bar()
        main_layout.addWidget(file_info_bar)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # 创建三个标签页
        self.spatial_tab = SpatialTab(self.data_manager, self)
        self.temporal_tab = TemporalTab(self.data_manager, self)
        self.heatmap_tab = HeatmapTab(self.data_manager, self)

        self.tab_widget.addTab(self.spatial_tab, LanguageManager.get_text('spatial_title'))
        self.tab_widget.addTab(self.temporal_tab, LanguageManager.get_text('temporal_title'))
        self.tab_widget.addTab(self.heatmap_tab, LanguageManager.get_text('heatmap_title'))

        main_layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(LanguageManager.get_text('no_data'))
        self.status_bar.addPermanentWidget(self.status_label)

        # 作者信息标签（显示在状态栏左侧）
        author_label = QLabel(f"Author: {Config.APP_AUTHOR} | Email: {Config.APP_EMAIL}")
        author_label.setStyleSheet("color: #666; padding-left: 10px;")
        self.status_bar.addWidget(author_label)

        # 连接信号
        self.data_loaded.connect(self._update_file_info_labels)

    def create_file_info_bar(self):
        """创建文件信息栏"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        frame.setMaximumHeight(50)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)

        # 文件标签
        layout.addWidget(QLabel("File:"))
        self.file_label = QLabel(LanguageManager.get_text('no_data'))
        self.file_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self.file_label)

        layout.addSpacing(20)

        # 时间步信息
        layout.addWidget(QLabel("Timesteps:"))
        self.timestep_label = QLabel("-")
        layout.addWidget(self.timestep_label)

        layout.addSpacing(20)

        # 网格数信息
        layout.addWidget(QLabel("Cells:"))
        self.cells_label = QLabel("-")
        layout.addWidget(self.cells_label)

        layout.addStretch()

        # 按钮
        self.load_btn = QPushButton(LanguageManager.get_text('menu_open'))
        self.load_btn.setMinimumWidth(120)
        self.load_btn.clicked.connect(self.open_file)
        layout.addWidget(self.load_btn)

        self.reload_btn = QPushButton("Reload")
        self.reload_btn.setMinimumWidth(100)
        self.reload_btn.clicked.connect(self.reload_files)
        self.reload_btn.setEnabled(False)
        layout.addWidget(self.reload_btn)

        return frame

    def setup_menubar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # ========== 文件菜单 ==========
        file_menu = menubar.addMenu(LanguageManager.get_text('menu_file'))

        open_action = QAction(LanguageManager.get_text('menu_open'), self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_img_action = QAction("Save Image...", self)
        save_img_action.setShortcut("Ctrl+S")
        save_img_action.triggered.connect(self.save_current_figure)
        file_menu.addAction(save_img_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ========== 视图菜单 ==========
        view_menu = menubar.addMenu(LanguageManager.get_text('menu_view'))

        spatial_action = QAction(LanguageManager.get_text('spatial_title'), self)
        spatial_action.setShortcut("Ctrl+1")
        spatial_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(spatial_action)

        temporal_action = QAction(LanguageManager.get_text('temporal_title'), self)
        temporal_action.setShortcut("Ctrl+2")
        temporal_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(temporal_action)

        heatmap_action = QAction(LanguageManager.get_text('heatmap_title'), self)
        heatmap_action.setShortcut("Ctrl+3")
        heatmap_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction(heatmap_action)

        # ========== 导出菜单 ==========
        export_menu = menubar.addMenu(LanguageManager.get_text('menu_export'))

        export_ascii_action = QAction("Export as ASCII...", self)
        export_ascii_action.triggered.connect(self.export_ascii)
        export_menu.addAction(export_ascii_action)

        export_csv_action = QAction("Export as CSV...", self)
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)

        # ========== 工具菜单 ==========
        tools_menu = menubar.addMenu(LanguageManager.get_text('menu_tools'))

        annotation_action = QAction(LanguageManager.get_text('tool_annotation'), self)
        annotation_action.setShortcut("Ctrl+M")
        annotation_action.triggered.connect(self.show_annotation_tool)
        tools_menu.addAction(annotation_action)

        # 热图分布提取
        heatmap_profile_action = QAction(LanguageManager.get_text('tool_heatmap_profile'), self)
        heatmap_profile_action.setShortcut("Ctrl+H")
        heatmap_profile_action.triggered.connect(self.show_heatmap_profile_tool)
        tools_menu.addAction(heatmap_profile_action)

        # 极值寻找工具
        extreme_finder_action = QAction(LanguageManager.get_text('tool_extreme_finder'), self)
        extreme_finder_action.setShortcut("Ctrl+E")
        extreme_finder_action.triggered.connect(self.show_extreme_finder_tool)
        tools_menu.addAction(extreme_finder_action)

        # 冲击波检测工具
        shock_detector_action = QAction(LanguageManager.get_text('tool_shock_detector'), self)
        shock_detector_action.setShortcut("Ctrl+D")
        shock_detector_action.triggered.connect(self.show_shock_detector_tool)
        tools_menu.addAction(shock_detector_action)

        # 代码录制工具
        code_recorder_action = QAction(LanguageManager.get_text('tool_code_recorder'), self)
        code_recorder_action.setShortcut("Ctrl+R")
        code_recorder_action.triggered.connect(self.show_code_recorder_tool)
        tools_menu.addAction(code_recorder_action)

        # ========== 设置菜单 ==========
        settings_menu = menubar.addMenu(LanguageManager.get_text('menu_settings'))

        # 线条样式子菜单
        style_menu = settings_menu.addMenu(LanguageManager.get_text('line_style_menu'))

        # 颜色
        color_menu = style_menu.addMenu(LanguageManager.get_text('color_menu'))
        self.color_actions = {}
        for color in Config.COLORS[:10]:
            action = QAction(color, self, checkable=True)
            action.triggered.connect(lambda checked, c=color: self.set_color(c))
            color_menu.addAction(action)
            self.color_actions[color] = action
        self.color_actions[Config.COLORS[0]].setChecked(True)

        # 线型
        linestyle_menu = style_menu.addMenu(LanguageManager.get_text('linestyle_menu'))
        self.linestyle_actions = {}
        for ls_name, ls in [
            (LanguageManager.get_text('solid_line'), '-'),
            (LanguageManager.get_text('dashed_line'), '--'),
            (LanguageManager.get_text('dash_dot_line'), '-.'),
            (LanguageManager.get_text('dotted_line'), ':')
        ]:
            action = QAction(ls_name, self, checkable=True)
            action.triggered.connect(lambda checked, l=ls: self.set_linestyle(l))
            linestyle_menu.addAction(action)
            self.linestyle_actions[ls] = action
        self.linestyle_actions['-'].setChecked(True)

        # 自定义颜色
        custom_color_action = QAction(LanguageManager.get_text('custom_color'), self)
        custom_color_action.triggered.connect(self.pick_custom_color)
        settings_menu.addAction(custom_color_action)

        # ========== 帮助菜单 ==========
        help_menu = menubar.addMenu(LanguageManager.get_text('menu_help'))

        # 语言切换
        language_action = QAction(LanguageManager.get_text('menu_change_language'), self)
        language_action.triggered.connect(self.change_language)
        help_menu.addAction(language_action)

        help_menu.addSeparator()

        about_action = QAction(LanguageManager.get_text('menu_about'), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        shortcut_action = QAction(LanguageManager.get_text('help_shortcuts'), self)
        shortcut_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcut_action)

    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)

        # 打开文件
        open_action = QAction("Open", self)
        open_action.setToolTip("Open fort.10 file (Ctrl+O)")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # 保存图片
        save_action = QAction("Save", self)
        save_action.setToolTip("Save current image (Ctrl+S)")
        save_action.triggered.connect(self.save_current_figure)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # 重新加载
        reload_action = QAction("Reload", self)
        reload_action.setToolTip("Reload current file")
        reload_action.triggered.connect(self.reload_files)
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        # 极值寻找
        extreme_action = QAction("Extreme Finder", self)
        extreme_action.setToolTip("Extract profiles from heatmap and find extremes (Ctrl+E)")
        extreme_action.triggered.connect(self.show_extreme_finder_tool)
        toolbar.addAction(extreme_action)

        toolbar.addSeparator()

        # 冲击波检测
        shock_action = QAction("Shock Detector", self)
        shock_action.setToolTip("Detect shock wave front from density evolution (Ctrl+D)")
        shock_action.triggered.connect(self.show_shock_detector_tool)
        toolbar.addAction(shock_action)

    def setup_connections(self):
        """设置信号连接"""
        pass

    def apply_style(self):
        """应用样式"""
        # 使用Fusion样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
                background-color: #e0e0e0;
                border: 1px solid #ccc;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QComboBox {
                padding: 3px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin-right: 2px;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
            }
            QTabBar::tab:!selected {
                background-color: #e0e0e0;
            }
        """)

    def load_user_settings(self):
        """加载用户设置"""
        settings = Config.load_settings()
        if settings:
            self.logger.info("已加载用户设置")

    def save_user_settings(self):
        """保存用户设置"""
        settings = {
            'color': self.current_color,
            'linestyle': self.current_linestyle,
            'linewidth': self.current_linewidth
        }
        Config.save_settings(settings)

    # ========== 文件操作 ==========

    def open_file(self):
        """打开数据文件（二进制 fort.10 / 十进制 .case）"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "",
            "支持的文件 (*.case fort.10 *.out);;"
            "Case 文件 (*.case);;"
            "二进制文件 (fort.10 *.out);;"
            "所有文件 (*)"
        )

        if filepath:
            self._load_file(filepath)

    def _load_file(self, filepath: str):
        """加载文件"""
        self.status_label.setText(f"正在加载: {filepath}...")
        QApplication.processEvents()

        if self.data_manager.load_file(filepath):
            self.reload_btn.setEnabled(True)

            # 更新各标签页数据
            self.spatial_tab.update_data()
            self.temporal_tab.update_data()
            self.heatmap_tab.update_data()

            # 更新文件信息
            parser = self.data_manager.get_active_parser()
            if parser:
                self.file_label.setText(os.path.basename(filepath))
                self.timestep_label.setText(str(parser.get_n_timesteps()))
                self.cells_label.setText(str(parser.get_n_cells()))

            self.data_loaded.emit(True)
            self.status_label.setText(f"Loaded: {filepath}")
            self.logger.info(f"Successfully loaded file: {filepath}")

            # 代码录制钩子
            from utils.code_recorder import CodeRecorder
            recorder = CodeRecorder()
            if recorder.is_recording:
                recorder.record_file_open(filepath)
                if self.code_recorder_dialog is not None:
                    self.code_recorder_dialog.update_count()
        else:
            QMessageBox.critical(self, LanguageManager.get_text('error'),
                               f"{LanguageManager.get_text('cannot_load_file')}: {filepath}")
            self.status_label.setText("Load failed")

    def reload_files(self):
        """重新加载文件"""
        parser = self.data_manager.get_active_parser()
        if parser:
            filepath = parser.filepath
            self.data_manager.unload_file(filepath)
            self._load_file(filepath)

    def _update_file_info_labels(self):
        """更新文件信息标签"""
        parser = self.data_manager.get_active_parser()
        if parser:
            self.timestep_label.setText(str(parser.get_n_timesteps()))
            self.cells_label.setText(str(parser.get_n_cells()))

    # ========== 导出功能 ==========

    def save_current_figure(self):
        """保存当前图片"""
        current_tab = self.tab_widget.currentWidget()
        if hasattr(current_tab, 'save_figure'):
            current_tab.save_figure()
        else:
            QMessageBox.information(self, LanguageManager.get_text('info'),
                                   LanguageManager.get_text('current_tab_no_save_support'))

    def export_ascii(self):
        """导出为ASCII格式"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('load_file_first'))
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export ASCII File", "", "Text Files (*.txt);;All Files (*)"
        )

        if filepath:
            try:
                from legacy.scanFile import writeAsciiCurves, writeAsciiTimeSeries
                # 获取原始数据
                writeAsciiCurves(filepath.replace('.txt', '_SCout.txt'), parser.second_dict)
                writeAsciiTimeSeries(filepath.replace('.txt', '_TSout.txt'), parser.second_dict)
                self.status_label.setText(f"Exported: {filepath}")
                QMessageBox.information(self, LanguageManager.get_text('success'),
                                       LanguageManager.get_text('data_exported_successfully'))
            except Exception as e:
                QMessageBox.critical(self, LanguageManager.get_text('error'),
                                   f"{LanguageManager.get_text('export_failed')}: {e}")

    def export_csv(self):
        """导出为CSV格式"""
        parser = self.data_manager.get_active_parser()
        if not parser:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('load_file_first'))
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if filepath:
            try:
                import pandas as pd

                # 导出空间数据
                spatial_vars = parser.get_available_spatial_vars()
                times = parser.get_time_array(unit='ns')

                for var in spatial_vars[:5]:  # 限制变量数量
                    data = parser.get_spatial_data_all_times(var)
                    if data.size > 0:
                        df = pd.DataFrame(data.T, columns=[f't={t:.3f}ns' for t in times])
                        var_filepath = filepath.replace('.csv', f'_{var}.csv')
                        df.to_csv(var_filepath, index=False)

                self.status_label.setText(f"CSV files exported")
                QMessageBox.information(self, LanguageManager.get_text('success'),
                                       LanguageManager.get_text('data_exported_successfully'))
            except ImportError:
                QMessageBox.warning(self, LanguageManager.get_text('warning'),
                                  LanguageManager.get_text('need_pandas_for_csv'))
            except Exception as e:
                QMessageBox.critical(self, LanguageManager.get_text('error'),
                                   f"{LanguageManager.get_text('export_failed')}: {e}")

    # ========== 样式设置 ==========

    def set_color(self, color: str):
        """设置颜色"""
        self.current_color = color
        for c, action in self.color_actions.items():
            action.setChecked(c == color)
        self.status_label.setText(f"线条颜色: {color}")

    def set_linestyle(self, linestyle: str):
        """设置线型"""
        self.current_linestyle = linestyle
        for ls, action in self.linestyle_actions.items():
            action.setChecked(ls == linestyle)
        self.status_label.setText(f"线型: {linestyle}")

    def set_linewidth(self, linewidth: float):
        """设置线宽"""
        self.current_linewidth = linewidth
        self.status_label.setText(f"线宽: {linewidth}")

    def pick_custom_color(self):
        """选择自定义颜色"""
        from PyQt5.QtWidgets import QColorDialog

        color = QColorDialog.getColor()
        if color.isValid():
            color_name = color.name()
            Config.COLORS.insert(0, color_name)
            self.set_color(color_name)

    # ========== 工具功能 ==========

    def show_annotation_tool(self):
        """显示标注工具对话框"""
        # 获取当前标签页的绘图引擎
        current_tab = self.tab_widget.currentWidget()
        if not hasattr(current_tab, 'plot_engine') or not current_tab.plot_engine:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('no_canvas_available'))
            return

        # 如果已有对话框在显示且可见，则激活它
        if self.annotation_dialog is not None and self.annotation_dialog.isVisible():
            self.annotation_dialog.raise_()
            self.annotation_dialog.activateWindow()
            return

        from ui.annotation_dialog import AnnotationDialog
        self.annotation_dialog = AnnotationDialog(current_tab.plot_engine, self)
        # 连接对话框完成信号（关闭时触发）
        self.annotation_dialog.finished.connect(self._on_annotation_dialog_finished)
        # 使用 show() 非模态显示，允许在主画布上交互
        self.annotation_dialog.show()

    def _on_annotation_dialog_finished(self):
        """标注对话框关闭时的回调"""
        if self.annotation_dialog is not None:
            # 断开事件连接
            if hasattr(self.annotation_dialog, 'annotation_canvas'):
                self.annotation_dialog.annotation_canvas.disconnect_events()
            self.annotation_dialog = None

    def show_heatmap_profile_tool(self):
        """显示热图分布提取工具"""
        # 检查是否在热图标签页
        current_tab = self.tab_widget.currentWidget()
        if current_tab != self.heatmap_tab:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('switch_to_heatmap_first'))
            return

        if not hasattr(current_tab, 'plot_engine') or not current_tab.plot_engine:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('plot_heatmap_first'))
            return

        # 如果已有对话框在显示且可见，则激活它
        if self.heatmap_profile_dialog is not None and self.heatmap_profile_dialog.isVisible():
            self.heatmap_profile_dialog.raise_()
            self.heatmap_profile_dialog.activateWindow()
            return

        from ui.heatmap_profile_dialog import HeatmapProfileDialog
        self.heatmap_profile_dialog = HeatmapProfileDialog(current_tab.plot_engine, current_tab, self)
        # 连接对话框完成信号（关闭时触发）
        self.heatmap_profile_dialog.finished.connect(self._on_heatmap_profile_dialog_finished)
        # 使用 show() 非模态显示，允许在主画布上交互
        self.heatmap_profile_dialog.show()

    def _on_heatmap_profile_dialog_finished(self):
        """热图分布提取对话框关闭时的回调"""
        if self.heatmap_profile_dialog is not None:
            # 停止提取并断开事件
            self.heatmap_profile_dialog.stop_extraction()
            self.heatmap_profile_dialog = None

    def show_extreme_finder_tool(self):
        """显示极值寻找工具"""
        # 检查是否在热图标签页
        current_tab = self.tab_widget.currentWidget()
        if current_tab != self.heatmap_tab:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('switch_to_heatmap_first'))
            return

        if not hasattr(current_tab, 'plot_engine') or not current_tab.plot_engine:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('plot_heatmap_first'))
            return

        # 如果已有对话框在显示且可见，则激活它
        if self.extreme_finder_dialog is not None and self.extreme_finder_dialog.isVisible():
            self.extreme_finder_dialog.raise_()
            self.extreme_finder_dialog.activateWindow()
            return

        from ui.extreme_finder_dialog import ExtremeFinderDialog
        self.extreme_finder_dialog = ExtremeFinderDialog(
            self.data_manager, current_tab, self
        )
        # 连接对话框完成信号
        self.extreme_finder_dialog.finished.connect(self._on_extreme_finder_dialog_finished)
        self.extreme_finder_dialog.show()

    def _on_extreme_finder_dialog_finished(self):
        """极值寻找对话框关闭时的回调"""
        self.extreme_finder_dialog = None

    def show_shock_detector_tool(self):
        """显示冲击波检测工具"""
        # 检查是否在热图标签页
        current_tab = self.tab_widget.currentWidget()
        if current_tab != self.heatmap_tab:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('switch_to_heatmap_first'))
            return

        if not hasattr(current_tab, 'plot_engine') or not current_tab.plot_engine:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('plot_heatmap_first'))
            return

        # 如果已有对话框在显示且可见，则激活它
        if self.shock_detector_dialog is not None and self.shock_detector_dialog.isVisible():
            self.shock_detector_dialog.raise_()
            self.shock_detector_dialog.activateWindow()
            return

        from ui.shock_detector_dialog import ShockDetectorDialog
        self.shock_detector_dialog = ShockDetectorDialog(
            self.data_manager, current_tab, self
        )
        # 连接对话框完成信号
        self.shock_detector_dialog.finished.connect(self._on_shock_detector_dialog_finished)
        # 更新对话框数据
        self.shock_detector_dialog.update_data()
        self.shock_detector_dialog.show()

    def _on_shock_detector_dialog_finished(self):
        """冲击波检测对话框关闭时的回调"""
        self.shock_detector_dialog = None

    def show_code_recorder_tool(self):
        """显示代码录制工具"""
        # 如果已有对话框在显示且可见，则激活它
        if self.code_recorder_dialog is not None and self.code_recorder_dialog.isVisible():
            self.code_recorder_dialog.raise_()
            self.code_recorder_dialog.activateWindow()
            return

        from ui.code_recorder_dialog import CodeRecorderDialog
        self.code_recorder_dialog = CodeRecorderDialog(self.data_manager, self)
        self.code_recorder_dialog.finished.connect(self._on_code_recorder_dialog_finished)
        self.code_recorder_dialog.show()

    def _on_code_recorder_dialog_finished(self):
        """代码录制对话框关闭时的回调"""
        self.code_recorder_dialog = None

    # ========== 帮助信息 ==========

    def show_about(self):
        """显示关于对话框"""
        app_name = LanguageManager.get_text('app_name')
        QMessageBox.about(
            self, LanguageManager.get_text('menu_about'),
            f"<h3>{app_name}</h3>"
            f"<p>Version: {Config.APP_VERSION}</p>"
            f"<p>Date: {Config.APP_DATE}</p>"
            f"<p>Author: {Config.APP_AUTHOR}</p>"
            f"<p>Email: {Config.APP_EMAIL}</p>"
            f"<hr>"
            f"<p>MULTI1D Simulation Result Visualization Tool</p>"
            f"<p>Supports reading and visualization of fort.10 binary files</p>"
            f"<hr>"
            f"<p>Features:</p>"
            f"<ul>"
            f"<li>Spatial Plot: Plot variables vs position</li>"
            f"<li>Temporal Plot: Plot variables vs time</li>"
            f"<li>Heatmap: Plot spatiotemporal distribution</li>"
            f"</ul>"
        )

    def show_shortcuts(self):
        """显示快捷键"""
        shortcuts = """
        <h3>Keyboard Shortcuts</h3>
        <table>
        <tr><td><b>Ctrl+O</b></td><td>Open fort.10 file</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save current image</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit program</td></tr>
        <tr><td><b>Ctrl+1</b></td><td>Switch to Spatial Plot</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>Switch to Temporal Plot</td></tr>
        <tr><td><b>Ctrl+3</b></td><td>Switch to Heatmap</td></tr>
        </table>
        """
        QMessageBox.information(self, LanguageManager.get_text('help_shortcuts'), shortcuts)

    def change_language(self):
        """更改语言"""
        dialog = QDialog(self)
        dialog.setWindowTitle(LanguageManager.get_text('settings_language'))
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        # 当前语言提示
        current_lang = LanguageManager.get_current_language()
        current_lang_name = LanguageManager.get_language_name(current_lang)
        layout.addWidget(QLabel(f"当前语言: {current_lang_name}"))

        layout.addWidget(QLabel("选择语言 / Select Language:"))

        # 语言选择下拉框
        lang_combo = QComboBox()
        for lang_code, lang_name in LanguageManager.get_available_languages():
            lang_combo.addItem(lang_name, lang_code)
        lang_combo.setCurrentIndex(0 if current_lang == 'zh' else 1)
        layout.addWidget(lang_combo)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            selected_lang = lang_combo.currentData()
            if selected_lang != current_lang:
                LanguageManager.set_language(selected_lang)
                LanguageManager.save_language_config()

                QMessageBox.information(
                    self,
                    LanguageManager.get_text('language_changed'),
                    "请重启程序以应用所有更改\nPlease restart the application to apply all changes."
                )

    # ========== 窗口事件 ==========

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 关闭工具对话框
        if self.annotation_dialog is not None:
            self.annotation_dialog.close()
        if self.heatmap_profile_dialog is not None:
            self.heatmap_profile_dialog.close()
        if self.extreme_finder_dialog is not None:
            self.extreme_finder_dialog.close()
        if self.code_recorder_dialog is not None:
            self.code_recorder_dialog.close()

        self.save_user_settings()
        event.accept()


# 需要导入QApplication
from PyQt5.QtWidgets import QApplication
