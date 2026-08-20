"""Logger utility for MULTI1D Visualizer v2.3.1"""

import logging
import os
import glob
from datetime import datetime


class Logger:
    """日志记录器 - 单例模式，自动保留最近3次运行日志"""

    _instance = None
    _initialized = False
    MAX_LOG_FILES = 3

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls, log_dir: str = None):
        """初始化日志系统"""
        if cls._initialized:
            return

        if log_dir is None:
            # Save logs in a 'logs' directory next to main.py
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(app_dir, 'logs')

        os.makedirs(log_dir, exist_ok=True)

        # Each run gets a unique log file with timestamp
        log_file = os.path.join(
            log_dir,
            f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )

        # Use direct handler setup instead of basicConfig
        # (basicConfig is a no-op if root logger already has handlers)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

        cls._cleanup_old_logs(log_dir)
        cls._initialized = True

    @classmethod
    def _cleanup_old_logs(cls, log_dir: str):
        """Delete old log files, keeping only the most recent MAX_LOG_FILES"""
        pattern = os.path.join(log_dir, 'run_*.log')
        log_files = sorted(glob.glob(pattern))
        if len(log_files) > cls.MAX_LOG_FILES:
            for old_file in log_files[:-cls.MAX_LOG_FILES]:
                try:
                    os.remove(old_file)
                except OSError:
                    pass

    @classmethod
    def get_logger(cls, name: str):
        """获取日志记录器"""
        if not cls._initialized:
            cls.init()
        return logging.getLogger(name)
