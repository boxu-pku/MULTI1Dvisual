"""DataManager for MULTI1D Visualizer v2.3

Manages multiple fort.10 / .case / MULTI-IFE fort.10 file instances.
"""

import os
from typing import Dict, Optional, List
from utils.logger import Logger


def _detect_fort10_format(filepath: str) -> str:
    """自动检测 fort.10 格式: 'binary' (标准MULTI1D) 或 'ife' (MULTI-IFE 格式化ASCII)"""
    try:
        with open(filepath, 'rb') as f:
            first_line = f.readline()
        text = first_line.decode('ascii').strip()
        if text.isdigit() and int(text) > 100:
            return 'ife'
    except Exception:
        pass
    return 'binary'


class DataManager:
    """数据管理器，管理多个文件"""

    def __init__(self):
        self._parsers: Dict[str, 'Fort10Parser'] = {}  # {filepath: parser}
        self._active_file: Optional[str] = None       # 当前活动文件路径
        self.logger = Logger.get_logger('DataManager')

    def load_file(self, filepath: str) -> bool:
        """
        加载文件（标准 fort.10 二进制 / .case 十进制 / MULTI-IFE fort.10 文本）

        :param filepath: 文件路径
        :return: 成功与否
        """
        from core.fort10_parser import Fort10Parser
        from core.ascii_parser import ASCIIParser
        from core.ife_parser import IFEParser

        if filepath.lower().endswith('.case'):
            ParserClass = ASCIIParser
        elif filepath.lower().endswith('.fort.10') or os.path.basename(filepath) == 'fort.10':
            fmt = _detect_fort10_format(filepath)
            ParserClass = IFEParser if fmt == 'ife' else Fort10Parser
            self.logger.info(f"检测到 fort.10 格式: {fmt}, 使用 {ParserClass.__name__}")
        else:
            ParserClass = Fort10Parser

        try:
            parser = ParserClass(filepath)
            if parser.parse():
                self._parsers[filepath] = parser
                self._active_file = filepath
                self.logger.info(f"成功加载文件: {filepath}")
                return True
            else:
                self.logger.error(f"解析文件失败: {filepath}")
        except Exception as e:
            self.logger.error(f"加载文件异常: {filepath}, 错误: {e}")
        return False

    def unload_file(self, filepath: str):
        """卸载文件"""
        if filepath in self._parsers:
            del self._parsers[filepath]
            self.logger.info(f"已卸载文件: {filepath}")
            if self._active_file == filepath:
                self._active_file = next(iter(self._parsers), None) if self._parsers else None

    def set_active_file(self, filepath: str):
        """设置当前活动文件"""
        if filepath in self._parsers:
            self._active_file = filepath
            self.logger.info(f"设置活动文件: {filepath}")

    def get_active_parser(self):
        """获取当前活动的解析器"""
        return self._parsers.get(self._active_file)

    def get_file_list(self) -> List[str]:
        """获取已加载的文件列表"""
        return list(self._parsers.keys())

    def get_active_filename(self) -> str:
        """获取当前活动文件名"""
        if self._active_file:
            import os
            return os.path.basename(self._active_file)
        return ""

    def clear_all(self):
        """清空所有加载的文件"""
        self._parsers.clear()
        self._active_file = None
        self.logger.info("已清空所有加载的文件")

    def has_active_file(self) -> bool:
        """检查是否有活动文件"""
        return self._active_file is not None

    def get_parser_by_filename(self, filename: str):
        """根据文件名获取解析器"""
        import os
        for filepath, parser in self._parsers.items():
            if os.path.basename(filepath) == filename:
                return parser
        return None
