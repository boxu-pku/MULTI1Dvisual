"""CodeRecorderDialog - 代码录制工具对话框
提供录制控制界面，生成独立的Python回放脚本
"""

import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from utils.code_recorder import CodeRecorder
from utils.logger import Logger
from utils.language import LanguageManager


class CodeRecorderDialog(QDialog):
    """代码录制工具对话框"""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.logger = Logger.get_logger('CodeRecorderDialog')
        self.recorder = CodeRecorder()

        self.setWindowTitle(LanguageManager.get_text('tool_code_recorder'))
        self.setMinimumSize(380, 280)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        self.setup_ui()
        self._update_ui_state()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 使用说明
        help_group = QGroupBox(LanguageManager.get_text('instructions'))
        help_layout = QVBoxLayout(help_group)
        if LanguageManager.get_current_language() == 'zh':
            help_text = (
                "1. 点击\"开始录制\"后，您的绘图操作将被记录\n"
                "2. 执行各种绘图操作（空间图、时间图、热图等）\n"
                "3. 点击\"停止录制\"结束录制\n"
                "4. 点击\"生成脚本\"将操作保存为Python脚本\n"
                "5. 脚本可在命令行独立运行"
            )
        else:
            help_text = (
                "1. Click \"Start Recording\" to capture your plot operations\n"
                "2. Perform various plot actions (spatial, temporal, heatmap, etc.)\n"
                "3. Click \"Stop Recording\" to end capture\n"
                "4. Click \"Generate Script\" to save as a Python script\n"
                "5. The script can be run independently from command line"
            )
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        layout.addWidget(help_group)

        # 状态标签
        self.status_label = QLabel(LanguageManager.get_text('status_ready'))
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.status_label)

        # 操作计数
        self.count_label = QLabel(f"{LanguageManager.get_text('recorded_operations')}: 0")
        layout.addWidget(self.count_label)

        # 录制控制按钮
        control_layout = QHBoxLayout()

        self.toggle_btn = QPushButton(LanguageManager.get_text('start_recording'))
        self.toggle_btn.setMinimumHeight(35)
        self.toggle_btn.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.toggle_btn)

        layout.addLayout(control_layout)

        # 生成脚本和清除按钮
        action_layout = QHBoxLayout()

        self.generate_btn = QPushButton(LanguageManager.get_text('generate_script'))
        self.generate_btn.setMinimumHeight(32)
        self.generate_btn.clicked.connect(self.generate_script)
        self.generate_btn.setEnabled(False)
        action_layout.addWidget(self.generate_btn)

        self.clear_btn = QPushButton(LanguageManager.get_text('clear_recording'))
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.clicked.connect(self.clear_recording)
        self.clear_btn.setEnabled(False)
        action_layout.addWidget(self.clear_btn)

        layout.addLayout(action_layout)

        layout.addStretch()

    def _update_ui_state(self):
        """更新UI状态"""
        if self.recorder.is_recording:
            self.status_label.setText(LanguageManager.get_text('status_recording'))
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 13px;")
            self.toggle_btn.setText(LanguageManager.get_text('stop_recording'))
            self.generate_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
        else:
            has_ops = self.recorder.operation_count > 0
            if has_ops:
                self.status_label.setText(LanguageManager.get_text('status_stopped_with_data'))
                self.status_label.setStyleSheet("color: #cc6600; font-weight: bold; font-size: 13px;")
            else:
                self.status_label.setText(LanguageManager.get_text('status_ready'))
                self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 13px;")
            self.toggle_btn.setText(LanguageManager.get_text('start_recording'))
            self.generate_btn.setEnabled(has_ops)
            self.clear_btn.setEnabled(has_ops)

        self.count_label.setText(
            f"{LanguageManager.get_text('recorded_operations')}: {self.recorder.operation_count}"
        )

    def update_count(self):
        """更新操作计数（由外部调用）"""
        self.count_label.setText(
            f"{LanguageManager.get_text('recorded_operations')}: {self.recorder.operation_count}"
        )

    def toggle_recording(self):
        """切换录制状态"""
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        else:
            # 开始录制时记录当前文件
            filepath = None
            parser = self.data_manager.get_active_parser()
            if parser and hasattr(parser, 'filepath'):
                filepath = parser.filepath
            self.recorder.start_recording(filepath)

        self._update_ui_state()

    def generate_script(self):
        """生成回放脚本"""
        if self.recorder.operation_count == 0:
            QMessageBox.warning(self, LanguageManager.get_text('warning'),
                              LanguageManager.get_text('no_operations_to_generate'))
            return

        # 确定默认路径
        default_dir = ""
        default_name = "replay_script.py"
        parser = self.data_manager.get_active_parser()
        if parser and hasattr(parser, 'filepath'):
            default_dir = os.path.dirname(parser.filepath)
            base = os.path.splitext(os.path.basename(parser.filepath))[0]
            default_name = f"{base}_replay.py"

        default_path = os.path.join(default_dir, default_name) if default_dir else default_name

        filepath, _ = QFileDialog.getSaveFileName(
            self, LanguageManager.get_text('generate_script'),
            default_path,
            "Python Scripts (*.py);;All Files (*)"
        )

        if filepath:
            try:
                self.recorder.generate_script(filepath)
                QMessageBox.information(
                    self, LanguageManager.get_text('success'),
                    f"{LanguageManager.get_text('script_generated_to')}:\n{filepath}"
                )
                self.logger.info(f"脚本已生成: {filepath}")
            except Exception as e:
                QMessageBox.critical(
                    self, LanguageManager.get_text('error'),
                    f"{LanguageManager.get_text('script_generation_failed')}: {e}"
                )
                self.logger.error(f"脚本生成失败: {e}")

    def clear_recording(self):
        """清除录制记录"""
        self.recorder.clear()
        self._update_ui_state()

    def closeEvent(self, event):
        """关闭事件"""
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        event.accept()
