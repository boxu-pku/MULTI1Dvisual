"""ShockDetector for MULTI1D Visualizer v2.3

Detects shock wave arrival times from density data.
"""

import numpy as np
from scipy.signal import find_peaks
from typing import Optional, Dict
from utils.config import Config
from utils.logger import Logger


class ShockDetector:
    """冲击波到达时刻检测器"""

    def __init__(self):
        self.logger = Logger.get_logger('ShockDetector')

    @staticmethod
    def detect_arrival_time(
        density_time_series: np.ndarray,
        times: np.ndarray,
        threshold: float = 0.2
    ) -> Optional[float]:
        """
        检测冲击波到达时刻

        :param density_time_series: 密度时间序列
        :param times: 时间数组
        :param threshold: 密度变化阈值 (g/cm³)
        :return: 冲击波到达时间，未检测到返回None
        """
        if len(density_time_series) < 2:
            return None

        # 方法1: 密度突变检测
        density_changes = np.diff(density_time_series)
        shock_indices = np.where(density_changes > threshold)[0]

        if len(shock_indices) > 0:
            first_shock_index = shock_indices[0]
            return times[first_shock_index + 1]

        # 方法2: 峰值检测
        try:
            peaks, _ = find_peaks(density_time_series, height=threshold)
            if len(peaks) > 0:
                return times[peaks[0]]
        except:
            pass

        return None

    def detect_multiple_positions(
        self,
        parser,
        var: str = 'R',
        positions: list = None,
        threshold: float = 0.2
    ) -> Dict[float, float]:
        """
        在多个位置检测冲击波到达时刻

        :param parser: Fort10Parser实例
        :param var: 变量名 (通常用R表示密度)
        :param positions: 要检测的位置列表 (um)
        :param threshold: 密度变化阈值
        :return: {位置: 到达时刻} 字典
        """
        if positions is None:
            positions = Config.DEFAULT_SHOCK_POSITIONS

        grid_pos_um = parser.get_grid_positions(unit='um')
        times_ns = parser.get_time_array(unit='ns')
        data_matrix = parser.get_spatial_data_all_times(var)

        arrival_times = {}

        for pos_um in positions:
            # 找到最近的网格点
            idx = np.argmin(np.abs(grid_pos_um - pos_um))
            actual_pos = grid_pos_um[idx]

            # 提取该位置的密度时间序列
            density_series = data_matrix[:, idx] if idx < data_matrix.shape[1] else data_matrix[:, 0]

            # 检测到达时刻
            arrival_time = self.detect_arrival_time(
                density_series, times_ns, threshold
            )

            if arrival_time is not None:
                arrival_times[actual_pos] = arrival_time
                self.logger.info(f"冲击波到达 {actual_pos:.1f} um 的时刻: {arrival_time:.2f} ns")

        return arrival_times
