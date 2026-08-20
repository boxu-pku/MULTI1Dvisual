"""IFEParser for MULTI1D Visualizer v2.3

Parses MULTI-IFE formatted ASCII fort.10 output files.
MULTI-IFE uses formatted (text) I/O instead of standard MULTI1D's
unformatted (binary) I/O, but the variable names and data layout
are similar enough to reuse the entire visualization pipeline.
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple

from core.fort10_parser import Fort10Parser
from utils.logger import Logger


class IFEParser(Fort10Parser):
    """
    MULTI-IFE 格式化 ASCII fort.10 解析器

    文件结构（每节 = count + N×labels + N×indices + N×values）:
      节1: 时间无关数据（CMC, NC, CMI, NI, FREC, FREI, N=463）
      节2: 时间相关数据（每步 47 个变量, N=1990），步数不限
    """

    # 非物理量：质量坐标 CMC/CMI；MULTI-IFE 里 PE/PI 已被 PT 合并掉（保留 PT）
    # XC/X 保留：cell-mode 下画"cell N 位置随时间"，与二进制 fort.10 一致
    NON_PHYSICAL_VARS = {'CMC', 'CMI', 'PE', 'PI'}

    def __init__(self, filepath: str):
        super().__init__(filepath)
        self.logger = Logger.get_logger('IFEParser')

    def parse(self) -> bool:
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            lines = [line.rstrip('\n\r') for line in lines]

            idx = 0
            count1 = int(lines[idx].strip()); idx += 1
            labels1 = [lines[idx + i].strip() for i in range(count1)]; idx += count1
            idx += count1  # skip indices
            values1 = [self._parse_float(lines[idx + i]) for i in range(count1)]; idx += count1

            self.first_dict = {}
            for var_name, vals in _group_by_label(labels1, values1).items():
                self.first_dict[var_name.ljust(8)] = np.asarray(vals, dtype=float)

            self.second_dict = []
            while idx < len(lines):
                s = lines[idx].strip()
                if not s:
                    idx += 1
                    continue
                count2 = int(s); idx += 1
                labels2 = [lines[idx + i].strip() for i in range(count2)]; idx += count2
                idx += count2  # skip indices
                values2 = [self._parse_float(lines[idx + i]) for i in range(count2)]; idx += count2

                step_data = {}
                for var_name, vals in _group_by_label(labels2, values2).items():
                    step_data[var_name.ljust(8)] = np.asarray(vals, dtype=float)
                self.second_dict.append(step_data)

            if not self.second_dict:
                self.logger.error("未找到时间相关数据")
                return False

            n_times = len(self.second_dict)
            self.logger.info(
                f"MULTI-IFE fort.10 解析成功: {n_times} 时间步, "
                f"{len(self.second_dict[0])} 变量"
            )

            self._extract_metadata()
            self._loaded = True
            return True

        except Exception as e:
            self.logger.error(f"IFE 解析失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _parse_float(self, s: str) -> float:
        s = s.strip()
        if not s:
            return float('nan')
        s = s.replace('D', 'E').replace('d', 'e')
        if 'E' not in s and ('+' in s[1:] or '-' in s[1:]):
            for i, ch in enumerate(s):
                if ch in '+-' and i > 0:
                    s = s[:i] + 'E' + s[i:]
                    break
        return float(s)

    def get_available_spatial_vars(self) -> List[str]:
        vars_list = super().get_available_spatial_vars()
        return [v for v in vars_list if v not in self.NON_PHYSICAL_VARS]

    def get_available_time_vars(self) -> List[str]:
        if not self._loaded or not self.second_dict:
            return []
        time_vars = []
        for key in self.second_dict[0].keys():
            stripped = key.strip()
            if stripped == 'TIME':
                continue
            data = self.second_dict[0][key]
            if isinstance(data, np.ndarray) and data.size <= 1:
                time_vars.append(stripped)
            elif isinstance(data, (list, tuple)) and len(data) <= 1:
                time_vars.append(stripped)
        return time_vars

    def __str__(self):
        return f"IFEParser: {self.filepath}\n" \
               f"  时间步数: {self._n_timesteps}\n" \
               f"  网格数: {self._n_cells}\n" \
               f"  已加载: {self._loaded}"


def _group_by_label(labels: List[str], values: List[float]) -> Dict[str, list]:
    """将连续重复标签的值分组为 {变量名: [值列表]}"""
    result: Dict[str, list] = {}
    i = 0
    n = len(labels)
    while i < n:
        label = labels[i]
        j = i
        while j < n and labels[j] == label:
            j += 1
        result[label] = values[i:j]
        i = j
    return result
