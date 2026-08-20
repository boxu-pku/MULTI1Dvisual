"""AnnotationDialog - 交互式标注工具
参考ImageJ设计，支持鼠标直接在画布上操作标注
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QSpinBox, QDoubleSpinBox,
    QColorDialog, QListWidget, QListWidgetItem, QSplitter,
    QWidget, QCheckBox, QFontDialog, QMessageBox, QFileDialog,
    QFrame, QSlider, QLineEdit, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QFont
import numpy as np

from utils.config import Config
from utils.logger import Logger
from utils.language import LanguageManager


class AnnotationTool:
    """标注工具类，管理单个标注的属性"""

    def __init__(self, tool_type='line', color='#ff0000', linewidth=2.0,
                 linestyle='-', alpha=1.0, fontsize=12, font_family='Arial',
                 text_content='Text'):
        self.tool_type = tool_type
        self.color = color
        self.linewidth = linewidth
        self.linestyle = linestyle
        self.alpha = alpha
        self.fontsize = fontsize
        self.font_family = font_family
        self.text_content = text_content

        # 标注的坐标
        self.start_pos = None  # (x, y) in data coordinates
        self.end_pos = None    # (x, y) in data coordinates

        # matplotlib artist对象
        self.artist = None


class InteractiveAnnotationCanvas:
    """交互式标注画布管理器"""

    def __init__(self, plot_engine, parent=None):
        self.plot_engine = plot_engine
        self.parent = parent
        self.logger = Logger.get_logger('InteractiveAnnotation')

        # 标注工具设置
        self.current_tool = 'line'
        self.current_color = '#ff0000'
        self.current_linewidth = 2.0
        self.current_linestyle = '-'
        self.current_alpha = 1.0
        self.current_fontsize = 12
        self.current_font_family = 'Arial'

        # 标注列表
        self.annotations = []

        # 绘制状态
        self.is_drawing = False
        self.start_pos = None
        self.temp_artist = None

        # 连接鼠标事件
        self.connect_events()

    def connect_events(self):
        """连接鼠标事件"""
        self.press_cid = self.plot_engine.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.release_cid = self.plot_engine.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.motion_cid = self.plot_engine.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

    def disconnect_events(self):
        """断开鼠标事件连接"""
        if hasattr(self, 'press_cid') and self.press_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.press_cid)
            except:
                pass
        if hasattr(self, 'release_cid') and self.release_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.release_cid)
            except:
                pass
        if hasattr(self, 'motion_cid') and self.motion_cid:
            try:
                self.plot_engine.canvas.mpl_disconnect(self.motion_cid)
            except:
                pass
        # 清除临时绘制
        if self.temp_artist:
            try:
                self.temp_artist.remove()
            except:
                pass
            self.temp_artist = None
        self.plot_engine.canvas.draw_idle()

    def on_mouse_press(self, event):
        """鼠标按下事件"""
        if event.inaxes != self.plot_engine.ax:
            return

        if self.current_tool == 'text':
            # 文字工具：直接在点击位置创建文字
            text, ok = QInputDialog.getText(
                self.parent, LanguageManager.get_text('enter_text_title'), LanguageManager.get_text('enter_text_prompt')
            )
            if ok and text:
                self.add_text_annotation(event.xdata, event.ydata, text)
        else:
            # 其他工具：开始绘制
            self.is_drawing = True
            self.start_pos = (event.xdata, event.ydata)

    def on_mouse_release(self, event):
        """鼠标释放事件"""
        if not self.is_drawing or event.inaxes != self.plot_engine.ax:
            self.is_drawing = False
            return

        end_pos = (event.xdata, event.ydata)

        # 根据工具类型创建标注
        if self.current_tool == 'line':
            self.add_line_annotation(self.start_pos, end_pos)
        elif self.current_tool == 'arrow':
            self.add_arrow_annotation(self.start_pos, end_pos)
        elif self.current_tool == 'rectangle':
            self.add_rectangle_annotation(self.start_pos, end_pos)
        elif self.current_tool == 'ellipse':
            self.add_ellipse_annotation(self.start_pos, end_pos)

        self.is_drawing = False
        self.start_pos = None

        # 移除临时绘制对象
        if self.temp_artist:
            try:
                self.temp_artist.remove()
            except:
                pass
            self.temp_artist = None
            self.plot_engine.canvas.draw_idle()

    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.is_drawing or event.inaxes != self.plot_engine.ax:
            return

        # 移除临时对象
        if self.temp_artist:
            try:
                self.temp_artist.remove()
            except:
                pass

        # 绘制临时预览
        end_pos = (event.xdata, event.ydata)

        if self.current_tool == 'line':
            self.temp_artist, = self.plot_engine.ax.plot(
                [self.start_pos[0], end_pos[0]],
                [self.start_pos[1], end_pos[1]],
                color=self.current_color,
                linewidth=self.current_linewidth,
                linestyle=self.current_linestyle,
                alpha=self.current_alpha
            )
        elif self.current_tool == 'arrow':
            self.temp_artist = self.plot_engine.ax.annotate(
                '', xy=end_pos, xytext=self.start_pos,
                arrowprops=dict(
                    arrowstyle='->',
                    color=self.current_color,
                    lw=self.current_linewidth,
                    mutation_scale=15
                )
            )
        elif self.current_tool == 'rectangle':
            from matplotlib.patches import Rectangle
            self.temp_artist = Rectangle(
                (min(self.start_pos[0], end_pos[0]),
                 min(self.start_pos[1], end_pos[1])),
                abs(end_pos[0] - self.start_pos[0]),
                abs(end_pos[1] - self.start_pos[1]),
                fill=False,
                edgecolor=self.current_color,
                linewidth=self.current_linewidth,
                linestyle=self.current_linestyle,
                alpha=self.current_alpha
            )
            self.plot_engine.ax.add_patch(self.temp_artist)
        elif self.current_tool == 'ellipse':
            from matplotlib.patches import Ellipse
            center_x = (self.start_pos[0] + end_pos[0]) / 2
            center_y = (self.start_pos[1] + end_pos[1]) / 2
            width = abs(end_pos[0] - self.start_pos[0])
            height = abs(end_pos[1] - self.start_pos[1])
            self.temp_artist = Ellipse(
                (center_x, center_y), width, height,
                fill=False,
                edgecolor=self.current_color,
                linewidth=self.current_linewidth,
                linestyle=self.current_linestyle,
                alpha=self.current_alpha
            )
            self.plot_engine.ax.add_patch(self.temp_artist)

        self.plot_engine.canvas.draw_idle()

    def add_text_annotation(self, x, y, text):
        """添加文字标注"""
        annotation = AnnotationTool(tool_type='text')
        annotation.start_pos = (x, y)
        annotation.color = self.current_color
        annotation.fontsize = self.current_fontsize
        annotation.font_family = self.current_font_family
        annotation.alpha = self.current_alpha
        annotation.text_content = text

        # 绘制文字
        annotation.artist = self.plot_engine.ax.text(
            x, y, text,
            fontsize=self.current_fontsize,
            color=self.current_color,
            fontfamily=self.current_font_family,
            alpha=self.current_alpha
        )

        self.annotations.append(annotation)
        self.plot_engine.canvas.draw_idle()
        self.logger.info(f"添加文字标注: {text} at ({x:.2f}, {y:.2f})")

    def add_line_annotation(self, start_pos, end_pos):
        """添加直线标注"""
        annotation = AnnotationTool(tool_type='line')
        annotation.start_pos = start_pos
        annotation.end_pos = end_pos
        annotation.color = self.current_color
        annotation.linewidth = self.current_linewidth
        annotation.linestyle = self.current_linestyle
        annotation.alpha = self.current_alpha

        # 绘制直线
        annotation.artist, = self.plot_engine.ax.plot(
            [start_pos[0], end_pos[0]],
            [start_pos[1], end_pos[1]],
            color=self.current_color,
            linewidth=self.current_linewidth,
            linestyle=self.current_linestyle,
            alpha=self.current_alpha
        )

        self.annotations.append(annotation)
        self.plot_engine.canvas.draw_idle()
        self.logger.info(f"添加直线标注: ({start_pos[0]:.2f}, {start_pos[1]:.2f}) -> ({end_pos[0]:.2f}, {end_pos[1]:.2f})")

    def add_arrow_annotation(self, start_pos, end_pos):
        """添加箭头标注"""
        annotation = AnnotationTool(tool_type='arrow')
        annotation.start_pos = start_pos
        annotation.end_pos = end_pos
        annotation.color = self.current_color
        annotation.linewidth = self.current_linewidth
        annotation.alpha = self.current_alpha

        # 绘制箭头
        annotation.artist = self.plot_engine.ax.annotate(
            '', xy=end_pos, xytext=start_pos,
            arrowprops=dict(
                arrowstyle='->',
                color=self.current_color,
                lw=self.current_linewidth,
                mutation_scale=15
            )
        )

        self.annotations.append(annotation)
        self.plot_engine.canvas.draw_idle()
        self.logger.info(f"添加箭头标注: ({start_pos[0]:.2f}, {start_pos[1]:.2f}) -> ({end_pos[0]:.2f}, {end_pos[1]:.2f})")

    def add_rectangle_annotation(self, start_pos, end_pos):
        """添加矩形标注"""
        from matplotlib.patches import Rectangle

        annotation = AnnotationTool(tool_type='rectangle')
        annotation.start_pos = start_pos
        annotation.end_pos = end_pos
        annotation.color = self.current_color
        annotation.linewidth = self.current_linewidth
        annotation.linestyle = self.current_linestyle
        annotation.alpha = self.current_alpha

        # 绘制矩形
        rect = Rectangle(
            (min(start_pos[0], end_pos[0]), min(start_pos[1], end_pos[1])),
            abs(end_pos[0] - start_pos[0]),
            abs(end_pos[1] - start_pos[1]),
            fill=False,
            edgecolor=self.current_color,
            linewidth=self.current_linewidth,
            linestyle=self.current_linestyle,
            alpha=self.current_alpha
        )
        annotation.artist = rect
        self.plot_engine.ax.add_patch(rect)

        self.annotations.append(annotation)
        self.plot_engine.canvas.draw_idle()
        self.logger.info(f"添加矩形标注")

    def add_ellipse_annotation(self, start_pos, end_pos):
        """添加椭圆标注"""
        from matplotlib.patches import Ellipse

        annotation = AnnotationTool(tool_type='ellipse')
        annotation.start_pos = start_pos
        annotation.end_pos = end_pos
        annotation.color = self.current_color
        annotation.linewidth = self.current_linewidth
        annotation.linestyle = self.current_linestyle
        annotation.alpha = self.current_alpha

        # 绘制椭圆
        center_x = (start_pos[0] + end_pos[0]) / 2
        center_y = (start_pos[1] + end_pos[1]) / 2
        width = abs(end_pos[0] - start_pos[0])
        height = abs(end_pos[1] - start_pos[1])
        ellipse = Ellipse(
            (center_x, center_y), width, height,
            fill=False,
            edgecolor=self.current_color,
            linewidth=self.current_linewidth,
            linestyle=self.current_linestyle,
            alpha=self.current_alpha
        )
        annotation.artist = ellipse
        self.plot_engine.ax.add_patch(ellipse)

        self.annotations.append(annotation)
        self.plot_engine.canvas.draw_idle()
        self.logger.info(f"添加椭圆标注")

    def delete_annotation(self, index):
        """删除指定索引的标注"""
        if 0 <= index < len(self.annotations):
            annotation = self.annotations[index]
            if annotation.artist:
                try:
                    annotation.artist.remove()
                except:
                    pass
            del self.annotations[index]
            self.plot_engine.canvas.draw_idle()
            self.logger.info(f"删除标注 #{index}")

    def clear_all(self):
        """清除所有标注"""
        for annotation in self.annotations:
            if annotation.artist:
                try:
                    annotation.artist.remove()
                except:
                    pass
        self.annotations.clear()
        self.plot_engine.canvas.draw_idle()
        self.logger.info("清除所有标注")

    def set_tool(self, tool_type):
        """设置当前工具"""
        self.current_tool = tool_type

    def set_color(self, color):
        """设置当前颜色"""
        self.current_color = color

    def set_linewidth(self, width):
        """设置当前线宽"""
        self.current_linewidth = width

    def set_linestyle(self, style):
        """设置当前线型"""
        self.current_linestyle = style

    def set_alpha(self, alpha):
        """设置当前透明度"""
        self.current_alpha = alpha

    def set_fontsize(self, size):
        """设置当前字号"""
        self.current_fontsize = size

    def set_font_family(self, family):
        """设置当前字体"""
        self.current_font_family = family


class AnnotationDialog(QDialog):
    """标注工具对话框 - 支持交互式标注"""

    # 标注类型 - 将在__init__中根据语言设置
    ANNOTATION_TYPES = {}
    LINESTYLES = {}

    def __init__(self, plot_engine, parent=None):
        super().__init__(parent)
        self.plot_engine = plot_engine
        self.logger = Logger.get_logger('AnnotationDialog')

        # 根据当前语言设置标注类型和线型
        lang = LanguageManager.get_current_language()
        if lang == 'en':
            self.ANNOTATION_TYPES = {
                'line': 'Line',
                'arrow': 'Arrow',
                'rectangle': 'Rectangle',
                'ellipse': 'Ellipse',
                'text': 'Text'
            }
            self.LINESTYLES = {
                '-': 'Solid',
                '--': 'Dashed',
                '-.': 'Dash-dot',
                ':': 'Dotted'
            }
        else:
            self.ANNOTATION_TYPES = {
                'line': '直线',
                'arrow': '箭头',
                'rectangle': '矩形',
                'ellipse': '椭圆',
                'text': '文字'
            }
            self.LINESTYLES = {
                '-': '实线',
                '--': '虚线',
                '-.': '点划线',
                ':': '点线'
            }

        # 创建交互式标注管理器
        self.annotation_canvas = InteractiveAnnotationCanvas(plot_engine, self)

        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(LanguageManager.get_text('annotation_title'))
        self.setMinimumSize(450, 650)
        self.resize(480, 700)

        main_layout = QHBoxLayout(self)

        # 左侧：工具和属性设置
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)

        # 右侧：标注列表
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)

        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 1)

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # === 使用说明 ===
        help_group = QGroupBox(LanguageManager.get_text('instructions'))
        help_layout = QVBoxLayout(help_group)
        help_text = LanguageManager.get_text('annotation_help_en')
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addWidget(help_group)

        # === 工具选择 ===
        tool_group = QGroupBox(LanguageManager.get_text('annotation_tools'))
        tool_layout = QVBoxLayout(tool_group)

        # 工具类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(LanguageManager.get_text('type') + ":"))
        self.tool_combo = QComboBox()
        for key, name in self.ANNOTATION_TYPES.items():
            self.tool_combo.addItem(name, key)
        self.tool_combo.currentIndexChanged.connect(self.on_tool_changed)
        type_layout.addWidget(self.tool_combo)
        tool_layout.addLayout(type_layout)

        layout.addWidget(tool_group)

        # === 线条样式 ===
        line_group = QGroupBox(LanguageManager.get_text('line_style_settings'))
        line_layout = QVBoxLayout(line_group)

        # 颜色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel(LanguageManager.get_text('color') + ":"))
        self.color_btn = QPushButton()
        self.color_btn.setStyleSheet(
            f"background-color: {self.annotation_canvas.current_color}; min-width: 60px; min-height: 25px;"
        )
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        line_layout.addLayout(color_layout)

        # 线宽
        lw_layout = QHBoxLayout()
        lw_layout.addWidget(QLabel(LanguageManager.get_text('line_width') + ":"))
        self.linewidth_spin = QDoubleSpinBox()
        self.linewidth_spin.setRange(0.5, 10.0)
        self.linewidth_spin.setValue(2.0)
        self.linewidth_spin.setSingleStep(0.5)
        self.linewidth_spin.valueChanged.connect(self.on_linewidth_changed)
        lw_layout.addWidget(self.linewidth_spin)
        lw_layout.addStretch()
        line_layout.addLayout(lw_layout)

        # 线型
        ls_layout = QHBoxLayout()
        ls_layout.addWidget(QLabel(LanguageManager.get_text('line_style') + ":"))
        self.linestyle_combo = QComboBox()
        for key, name in self.LINESTYLES.items():
            self.linestyle_combo.addItem(name, key)
        self.linestyle_combo.currentIndexChanged.connect(self.on_linestyle_changed)
        ls_layout.addWidget(self.linestyle_combo)
        ls_layout.addStretch()
        line_layout.addLayout(ls_layout)

        # 透明度
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(QLabel(LanguageManager.get_text('opacity') + ":"))
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(100)
        self.alpha_slider.valueChanged.connect(self.on_alpha_changed)
        alpha_layout.addWidget(self.alpha_slider)
        self.alpha_label = QLabel("100%")
        self.alpha_label.setMinimumWidth(40)
        alpha_layout.addWidget(self.alpha_label)
        line_layout.addLayout(alpha_layout)

        layout.addWidget(line_group)

        # === 文字样式 ===
        self.text_group = QGroupBox(LanguageManager.get_text('text_style'))
        text_layout = QVBoxLayout(self.text_group)

        # 字号
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(LanguageManager.get_text('font_size') + ":"))
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(6, 72)
        self.fontsize_spin.setValue(12)
        self.fontsize_spin.valueChanged.connect(self.on_fontsize_changed)
        font_layout.addWidget(self.fontsize_spin)
        font_layout.addStretch()
        text_layout.addLayout(font_layout)

        # 字体
        font_btn_layout = QHBoxLayout()
        self.font_btn = QPushButton(LanguageManager.get_text('select_font'))
        self.font_btn.clicked.connect(self.choose_font)
        font_btn_layout.addWidget(self.font_btn)
        font_btn_layout.addStretch()
        text_layout.addLayout(font_btn_layout)

        layout.addWidget(self.text_group)
        # 默认隐藏文字样式（当选择文字工具时显示）
        self.text_group.setVisible(False)

        layout.addStretch()

        # === 底部按钮 ===
        bottom_layout = QHBoxLayout()

        self.clear_btn = QPushButton(LanguageManager.get_text('clear_all_annotations'))
        self.clear_btn.clicked.connect(self.clear_all)
        bottom_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton(LanguageManager.get_text('export_annotated_image'))
        self.export_btn.clicked.connect(self.export_annotated)
        bottom_layout.addWidget(self.export_btn)

        layout.addLayout(bottom_layout)

        return panel

    def create_right_panel(self):
        """创建右侧面板（标注列表）"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        list_label = QLabel(LanguageManager.get_text('annotation_list') + ":")
        layout.addWidget(list_label)

        self.annotation_list = QListWidget()
        self.annotation_list.setMinimumHeight(300)
        layout.addWidget(self.annotation_list)

        # 列表操作按钮
        list_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton(LanguageManager.get_text('delete_selected'))
        self.delete_btn.clicked.connect(self.delete_selected)
        list_btn_layout.addWidget(self.delete_btn)

        layout.addLayout(list_btn_layout)

        # 刷新列表按钮
        self.refresh_btn = QPushButton(LanguageManager.get_text('refresh_list'))
        self.refresh_btn.clicked.connect(self.update_list)
        layout.addWidget(self.refresh_btn)

        return panel

    def on_tool_changed(self, index):
        """工具类型改变"""
        tool_type = self.tool_combo.itemData(index)
        self.annotation_canvas.set_tool(tool_type)

        # 显示/隐藏文字样式
        self.text_group.setVisible(tool_type == 'text')

    def choose_color(self):
        """选择颜色"""
        color = QColorDialog.getColor(
            QColor(self.annotation_canvas.current_color),
            self, LanguageManager.get_text('select_color')
        )
        if color.isValid():
            self.annotation_canvas.set_color(color.name())
            self.color_btn.setStyleSheet(
                f"background-color: {color.name()}; min-width: 60px; min-height: 25px;"
            )

    def on_linewidth_changed(self, value):
        """线宽改变"""
        self.annotation_canvas.set_linewidth(value)

    def on_linestyle_changed(self, index):
        """线型改变"""
        linestyle = self.linestyle_combo.itemData(index)
        self.annotation_canvas.set_linestyle(linestyle)

    def on_alpha_changed(self, value):
        """透明度改变"""
        alpha = value / 100.0
        self.annotation_canvas.set_alpha(alpha)
        self.alpha_label.setText(f"{value}%")

    def on_fontsize_changed(self, value):
        """字号改变"""
        self.annotation_canvas.set_fontsize(value)

    def choose_font(self):
        """选择字体"""
        font, ok = QFontDialog.getFont(self)
        if ok:
            self.annotation_canvas.set_font_family(font.family())
            self.fontsize_spin.setValue(font.pointSize())

    def delete_selected(self):
        """删除选中的标注"""
        current_row = self.annotation_list.currentRow()
        if current_row >= 0:
            self.annotation_canvas.delete_annotation(current_row)
            self.update_list()

    def clear_all(self):
        """清除所有标注"""
        if self.annotation_canvas.annotations:
            reply = QMessageBox.question(
                self, LanguageManager.get_text('confirm_clear_title'), LanguageManager.get_text('confirm_clear_all'),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.annotation_canvas.clear_all()
                self.update_list()

    def update_list(self):
        """更新标注列表"""
        self.annotation_list.clear()
        for i, ann in enumerate(self.annotation_canvas.annotations):
            type_name = self.ANNOTATION_TYPES.get(ann.tool_type, ann.tool_type)
            if ann.start_pos:
                item_text = f"#{i+1}: {type_name} ({ann.start_pos[0]:.2f}, {ann.start_pos[1]:.2f})"
            else:
                item_text = f"#{i+1}: {type_name}"
            item = QListWidgetItem(item_text)
            item.setForeground(QColor(ann.color))
            self.annotation_list.addItem(item)

    def export_annotated(self):
        """导出带标注的图片"""
        if not self.plot_engine:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('export_annotated_image_title'), "",
            f"{LanguageManager.get_text('png_files')};;{LanguageManager.get_text('pdf_files')};;{LanguageManager.get_text('svg_files')}"
        )
        if filepath:
            fmt = filepath.split('.')[-1] if '.' in filepath else 'png'
            self.plot_engine.save_figure(filepath, dpi=Config.DEFAULT_SAVE_DPI, format=fmt)
            self.logger.info(f"已导出带标注图片: {filepath}")
            QMessageBox.information(self, LanguageManager.get_text('success'), f"{LanguageManager.get_text('image_exported_to')}:\n{filepath}")

    def closeEvent(self, event):
        """对话框关闭事件"""
        # 断开鼠标事件连接
        if hasattr(self, 'annotation_canvas'):
            self.annotation_canvas.disconnect_events()
        event.accept()
