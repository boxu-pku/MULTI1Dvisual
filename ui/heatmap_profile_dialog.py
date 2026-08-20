"""HeatmapProfileExtractor - 热图分布提取工具
从热图中提取沿某条线上的颜色映射量分布
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QMessageBox, QFileDialog, QWidget, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import numpy as np

from core.plot_engine import PlotEngine
from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class HeatmapProfileExtractor:
    """热图分布提取器 - 处理鼠标交互和数据提取"""

    def __init__(self, plot_engine, heatmap_tab, parent=None):
        self.plot_engine = plot_engine
        self.heatmap_tab = heatmap_tab
        self.parent = parent
        self.logger = Logger.get_logger('HeatmapProfileExtractor')

        # 绘制状态
        self.is_drawing = False
        self.start_pos = None
        self.temp_line = None
        self.line_artist = None

        # 提取的数据
        self.extracted_data = None
        self.line_coords = None

        # 鼠标事件连接ID
        self.press_cid = None
        self.release_cid = None
        self.motion_cid = None

        # 回调函数：当线条绘制时调用
        self.on_line_drawn = None

    def connect_events(self):
        """连接鼠标事件"""
        self.press_cid = self.plot_engine.canvas.mpl_connect(
            'button_press_event', self.on_mouse_press
        )
        self.release_cid = self.plot_engine.canvas.mpl_connect(
            'button_release_event', self.on_mouse_release
        )
        self.motion_cid = self.plot_engine.canvas.mpl_connect(
            'motion_notify_event', self.on_mouse_move
        )
        self.logger.info("热图分布提取工具已激活，请在热图上拖拽绘制直线")

    def disconnect_events(self):
        """断开鼠标事件"""
        if self.press_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.press_cid)
            except:
                pass
        if self.release_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.release_cid)
            except:
                pass
        if self.motion_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.motion_cid)
            except:
                pass

        # 清除临时绘制
        if self.temp_line:
            try:
                self.temp_line.remove()
            except:
                pass
            self.temp_line = None
        self.plot_engine.canvas.draw_idle()

    def on_mouse_press(self, event):
        """鼠标按下事件"""
        if event.inaxes != self.plot_engine.ax:
            return

        self.is_drawing = True
        self.start_pos = (event.xdata, event.ydata)

    def on_mouse_release(self, event):
        """鼠标释放事件"""
        if not self.is_drawing or event.inaxes != self.plot_engine.ax:
            self.is_drawing = False
            return

        end_pos = (event.xdata, event.ydata)

        # 移除临时线
        if self.temp_line:
            try:
                self.temp_line.remove()
            except:
                pass
            self.temp_line = None

        # 提取分布数据
        self.extract_profile(self.start_pos, end_pos)

        self.is_drawing = False
        self.start_pos = None

    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.is_drawing or event.inaxes != self.plot_engine.ax:
            return

        # 移除临时线
        if self.temp_line:
            try:
                self.temp_line.remove()
            except:
                pass

        # 绘制预览线
        end_pos = (event.xdata, event.ydata)
        self.temp_line, = self.plot_engine.ax.plot(
            [self.start_pos[0], end_pos[0]],
            [self.start_pos[1], end_pos[1]],
            color='white', linewidth=2, linestyle='-', alpha=0.8
        )
        self.plot_engine.canvas.draw_idle()

    def extract_profile(self, start_pos, end_pos):
        """提取沿直线的分布数据"""
        try:
            # Use the already-interpolated data from PlotEngine (no re-interpolation)
            if self.plot_engine._heatmap_data is None:
                QMessageBox.warning(self.parent, LanguageManager.get_text('warning'),
                                   LanguageManager.get_text('plot_heatmap_first'))
                return

            xarr, yarr, data = self.plot_engine._heatmap_data

            var_idx = self.heatmap_tab.var_combo.currentIndex()
            if var_idx < 0:
                QMessageBox.warning(self.parent, LanguageManager.get_text('warning'),
                                   LanguageManager.get_text('select_var_and_plot_heatmap_first'))
                return
            var = self.heatmap_tab.var_combo.itemData(var_idx)

            # Sample along the line using 2D interpolation on the stored grid
            n_samples = 200
            x_values = np.linspace(start_pos[0], end_pos[0], n_samples)
            y_values = np.linspace(start_pos[1], end_pos[1], n_samples)

            from scipy.interpolate import RegularGridInterpolator
            interp_func = RegularGridInterpolator(
                (yarr, xarr), data,
                method='linear', bounds_error=False, fill_value=np.nan
            )
            points = np.column_stack([y_values, x_values])
            profile_values = interp_func(points)

            # Distance along line
            distances = np.sqrt(
                (x_values - start_pos[0])**2 + (y_values - start_pos[1])**2
            )

            # Store extracted data
            self.extracted_data = {
                'distances': distances,
                'values': profile_values,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'var': var,
                'xunit': self.heatmap_tab.xunit_combo.currentText(),
                'time_unit': self.heatmap_tab.time_unit_combo.currentText()
            }

            # 代码录制钩子
            from utils.code_recorder import CodeRecorder
            recorder = CodeRecorder()
            if recorder.is_recording:
                recorder.record_profile_extraction(
                    start_pos=start_pos,
                    end_pos=end_pos,
                    var=var,
                    xunit=self.heatmap_tab.xunit_combo.currentText(),
                    time_unit=self.heatmap_tab.time_unit_combo.currentText()
                )
                if hasattr(self.parent, 'main_window') and hasattr(self.parent.main_window, 'code_recorder_dialog'):
                    if self.parent.main_window.code_recorder_dialog is not None:
                        self.parent.main_window.code_recorder_dialog.update_count()
                elif hasattr(self.parent, 'code_recorder_dialog') and self.parent.code_recorder_dialog is not None:
                    self.parent.code_recorder_dialog.update_count()

            # Draw line on heatmap
            if self.line_artist:
                try:
                    self.line_artist.remove()
                except:
                    pass
            self.line_artist, = self.plot_engine.ax.plot(
                [start_pos[0], end_pos[0]],
                [start_pos[1], end_pos[1]],
                color='white', linewidth=2, linestyle='-', alpha=0.9
            )
            self.plot_engine.canvas.draw_idle()

            # Callback to sync line_artist to dialog
            if self.on_line_drawn is not None:
                self.on_line_drawn(self.line_artist)

            # Show profile dialog
            self.show_profile_dialog()

        except Exception as e:
            self.logger.error(f"提取分布数据失败: {e}")
            QMessageBox.critical(self.parent, LanguageManager.get_text('error'),
                               f"{LanguageManager.get_text('extract_distribution_failed')}: {e}")

    def show_profile_dialog(self):
        """显示分布曲线对话框"""
        if self.extracted_data is None:
            return

        dialog = ProfileDialog(self.extracted_data, self.parent)
        dialog.exec_()


class ProfileDialog(QDialog):
    """分布曲线显示对话框"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.logger = Logger.get_logger('ProfileDialog')

        self.setWindowTitle(f"热图分布提取 - {data['var']}")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 信息标签
        info_label = QLabel(
            f"变量: {self.data['var']} | "
            f"起点: ({self.data['start_pos'][0]:.2f}, {self.data['start_pos'][1]:.2f}) | "
            f"终点: ({self.data['end_pos'][0]:.2f}, {self.data['end_pos'][1]:.2f})"
        )
        layout.addWidget(info_label)

        # 绘图区域
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_engine = PlotEngine(parent=plot_widget)
        plot_layout.addWidget(self.plot_engine.canvas)
        self.plot_engine.install_global_hotkeys(self)
        layout.addWidget(plot_widget)

        # 绘制分布曲线
        self.plot_profile()

        # 按钮行
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton(LanguageManager.get_text('save_image'))
        self.save_btn.clicked.connect(self.save_figure)
        btn_layout.addWidget(self.save_btn)

        self.export_btn = QPushButton(LanguageManager.get_text('export_data'))
        self.export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(self.export_btn)

        self.close_btn = QPushButton(LanguageManager.get_text('close'))
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def plot_profile(self):
        """绘制分布曲线"""
        distances = self.data['distances']
        values = self.data['values']

        # 获取变量显示名称
        var = self.data['var']

        # 绘制
        self.plot_engine.clear()
        self.plot_engine.ax.grid(True, linestyle='--', alpha=0.3)
        self.plot_engine.ax.plot(distances, values, 'b-', linewidth=1.5)
        self.plot_engine.ax.set_xlabel('Distance along line')
        self.plot_engine.ax.set_ylabel(f'{var} (color value)')
        self.plot_engine.ax.set_title('Profile along extracted line')
        self.plot_engine.canvas.draw_idle()

    def save_figure(self):
        """保存图片"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图片", f"{self.data['var']}_profile.png",
            "PNG图片 (*.png);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            self.plot_engine.save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            QMessageBox.information(self, "成功", f"图片已保存至:\n{filepath}")

    def export_data(self):
        """导出数据"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出数据", f"{self.data['var']}_profile.csv",
            "CSV文件 (*.csv)"
        )
        if filepath:
            try:
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Distance', f'{self.data["var"]}'])
                    for d, v in zip(self.data['distances'], self.data['values']):
                        writer.writerow([f'{d:.6e}', f'{v:.6e}' if not np.isnan(v) else ''])
                QMessageBox.information(self, "成功", f"数据已导出至:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")


