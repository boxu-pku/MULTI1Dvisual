"""Configuration for MULTI1D Visualizer v2.3.1.1"""

import json
import os


class Config:
    """Application configuration class"""

    # ========== 应用信息 ==========
    APP_NAME = "MULTI1D可视化工具"
    APP_VERSION = "2.3.1"
    APP_AUTHOR = "徐博(BoXu)"
    APP_EMAIL = "boxu25@stu.pku.edu.cn"
    APP_DATE = "2026-08-20"

    # ========== 变量显示名称映射 (使用英文label，避免字符显示问题) ==========
    VARIABLE_DISPLAY = {
        # 空间变量
        'XC': 'Centroid (cm)',
        'DENE': 'Electron Density (cm^-3)',
        'EE': 'Electron Energy (erg)',
        'EI': 'Ion Energy (erg)',
        'P': 'Pressure (dyn/cm^2)',
        'PT': 'Total Pressure (dyn/cm^2)',
        'R': 'Density (g/cm^3)',
        'T': 'Electron Temperature (eV)',
        'TI': 'Ion Temperature (eV)',
        'ZI': 'Ion Charge',
        'TR': 'Radiation Temperature (eV)',
        'V': 'Velocity (cm/s)',
        'D': 'Depth (cm)',
        'EA': 'Absorbed Energy',
        'F': 'Flux',
        'X': 'Position (cm)',
        'S': 'Source',
        'S+': 'Positive Source',
        'S-': 'Negative Source',

        # 时间变量
        'ENIE': 'Electron Internal Energy',
        'ENII': 'Ion Internal Energy',
        'ENKI': 'Kinetic Energy',
        'ENLAS': 'Incident Laser Energy',
        'ENQUE': 'Absorbed Laser Energy',
        'EALFA': 'Alpha Particle Energy',
        'ENAG': 'Fusion Energy/5',
        'ENAL': 'Alpha Loss Energy',
        'ENRAD': 'Radiation Energy',
        'EYIELD': 'Neutron Yield',
        'I-Left': 'Left Boundary',
        'I-Right': 'Right Boundary',
        'ENRG1': 'Energy Group 1',
        'ENRG2': 'Energy Group 2',
        'ENRG3': 'Energy Group 3',
        'ENRG4': 'Energy Group 4',
        'ENRL1': 'Radiation Group 1',
        'ENRL2': 'Radiation Group 2',
        'ENRL3': 'Radiation Group 3',
        'ENRL4': 'Radiation Group 4',
        # MULTI-IFE 专用变量
        'TE': 'Electron Temperature (eV)',
        'PE': 'Electron Pressure (dyn/cm^2)',
        'PI': 'Ion Pressure (dyn/cm^2)',
        'AD': 'Alpha Deposition',
        'ALPHA': 'Alpha Fraction',
        'ALPHAS': 'Alpha Loss Energy',
        'DEFUS': 'Deposited Fusion Energy',
        'DELAS': 'Absorbed Laser Energy',
        'DERAD': 'Absorbed Radiation',
        'ENIA': 'Alpha Particle Energy',
        'FUSION': 'Fusion Energy',
        'I+': 'Right Boundary Spectrum',
        'I-': 'Left Boundary Spectrum',
        'IFAR': 'In-Flight Aspect Ratio',
        'ISTEP': 'Time Step',
        'LASER': 'Incident Laser Energy',
        'NEUTRONS': 'Neutron Count',
        'REF': 'Laser Reflection',
        'RHORDT': 'rhoR (Cold)',
        'RHORHS': 'rhoR (Hot Spot)',
        'TRA': 'Laser Transmission',
        'VIMPLO': 'Implosion Velocity'
    }

    # ========== 绘图配置 ==========
    # 颜色名称映射（用户友好的名称 -> matplotlib颜色代码）
    COLOR_NAMES = {
        'red': '#e74c3c',
        'blue': '#3498db',
        'green': '#2ecc71',
        'orange': '#f39c12',
        'purple': '#9b59b6',
        'cyan': '#1abc9c',
        'magenta': '#e91e63',
        'brown': '#795548',
        'gray': '#607d8b',
        'black': '#000000',
        'darkred': '#c0392b',
        'darkblue': '#2980b9',
        'darkgreen': '#27ae60',
        'gold': '#f1c40f',
        'pink': '#ff69b4',
        'navy': '#000080',
        'teal': '#008080',
        'olive': '#808000',
        'maroon': '#800000',
        'coral': '#ff7f50'
    }

    # 颜色列表（用于下拉框）
    COLORS = list(COLOR_NAMES.keys())

    # 颜色代码列表（用于实际绘图）
    COLOR_CODES = list(COLOR_NAMES.values())

    LINE_STYLES = ['-', '--', '-.', ':']

    LINE_WIDTHS = [1.0, 1.5, 2.0, 2.5, 3.0]

    MARKERS = ['o', 's', '^', 'v', 'd', '*', '+', 'x']

    COLORMAPS = ['jet', 'viridis', 'plasma', 'inferno', 'magma',
                'cividis', 'coolwarm', 'RdYlBu', 'RdYlGn',
                'Spectral', 'seismic', 'twilight']

    # ========== 默认设置 ==========
    DEFAULT_CANVAS_WIDTH = 10
    DEFAULT_CANVAS_HEIGHT = 8
    DEFAULT_CANVAS_DPI = 100
    DEFAULT_SAVE_DPI = 300
    DEFAULT_IMAGE_FORMAT = 'png'

    # ========== 冲击波检测参数 (复用plot_density_dis.py) ==========
    SHOCK_DETECTION_THRESHOLD = 0.2  # 密度变化阈值 (g/cm³)
    DEFAULT_SHOCK_POSITIONS = [0, 1000]  # 默认检测位置 (um)

    # ========== 信号时间区域 (关心时间段) ==========
    DELAY = 14.8      # 信号来临延迟时间 (ns)
    PS_DURATION = 1.0   # 信号持续时间 (ns)

    # ========== 压强单位 ==========
    # 内部数据始终以 dyn/cm² 存储；显示时按用户选择的单位换算
    PRESSURE_VARS = ('P', 'PT')
    # 从 dyn/cm² 到目标单位的乘法因子
    PRESSURE_UNIT_FACTORS = {
        'dyn/cm^2': 1.0,
        'GPa': 1e-10,   # 1 GPa = 1e10 dyn/cm²
        'Mbar': 1e-12,  # 1 Mbar = 1e12 dyn/cm² = 100 GPa
    }
    DEFAULT_PRESSURE_UNIT = 'GPa'
    _current_pressure_unit = DEFAULT_PRESSURE_UNIT

    # 各变量类别当前选中的单位（运行期状态，可选持久化）
    # 实际初始化在文件末尾（class body 内部 dict comprehension 不能引用类名）
    _current_var_units = {}

    # ========== 通用：按物理量类型的单位系统 ==========
    # 用于 Y 轴变量 / colorbar 值的单位选择。
    # raw 数据的"原始单位"列在 raw_unit 里，factor 是"raw → target"的乘法因子。
    # coord 类（XC/X/CMC/CMI）是坐标系，单独处理（CMC/CMI 的 factor 与 xunit 联动）。
    VAR_UNIT_CATEGORIES = {
        'pressure': {
            'vars': ('P', 'PT'),
            'units': ['dyn/cm^2', 'GPa', 'Mbar'],
            'factors': {'dyn/cm^2': 1.0, 'GPa': 1e-10, 'Mbar': 1e-12},
            'default': 'GPa',
        },
        'temperature': {
            'vars': ('T', 'TI', 'TR'),
            'units': ['eV', 'K'],
            'factors': {'eV': 1.0, 'K': 11604.518},  # raw 是 eV；1 eV = 11604.518 K
            'default': 'eV',
        },
        'density': {
            'vars': ('R', 'DENE'),
            'units': ['g/cm^3'],
            'factors': {'g/cm^3': 1.0},
            'default': 'g/cm^3',
        },
        'velocity': {
            'vars': ('V',),
            'units': ['km/s'],
            'factors': {'km/s': 1e-5},  # raw 是 cm/s；1 km/s = 1e5 cm/s
            'default': 'km/s',
        },
        # 位置变量（XC/X）也作为 Y 轴变量时套同样的逻辑；raw 是 cm
        'position': {
            'vars': ('XC', 'X'),
            'units': ['um', 'cm'],
            'factors': {'um': 1e4, 'cm': 1.0},
            'default': 'um',
        },
    }

    # 变量描述（不含单位，单位单独拼）。给轴标签"var 描述 (unit)"用。
    VAR_DESCRIPTION = {
        'XC': 'Centroid',
        'X': 'Position',
        'CMC': 'Mass Coord',
        'CMI': 'Mass Interface',
        'LC': 'Lagrangian Coord',
        'LI': 'Lagrangian Interface',
        'R': 'Density',
        'DENE': 'Electron Density',
        'T': 'Electron Temperature',
        'TI': 'Ion Temperature',
        'TR': 'Radiation Temperature',
        'P': 'Pressure',
        'PT': 'Total Pressure',
        'V': 'Velocity',
        'EE': 'Electron Energy',
        'EI': 'Ion Energy',
        'ZI': 'Ion Charge',
        'D': 'Depth',
        'EA': 'Absorbed Energy',
        'F': 'Flux',
        'S': 'Source',
        'S+': 'Positive Source',
        'S-': 'Negative Source',
    }

    @classmethod
    def get_config_file_path(cls):
        """获取配置文件路径"""
        home = os.path.expanduser('~')
        return os.path.join(home, f'.{cls.APP_NAME}', 'config.json')

    @classmethod
    def save_settings(cls, settings: dict):
        """保存用户设置到配置文件"""
        config_path = cls.get_config_file_path()
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_settings(cls) -> dict:
        """加载用户设置"""
        config_path = cls.get_config_file_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}  # 返回默认空配置

    @classmethod
    def get_color_code(cls, color_name: str) -> str:
        """根据颜色名称获取颜色代码"""
        return cls.COLOR_NAMES.get(color_name, color_name)  # 如果找不到，返回原值（可能是代码）

    # ========== 压强单位辅助 ==========
    @classmethod
    def get_pressure_unit(cls) -> str:
        return cls._current_pressure_unit

    @classmethod
    def set_pressure_unit(cls, unit: str):
        """切换当前压强单位（不写盘）"""
        if unit in cls.PRESSURE_UNIT_FACTORS:
            cls._current_pressure_unit = unit

    @classmethod
    def get_pressure_factor(cls, unit: str = None) -> float:
        """返回从 dyn/cm² 到目标单位的换算因子"""
        unit = unit if unit is not None else cls._current_pressure_unit
        return cls.PRESSURE_UNIT_FACTORS.get(unit, 1.0)

    @classmethod
    def is_pressure_var(cls, var: str) -> bool:
        return (var or '').strip() in cls.PRESSURE_VARS

    @classmethod
    def format_pressure_label(cls, var: str, unit: str = None) -> str:
        """生成 'Pressure (GPa)' / 'Total Pressure (Mbar)' 之类的轴标签"""
        unit = unit if unit is not None else cls._current_pressure_unit
        name = 'Total Pressure' if (var or '').strip() == 'PT' else 'Pressure'
        return f'{name} ({unit})'

    @classmethod
    def convert_pressure_values(cls, values, unit: str = None):
        """对压强数据按当前/指定单位做数值换算"""
        import numpy as _np
        factor = cls.get_pressure_factor(unit)
        if factor == 1.0:
            return values
        if isinstance(values, _np.ndarray):
            return values * factor
        return [v * factor for v in values]

    @classmethod
    def save_pressure_unit(cls, unit: str = None):
        """持久化压强单位到 settings.json"""
        unit = unit if unit is not None else cls._current_pressure_unit
        settings = cls.load_settings()
        settings['pressure_unit'] = unit
        cls.save_settings(settings)

    @classmethod
    def load_pressure_unit(cls) -> str:
        """从 settings.json 读取并设为当前单位；读取失败时保留默认"""
        settings = cls.load_settings()
        unit = settings.get('pressure_unit', cls.DEFAULT_PRESSURE_UNIT)
        if unit in cls.PRESSURE_UNIT_FACTORS:
            cls._current_pressure_unit = unit
        return cls._current_pressure_unit

    # ========== 通用：按变量类型查询单位 ==========
    @classmethod
    def get_var_category(cls, var: str):
        """返回变量所属的单位类别 dict（含 units/factors/default），不属于任何类别返回 None"""
        v = (var or '').strip()
        for cat in cls.VAR_UNIT_CATEGORIES.values():
            if v in cat['vars']:
                return cat
        return None

    @classmethod
    def get_var_units(cls, var: str) -> list:
        """变量支持的所有单位列表；不属于任何类别返回 []"""
        cat = cls.get_var_category(var)
        return list(cat['units']) if cat else []

    @classmethod
    def get_var_factor(cls, var: str, unit: str) -> float:
        """变量在某单位下的换算因子（raw → 显示值）"""
        cat = cls.get_var_category(var)
        if cat is None:
            return 1.0
        return cat['factors'].get(unit, 1.0)

    @classmethod
    def get_var_default_unit(cls, var: str):
        """变量的默认单位；不属于任何类别返回 None"""
        cat = cls.get_var_category(var)
        return cat['default'] if cat else None

    @classmethod
    def format_var_label(cls, var: str, unit: str = None) -> str:
        """生成 "VAR 描述 (unit)" 形式的轴标签；unit 为 None 时不带括号"""
        v = (var or '').strip()
        desc = cls.VAR_DESCRIPTION.get(v, '')
        parts = [v] if v else []
        if desc:
            parts.append(desc)
        head = ' '.join(parts) if parts else ''
        if unit:
            return f'{head} ({unit})' if head else f'({unit})'
        return head

    # ---- 当前选中单位（per-category 运行期状态）----
    @classmethod
    def get_current_unit_for_var(cls, var: str) -> str:
        """返回当前 var 的单位；不在任何类别则返回 ''。
        若该类别尚未设置过，返回类别的 default。"""
        for name, cat in cls.VAR_UNIT_CATEGORIES.items():
            if (var or '').strip() in cat['vars']:
                return cls._current_var_units.get(name, cat['default'])
        return ''

    @classmethod
    def set_current_unit_for_var(cls, var: str, unit: str):
        """设置 var 所属类别的当前单位；不属于任何类别则忽略"""
        for name, cat in cls.VAR_UNIT_CATEGORIES.items():
            if (var or '').strip() in cat['vars']:
                if unit in cat['units']:
                    cls._current_var_units[name] = unit
                    # back-compat: 压强类别同步旧 API
                    if name == 'pressure':
                        cls._current_pressure_unit = unit
                return

    @classmethod
    def save_var_units(cls):
        """把当前各变量类别的单位持久化"""
        settings = cls.load_settings()
        settings['var_units'] = dict(cls._current_var_units)
        # 保留旧字段以便回退兼容
        settings['pressure_unit'] = cls._current_var_units.get('pressure', cls.DEFAULT_PRESSURE_UNIT)
        cls.save_settings(settings)

    @classmethod
    def load_var_units(cls):
        """从 settings.json 恢复各变量类别单位"""
        settings = cls.load_settings()
        saved = settings.get('var_units', {})
        for name, cat in cls.VAR_UNIT_CATEGORIES.items():
            if name in saved and saved[name] in cat['units']:
                cls._current_var_units[name] = saved[name]
        # 旧字段回退
        if 'pressure_unit' in settings and 'pressure' not in saved:
            pu = settings['pressure_unit']
            if pu in Config.VAR_UNIT_CATEGORIES['pressure']['units']:
                cls._current_var_units['pressure'] = pu
        # 同步旧 API
        cls._current_pressure_unit = cls._current_var_units['pressure']


# 初始化 _current_var_units（class body 内的 dict comprehension 不能引用同类的名字）
Config._current_var_units = {name: cat['default']
                             for name, cat in Config.VAR_UNIT_CATEGORIES.items()}
