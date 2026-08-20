"""IFEParser for MULTI1D Visualizer v2.3.1

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

            # 统一转成非空 token 序列（每行一个 label/index/value，空行跳过）
            tokens = [t for t in (l.strip() for l in lines) if t]

            # ===== 第一节（时间无关数据）=====
            p = 0
            count1 = int(tokens[p]); p += 1
            labels1 = tokens[p:p + count1]; p += count1
            p += count1  # skip indices
            values1 = [self._parse_float(t) for t in tokens[p:p + count1]]; p += count1

            self.first_dict = {}
            for var_name, vals in _group_by_label(labels1, values1).items():
                self.first_dict[var_name.ljust(8)] = np.asarray(vals, dtype=float)

            # ===== 第二节表头（计数 + 变量名 + 索引）=====
            count2 = int(tokens[p]); p += 1
            labels2 = tokens[p:p + count2]; p += count2
            p += count2  # skip indices

            # 变量名 → 列区间（名字连续重复，一次分组供所有记录复用）
            var_ranges = []
            i = 0
            while i < count2:
                j = i
                while j < count2 and labels2[j] == labels2[i]:
                    j += 1
                var_ranges.append((labels2[i].ljust(8), i, j))
                i = j

            # ===== 第二节记录：兼容两种 fort.10 布局 =====
            # A) 逐记录表头：每条记录前重复 count+labels+indices（原实现假设的布局）
            # B) 流式输出：表头只写一次，随后所有记录的值连续输出、每行一个
            #    （r94/MULTI-IFE-2015 m150304.f95 write_output_record 的实际行为）
            # 判据：首条记录的 count2 个值之后，下一个 token 若是纯整数且等于
            # count2，说明又出现一个完整表头 → 布局 A；否则视为布局 B。
            rest = tokens[p:]
            self.second_dict = []
            if len(rest) > count2 and rest[count2].lstrip('+-').isdigit() \
                    and int(rest[count2]) == count2:
                # 布局 A：逐记录表头。首个表头已在上面消费，rest 开头是
                # 首条记录的值；之后每条记录重复 count+labels+indices+values。
                self.second_dict.append(
                    self._build_record(var_ranges, rest[:count2]))
                q = count2
                while q < len(rest):
                    cnt = int(rest[q]); q += 1
                    if cnt != count2:
                        raise ValueError(f'记录表头计数 {cnt} != {count2}')
                    q += 2 * cnt  # labels + indices
                    vals = rest[q:q + cnt]; q += cnt
                    if len(vals) < cnt:
                        raise ValueError('文件在记录中间意外结束')
                    self.second_dict.append(self._build_record(var_ranges, vals))
            else:
                # 布局 B：流式输出
                if len(rest) % count2 != 0:
                    raise ValueError(
                        f'流式布局 token 数 {len(rest)} 不是每记录 {count2} 个的整数倍')
                for r in range(len(rest) // count2):
                    vals = rest[r * count2:(r + 1) * count2]
                    self.second_dict.append(self._build_record(var_ranges, vals))

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

    def _build_record(self, var_ranges, vals):
        """按 var_ranges 把一条记录的值切成 {变量名: 数组} 字典"""
        d = {}
        for name, i0, i1 in var_ranges:
            d[name] = np.asarray(
                [self._parse_float(v) for v in vals[i0:i1]], dtype=float)
        return d

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
