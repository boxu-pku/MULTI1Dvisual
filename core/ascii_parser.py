"""ASCIIParser for MULTI1D Visualizer v2.3

Parses MULTI1D decimal ASCII output files (.case + .dat files)
and converts to the same (first_dict, second_dict) format as Fort10Parser,
enabling full reuse of the existing visualization pipeline.
"""

import os
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

from core.fort10_parser import Fort10Parser
from utils.logger import Logger


class ASCIIParser(Fort10Parser):
    """
    MULTI1D 十进制 ASCII 文件解析器

    读取 .case 文件作为入口，自动匹配同根名的 .dat 数据文件：
      - *.scalars.dat  → 全局标量时间序列
      - *.center.dat   → 网格质心量（每时间步 N 行）
      - *.interface.dat → 网格边界量（每时间步 N+1 行）
      - *.group.dat    → 辐射群量（每时间步 1 行）

    将上述数据重塑为标准 (first_dict, second_dict) 格式，
    与 Fort10Parser 完全兼容，可无缝复用所有现有功能。
    """

    # ASCII 特有的非物理量变量（质量坐标参考，不应出现在变量选择列表）
    # XC/X 保留：cell-mode 下画"cell N 位置随时间"对拉氏跟踪有用，与二进制 fort.10 行为一致
    NON_PHYSICAL_VARS = {'CMC', 'CMI'}
    # &LAYERS 段后面的 section 标记（用于截取 section 边界）
    _NEXT_SECTION_MARKERS = ('&RBOUND', '&PULSE', '&CONTROL', '&MATERIAL',
                             '&OPACITY', '&EOS', '&PROBE', '&END')

    def __init__(self, filepath: str):
        super().__init__(filepath)
        self.logger = Logger.get_logger('ASCIIParser')

    def parse(self) -> bool:
        try:
            root = re.sub(r'\.case$', '', self.filepath, flags=re.IGNORECASE)

            scalar_file = root + '.scalars.dat'
            center_file = root + '.center.dat'
            interface_file = root + '.interface.dat'
            group_file = root + '.group.dat'

            if not os.path.isfile(scalar_file):
                self.logger.error(f"找不到标量文件: {scalar_file}")
                return False
            if not os.path.isfile(center_file):
                self.logger.error(f"找不到中心数据文件: {center_file}")
                return False

            scalars_df = self._read_dat_file(scalar_file)
            center_df = self._read_dat_file(center_file)
            interface_df = self._read_dat_file(interface_file) if os.path.isfile(interface_file) else None
            group_df = self._read_dat_file(group_file) if os.path.isfile(group_file) else None

            n_timesteps = len(scalars_df)
            n_cells = self._infer_n_cells(center_df, n_timesteps)

            center_arrays = self._extract_center_arrays(center_df, n_timesteps, n_cells)
            interface_arrays = self._extract_interface_arrays(interface_df, n_timesteps, n_cells) if interface_df is not None else {}
            group_arrays = self._extract_group_arrays(group_df, n_timesteps) if group_df is not None else {}
            scalar_arrays = self._extract_scalar_arrays(scalars_df, n_timesteps)

            self.first_dict = {}
            self.second_dict = []

            for t in range(n_timesteps):
                step_data = {}
                for var_name, arr in center_arrays.items():
                    if var_name in ('TIME', 'MID'):
                        continue
                    if t < arr.shape[0]:
                        step_data[var_name.ljust(8)] = arr[t]
                for var_name, arr in interface_arrays.items():
                    if t < arr.shape[0]:
                        step_data[var_name.ljust(8)] = arr[t]
                for var_name, arr in group_arrays.items():
                    if t < arr.shape[0]:
                        step_data[var_name.ljust(8)] = arr[t]
                for var_name, arr in scalar_arrays.items():
                    if t < arr.shape[0]:
                        step_data[var_name.ljust(8)] = np.array([arr[t]], dtype=float)
                step_data['TIME    '] = np.array([center_arrays['TIME'][t]], dtype=float)
                self.second_dict.append(step_data)

            first_step = self.second_dict[0]
            for key in ('CMC', 'CMI', 'NC', 'NI'):
                padded = key.ljust(8)
                if padded in first_step:
                    self.first_dict[padded] = np.asarray(first_step[padded], dtype=float)

            # MID (time-invariant 材料标识码，来自 center.dat 的 MID 列)
            if 'MID' in center_arrays:
                self.first_dict['MID     '] = np.asarray(center_arrays['MID'], dtype=float)

            # 解析 .case &LAYERS 段，建立 {MID: 材料名} 映射
            self._material_map = self._parse_material_map()

            self._extract_metadata()
            self._loaded = True
            return True

        except Exception as e:
            self.logger.error(f"ASCII 解析失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _read_dat_file(self, filepath: str) -> pd.DataFrame:
        """读取 tab 分隔的 .dat 文件，自动检测表头行"""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        header_idx = None
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith('#') and re.search(r'#\s*TIME', stripped, re.IGNORECASE):
                header_idx = i

        if header_idx is None:
            raise ValueError(f"无法在 {filepath} 中找到列头行")

        header_line = lines[header_idx].lstrip('#').strip()
        columns = header_line.split('\t')
        columns = [c.strip() for c in columns if c.strip()]

        data_lines = []
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                data_lines.append(stripped)

        if not data_lines:
            return pd.DataFrame(columns=columns)

        rows = [line.split('\t') for line in data_lines]
        df = pd.DataFrame(rows, columns=columns)
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def _find_time_column(self, df: pd.DataFrame) -> str:
        for col in df.columns:
            s = col.strip().lstrip('#').upper()
            if s == 'TIME':
                return col
        return df.columns[0]

    def _infer_n_cells(self, center_df: pd.DataFrame, n_timesteps: int) -> int:
        if n_timesteps == 0:
            return 0
        return len(center_df) // n_timesteps

    def _extract_center_arrays(self, df: pd.DataFrame, n_times: int, n_cells: int) -> Dict[str, np.ndarray]:
        """提取中心数据并重塑为 (n_times, n_cells) 的 2D 数组。
        MID 是 time-invariant，单独存为 1D per-cell 数组。"""
        time_col = self._find_time_column(df)
        data_cols = [c for c in df.columns if c != time_col]

        arrays = {}

        for col in data_cols:
            raw = col.strip()
            if raw == 'MID':
                values = df[col].values.astype(float)
                values = values[:n_times * n_cells]
                # MID 在所有时间步相同，取第 0 步作为 per-cell 1D 数组
                arrays['MID'] = values.reshape(n_times, n_cells)[0].copy()
                continue
            if raw == 'Index' or raw.startswith('dln'):
                continue
            if raw == 'TR_cell':
                raw = 'TR'

            values = df[col].values.astype(float)
            values = values[:n_times * n_cells]
            arrays[raw] = values.reshape(n_times, n_cells).copy()

        time_vals = df[time_col].values.astype(float)
        time_vals = time_vals[:n_times * n_cells:n_cells]
        arrays['TIME'] = time_vals

        return arrays

    def _parse_material_map(self) -> Dict[int, str]:
        """解析 .case 文件的 &LAYERS 段，返回 {MID: 材料名} 映射。
        每层有 Name(i)=... 和 MID(i)=... 配对，同一 MID 可出现在多层（如
        两层 Aluminum），但材料名一致，映射无冲突。"""
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            return {}

        idx = content.find('&LAYERS')
        if idx == -1:
            return {}

        # 找到下一个 section 标记作为 &LAYERS 的结束
        end = len(content)
        for marker in self._NEXT_SECTION_MARKERS:
            pos = content.find(marker, idx + 1)
            if pos != -1 and pos < end:
                end = pos
        section = content[idx:end]

        names = {}
        for m in re.finditer(r'Name\((\d+)\)\s*=\s*(\S+)', section):
            names[int(m.group(1))] = m.group(2).strip()

        material_map = {}
        for m in re.finditer(r'MID\((\d+)\)\s*=\s*(\d+)', section):
            layer = int(m.group(1))
            mid_code = int(m.group(2))
            if layer in names:
                material_map[mid_code] = names[layer]

        if material_map:
            self.logger.info(f"解析到 {len(material_map)} 种材料: {material_map}")
        return material_map

    def _extract_interface_arrays(self, df: pd.DataFrame, n_times: int, n_cells: int) -> Dict[str, np.ndarray]:
        if df is None or df.empty:
            return {}
        n_iface = n_cells + 1
        time_col = self._find_time_column(df)
        data_cols = [c for c in df.columns if c != time_col]

        arrays = {}
        for col in data_cols:
            raw = col.strip()
            values = df[col].values.astype(float)
            values = values[:n_times * n_iface]
            arrays[raw] = values.reshape(n_times, n_iface).copy()

        return arrays

    def _extract_group_arrays(self, df: pd.DataFrame, n_times: int) -> Dict[str, np.ndarray]:
        if df is None or df.empty:
            return {}
        time_col = self._find_time_column(df)
        data_cols = [c for c in df.columns if c != time_col]

        arrays = {}
        for col in data_cols:
            raw = col.strip()
            values = df[col].values.astype(float)[:n_times]
            ng = max(values.size // n_times, 1)
            arrays[raw] = values.reshape(n_times, ng)

        return arrays

    def _extract_scalar_arrays(self, df: pd.DataFrame, n_times: int) -> Dict[str, np.ndarray]:
        time_col = self._find_time_column(df)
        data_cols = [c for c in df.columns if c != time_col]

        rename_map = {
            'MaxDrho@': 'MaxDrho', 'MaxDTr@': 'MaxDTr',
            'MaxDPressure@': 'MaxDPressure', 'MaxRho@': 'MaxRho',
            'MaxTr@': 'MaxTr', 'MaxPressure@': 'MaxPressure',
            'MaxDeposition@': 'MaxDeposition',
        }

        arrays = {}
        for col in data_cols:
            raw = col.strip()
            var_name = rename_map.get(raw, raw)
            values = df[col].values.astype(float)[:n_times]
            arrays[var_name] = values

        return arrays

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
        return f"ASCIIParser: {self.filepath}\n" \
               f"  时间步数: {self._n_timesteps}\n" \
               f"  网格数: {self._n_cells}\n" \
               f"  已加载: {self._loaded}"