class HeatmapProfileDialog(QDialog):
    """热图分布提取工具对话框"""

    def __init__(self, plot_engine, heatmap_tab, parent=None):
        super().__init__(parent)
        self.plot_engine = plot_engine
        self.heatmap_tab = heatmap_tab
        self.parent = parent
        self.logger = Logger.get_logger('HeatmapProfileDialog')

        self.extractor = None
        # 单独保存标记线的引用，这样即使停止后也能清除
        self.line_artist = None

        self.setWindowTitle("热图分布提取工具")
        self.setMinimumSize(350, 250)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 使用说明
        help_group = QGroupBox(LanguageManager.get_text('instructions'))
        help_layout = QVBoxLayout(help_group)
        help_text = LanguageManager.get_text('heatmap_profile_help_en')
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addWidget(help_group)

        # 状态标签
        self.status_label = QLabel(LanguageManager.get_text('status_ready'))
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 按钮
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton(LanguageManager.get_text('start_extraction'))
        self.start_btn.clicked.connect(self.start_extraction)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton(LanguageManager.get_text('stop'))
        self.stop_btn.clicked.connect(self.stop_extraction)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # 清除和关闭按钮
        btn_layout2 = QHBoxLayout()

        self.clear_btn = QPushButton(LanguageManager.get_text('clear_marks'))
        self.clear_btn.clicked.connect(self.clear_markers)
        btn_layout2.addWidget(self.clear_btn)

        self.close_btn = QPushButton(LanguageManager.get_text('close'))
        self.close_btn.clicked.connect(self.close)
        btn_layout2.addWidget(self.close_btn)

        layout.addLayout(btn_layout2)

        layout.addStretch()

    def clear_markers(self):
        """清除热图上的标记线"""
        # 使用对话框自己的 line_artist 引用
        if self.line_artist is not None:
            try:
                self.line_artist.remove()
                self.line_artist = None
                # 同时清除 extractor 中的引用（如果存在）
                if self.extractor is not None:
                    self.extractor.line_artist = None
                self.plot_engine.canvas.draw_idle()
                self.status_label.setText("状态: 已清除标记线")
            except Exception as e:
                self.logger.error(f"清除标记线失败: {e}")
        else:
            self.status_label.setText("状态: 没有标记线可清除")

    def start_extraction(self):
        """开始提取"""
        if not self.plot_engine or not self.plot_engine.ax.has_data():
            QMessageBox.warning(self, LanguageManager.get_text('warning'), LanguageManager.get_text('plot_heatmap_first'))
            return

        self.extractor = HeatmapProfileExtractor(
            self.plot_engine, self.heatmap_tab, self
        )
        # 设置回调，当 extractor 绘制线条时同步到对话框
        self.extractor.on_line_drawn = self._on_line_drawn
        self.extractor.connect_events()

        self.status_label.setText("状态: 等待在热图上拖拽...")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _on_line_drawn(self, line_artist):
        """当 extractor 绘制线条时的回调"""
        self.line_artist = line_artist

    def stop_extraction(self):
        """停止提取"""
        if self.extractor:
            self.extractor.disconnect_events()
            self.extractor = None

        self.status_label.setText("状态: 就绪")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        """关闭事件"""
        self.stop_extraction()
        event.accept()
