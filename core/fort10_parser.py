"""Fort10Parser for MULTI1D Visualizer v2.3.1

Parses fort.10 binary files from MULTI1D simulation.
"""

import sys
import os
import numpy as np
from typing import Dict, List, Optional, Tuple

from utils.logger import Logger

# 添加legacy目录和项目根目录到路径以导入scanFile
_legacy_path = os.path.join(os.path.dirname(__file__), '..', 'legacy')
_root_path = os.path.join(os.path.dirname(__file__), '..', '..')
if _legacy_path not in sys.path:
    sys.path.insert(0, _legacy_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)


class Fort10Parser:
    """
    fort.10二进制文件解析器

    数据结构:
    - firstDict: 时间无关数据 (dict)
    - secondDict: 时间相关数据 (list of dict)，每个元素对应一个时间步
    """

    # 空间变量列表 (排除X和TIME)
    SPATIAL_VARS = ['XC', 'DENE', 'EE', 'EI', 'P', 'PT', 'R', 'T',
                    'TI', 'ZI', 'TR', 'V', 'D', 'EA', 'F', 'X',
                    'S', 'S+', 'S-']

    # 时间变量列表 (全局量)
    TIME_VARS = ['ENIE', 'ENII', 'ENKI', 'ENLAS', 'ENQUE', 'EALFA',
                'ENAG', 'ENAL', 'ENRAD', 'EYIELD', 'I-Left', 'I-Right',
                'ENRG1', 'ENRG2', 'ENRG3', 'ENRG4',
                'ENRL1', 'ENRL2', 'ENRL3', 'ENRL4']

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.first_dict: Optional[Dict] = None      # 时间无关数据
        self.second_dict: Optional[List[Dict]] = None  # 时间相关数据
        self._times: Optional[np.ndarray] = None     # 时间数组 (s)
        self._grid_positions: Optional[np.ndarray] = None  # 默认网格位置 (cm)
        self._grid_positions_xc: Optional[np.ndarray] = None  # XC 质心坐标 (cm)
        self._grid_positions_x: Optional[np.ndarray] = None   # X 网格边界坐标 (cm)
        # 拉格朗日质量坐标（time-invariant，来自 first_dict）
        self._grid_positions_cmc: Optional[np.ndarray] = None  # CMC cell-center mass coord
        self._grid_positions_cmi: Optional[np.ndarray] = None  # CMI cell-edge mass coord
        # cell/interface 编号（time-invariant 整数标签）
        self._grid_positions_nc: Optional[np.ndarray] = None   # NC cell number 1..N
        self._grid_positions_ni: Optional[np.ndarray] = None   # NI interface number 1..N+1
        # 真正的拉格朗日坐标（time-invariant，初始位置，来自第0步 XC/X）
        self._grid_positions_lc: Optional[np.ndarray] = None   # LC initial cell-center (cm)
        self._grid_positions_li: Optional[np.ndarray] = None   # LI initial interface (cm)
        self._n_timesteps: int = 0                 # 时间步数
        self._n_cells: int = 0                     # 网格数
        self._loaded: bool = False
        self._material_map: Dict[int, str] = {}    # {MID: 材料名}，仅 ASCII .case 有
        self.logger = Logger.get_logger('Fort10Parser')

    def parse(self) -> bool:
        """解析fort.10文件，返回成功与否"""
        try:
            from scanFile import readFileContents
            self.first_dict, self.second_dict = readFileContents(self.filepath)
            self._extract_metadata()
            self._loaded = True
            return True
        except Exception as e:
            print(f"解析失败: {e}")
            return False

    def _extract_metadata(self):
        """提取元数据：时间数组、网格位置等"""
        # 提取时间数组
        self._times = np.array([d['TIME    '][0] for d in self.second_dict])
        self._n_timesteps = len(self._times)

        # 提取并存储两套坐标（均可用时）
        if 'XC      ' in self.second_dict[0]:
            self._grid_positions_xc = np.array(self.second_dict[0]['XC      '])
        if 'X       ' in self.second_dict[0]:
            self._grid_positions_x = np.array(self.second_dict[0]['X       '])

        # 默认网格位置优先使用XC（保持向后兼容）
        if self._grid_positions_xc is not None:
            self._grid_positions = self._grid_positions_xc
        elif self._grid_positions_x is not None:
            self._grid_positions = self._grid_positions_x
        else:
            first_key = list(self.second_dict[0].keys())[0]
            self._grid_positions = np.arange(len(self.second_dict[0][first_key]))

        self._n_cells = len(self._grid_positions)

        # 拉格朗日质量坐标（time-invariant，来自 first_dict）
        # CMC: 累积质量坐标在 cell center；CMI: 在 cell interface（比 CMC 多一个值）
        # NC/NI: cell/interface 编号（1..N），整数标签，作为拉氏坐标的"格子号"版本
        if self.first_dict is not None:
            if 'CMC     ' in self.first_dict:
                self._grid_positions_cmc = np.array(self.first_dict['CMC     '])
            if 'CMI     ' in self.first_dict:
                self._grid_positions_cmi = np.array(self.first_dict['CMI     '])
            if 'NC      ' in self.first_dict:
                self._grid_positions_nc = np.array(self.first_dict['NC      '])
            if 'NI      ' in self.first_dict:
                self._grid_positions_ni = np.array(self.first_dict['NI      '])

        # 真正的拉格朗日坐标（time-invariant，以 um 为物理单位）：
        # LC = XC from timestep 0（初始位置，cell-center）
        # LI = X  from timestep 0（初始位置，interface）
        if self._grid_positions_xc is not None:
            self._grid_positions_lc = self._grid_positions_xc.copy()
        else:
            self._grid_positions_lc = None
        if self._grid_positions_x is not None:
            self._grid_positions_li = self._grid_positions_x.copy()
        else:
            self._grid_positions_li = None

    # ========== 数据访问接口 ==========

    def get_time_array(self, unit: str = 's') -> np.ndarray:
        """
        获取时间数组
        :param unit: 时间单位 's'(秒) 或 'ns'(纳秒)
        """
        if self._times is None:
            return np.array([])
        if unit == 'ns':
            return self._times * 1e9
        return self._times

    def get_grid_positions(self, unit: str = 'cm', coord_system: str = 'XC',
                           time_idx: int = None) -> np.ndarray:
        """
        获取网格位置数组
        :param unit: 位置单位；
                     - 欧拉 XC/X：'cm'(厘米) / 'um'(微米，×1e4)
                     - 拉氏 CMC/CMI：'g/cm^2'(原值) / 'g·um/cm³'(×1e4，um 等效)
                     - 拉氏 NC/NI：纯整数编号，单位参数忽略
        :param coord_system: 'XC'/'X' (欧拉)；
                              'CMC'/'CMI' (质量坐标, 拉氏)；
                              'NC'/'NI' (cell/interface 编号, 拉氏)
        :param time_idx: 时间步索引；欧拉下指定时从该步读取（拉格朗日网格每步不同），
                         拉氏下忽略（CMC/CMI/NC/NI 都是 time-invariant）
        """
        # 拉氏质量坐标：time-invariant。原值是 g/cm²（cm 等效）。
        # 当 unit='g·um/cm³' 时 ×1e4，与 XC 的 um 换算保持一致。
        if coord_system == 'CMC':
            if self._grid_positions_cmc is None:
                return np.array([])
            pos = self._grid_positions_cmc
            if unit == 'g·um/cm³':
                return pos * 1e4
            return pos  # 'g/cm^2' 或其他未识别的原值返回
        if coord_system == 'CMI':
            if self._grid_positions_cmi is None:
                return np.array([])
            pos = self._grid_positions_cmi
            if unit == 'g·um/cm³':
                return pos * 1e4
            return pos
        # cell/interface 编号：time-invariant，整数标签，无单位换算
        if coord_system == 'NC':
            if self._grid_positions_nc is None:
                return np.array([])
            return self._grid_positions_nc
        if coord_system == 'NI':
            if self._grid_positions_ni is None:
                return np.array([])
            return self._grid_positions_ni

        # 真正拉格朗日坐标（time-invariant，初始位置，cm 或 um）
        if coord_system == 'LC':
            if self._grid_positions_lc is None:
                return np.array([])
            pos = self._grid_positions_lc
            return pos * 1e4 if unit == 'um' else pos
        if coord_system == 'LI':
            if self._grid_positions_li is None:
                return np.array([])
            pos = self._grid_positions_li
            return pos * 1e4 if unit == 'um' else pos

        # 欧拉坐标（XC / X）：随时间变化，需要 time_idx
        if time_idx is not None and time_idx < self._n_timesteps:
            # 从指定时间步读取该步的坐标
            key_xc = 'XC      '
            key_x = 'X       '
            if coord_system == 'X' and key_x in self.second_dict[time_idx]:
                positions = np.array(self.second_dict[time_idx][key_x])
            elif key_xc in self.second_dict[time_idx]:
                positions = np.array(self.second_dict[time_idx][key_xc])
            else:
                positions = self._grid_positions
        else:
            # 使用存储的默认坐标（第0步）
            if coord_system == 'X' and self._grid_positions_x is not None:
                positions = self._grid_positions_x
            else:
                positions = self._grid_positions
        if positions is None:
            return np.array([])
        if unit == 'um':
            return positions * 1e4
        return positions

    def get_available_coord_systems(self) -> List[str]:
        """返回可用的坐标系列表，如 ['XC', 'X', 'CMC', 'CMI', 'NC', 'NI']"""
        systems = []
        if self._grid_positions_xc is not None:
            systems.append('XC')
        if self._grid_positions_x is not None:
            systems.append('X')
        if self._grid_positions_cmc is not None:
            systems.append('CMC')
        if self._grid_positions_cmi is not None:
            systems.append('CMI')
        if self._grid_positions_nc is not None:
            systems.append('NC')
        if self._grid_positions_ni is not None:
            systems.append('NI')
        if self._grid_positions_lc is not None:
            systems.append('LC')
        if self._grid_positions_li is not None:
            systems.append('LI')
        return systems

    def get_material_ids(self) -> Optional[np.ndarray]:
        """返回每个网格的 材料标识码（MID），shape=(n_cells,)。
        仅 ASCII .case 格式可用；二进制 fort.10 无此数据，返回 None。"""
        if self.first_dict is not None and 'MID     ' in self.first_dict:
            return np.asarray(self.first_dict['MID     '], dtype=int)
        return None

    def get_material_map(self) -> Dict[int, str]:
        """返回 {MID: 材料名} 映射（来自 .case &LAYERS 段）。
        二进制格式返回空 dict。"""
        return getattr(self, '_material_map', {})

    def get_n_timesteps(self) -> int:
        """获取时间步数"""
        return self._n_timesteps

    def get_n_cells(self) -> int:
        """获取网格数"""
        return self._n_cells

    def is_loaded(self) -> bool:
        """检查是否已加载数据"""
        return self._loaded

    # ========== 空间数据 ==========

    def get_spatial_data(self, var: str, time_idx: int, coord_system: str = 'XC') -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        获取指定变量在指定时刻的空间分布

        :param var: 变量名 (如 'R', 'T', 'P' 等)
        :param time_idx: 时间步索引 (0-based)
        :param coord_system: 坐标系 'XC'(质心) 或 'X'(网格边界)
        :return: (grid_positions, values) 或 None
        """
        if not self._loaded or time_idx >= self._n_timesteps:
            return None

        # 变量名需要8字节对齐，填充空格
        var_padded = var.ljust(8)

        if var_padded in self.second_dict[time_idx]:
            values = np.array(self.second_dict[time_idx][var_padded])
            # 使用该时间步自己的坐标（拉格朗日网格每步不同）
            grid = self.get_grid_positions(unit='cm', coord_system=coord_system,
                                           time_idx=time_idx)
            # 处理可能的长度不一致
            actual_len = min(len(grid), len(values))
            return grid[:actual_len], values[:actual_len]
        return None

    def get_spatial_data_all_times(self, var: str) -> np.ndarray:
        """
        获取指定变量在所有时刻的空间分布 (用于热图)

        :param var: 变量名
        :return: (n_timesteps, n_cells) 形状的数组
        """
        if not self._loaded:
            return np.array([])

        var_padded = var.ljust(8)
        data_matrix = []

        for d in self.second_dict:
            if var_padded in d:
                data_matrix.append(np.array(d[var_padded]))
            else:
                # 如果该变量不存在，添加空数组
                data_matrix.append(np.zeros(self._n_cells))

        if data_matrix:
            # 对齐长度（取最小长度）
            min_len = min(len(arr) for arr in data_matrix)
            aligned_data = [arr[:min_len] for arr in data_matrix]
            return np.array(aligned_data)

        return np.array([])

    # ========== 时间序列数据 ==========

    def get_time_series_at_cell(self, var: str, cell_idx: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        获取指定变量在指定网格上的时间序列

        :param var: 变量名
        :param cell_idx: 网格索引
        :return: (times, values) 或 None
        """
        if not self._loaded or cell_idx >= self._n_cells:
            return None

        var_padded = var.ljust(8)
        values = []

        for d in self.second_dict:
            if var_padded in d:
                if cell_idx < len(d[var_padded]):
                    values.append(d[var_padded][cell_idx])
                else:
                    values.append(np.nan)

        if len(values) == self._n_timesteps:
            return self._times, np.array(values)
        return None

    def get_time_series_global(self, var: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        获取全局时间变量（每个时刻一个标量值）

        :param var: 变量名（如 'ENIE', 'ENII' 等真标量；或 I-Left/I-Right 在 NG=1 时）
        :return: (times, values) 或 None

        注意：对多群变量（I-Left/I-Right 当 NG>1 时每步是 NG 维向量），本函数会
        在 NG=1 时按原逻辑返回；在 NG>1 时把每步的多群向量**求和**当成"总通量"返回，
        并 log warning。要拿完整的多群矩阵请用 get_boundary_spectrum()。
        """
        if not self._loaded:
            return None

        var_padded = var.ljust(8)
        values = []

        # 先探测每步长度，识别多群变量
        per_step_len = 1
        for d in self.second_dict:
            if var_padded in d:
                per_step_len = max(per_step_len, len(d[var_padded]))
                if per_step_len > 1:
                    break  # 发现多群就够，不需要继续

        is_multi_group = per_step_len > 1
        if is_multi_group:
            self.logger.warning(
                f"变量 {var!r} 每步有 {per_step_len} 个值（多群），"
                f"get_time_series_global 返回每步求和（总通量）。"
                f"如需完整 spectrum，请用 get_boundary_spectrum()。"
            )

        for d in self.second_dict:
            if var_padded in d:
                arr = np.asarray(d[var_padded], dtype=float)
                if arr.size == 0:
                    values.append(np.nan)
                elif is_multi_group:
                    values.append(float(np.nansum(arr)))
                else:
                    values.append(float(arr[0]))
            else:
                values.append(np.nan)

        if len(values) == self._n_timesteps:
            return self._times, np.array(values)
        return None

    def get_boundary_spectrum(self, var: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        获取边界辐射谱（多群）的完整 (时间 × 频率) 矩阵

        :param var: 'I-Left' 或 'I-Right'
        :return: (times, freq_centers, matrix) 或 None；
                 matrix.shape = (n_times, NG)；freq_centers 来自 FREC（NG 个）
        """
        if not self._loaded:
            return None

        var_padded = var.ljust(8)
        if self.first_dict is None or 'FREC    ' not in self.first_dict:
            self.logger.warning("缺少 FREC（辐射群结构），无法构建 spectrum")
            return None

        freq_centers = np.asarray(self.first_dict['FREC    '], dtype=float)
        ng = len(freq_centers)

        # 构建 (n_times, NG) 矩阵
        rows = []
        for d in self.second_dict:
            if var_padded in d:
                arr = np.asarray(d[var_padded], dtype=float)
                # 期望长度 == ng；不足补 NaN，多余截断
                if arr.size >= ng:
                    rows.append(arr[:ng])
                else:
                    padded = np.full(ng, np.nan)
                    padded[:arr.size] = arr
                    rows.append(padded)
            else:
                rows.append(np.full(ng, np.nan))

        matrix = np.array(rows)  # shape (n_times, NG)
        return self._times, freq_centers, matrix

    # ========== 变量列表 ==========

    def get_available_spatial_vars(self) -> List[str]:
        """获取可用的空间变量名列表（每个时间步有多个值的变量）"""
        if not self._loaded:
            return []

        # 空间变量是每个时间步有多个值（网格数）的变量
        # 时间变量是每个时间步只有一个值的变量
        spatial_vars = []
        all_keys = list(self.second_dict[0].keys())

        for key in all_keys:
            stripped = key.strip()
            # 跳过TIME和已添加的变量
            if stripped == 'TIME' or stripped in spatial_vars:
                continue
            # 检查这个变量是否是空间变量（数组长度大于1）
            data = self.second_dict[0].get(key, [])
            if len(data) > 1:
                spatial_vars.append(stripped)

        return spatial_vars

    def get_available_time_vars(self) -> List[str]:
        """获取可用的全局时间变量名列表"""
        return self.TIME_VARS.copy()

    def get_variable_display_name(self, var: str) -> str:
        """获取变量的显示名称 (中英文对照)"""
        from utils.config import Config
        return Config.VARIABLE_DISPLAY.get(var, var)

    def __str__(self):
        """返回文件信息字符串"""
        return f"Fort10Parser: {self.filepath}\n" \
               f"  时间步数: {self._n_timesteps}\n" \
               f"  网格数: {self._n_cells}\n" \
               f"  已加载: {self._loaded}"
