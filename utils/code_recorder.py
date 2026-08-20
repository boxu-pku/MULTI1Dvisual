"""CodeRecorder - 代码录制器
记录用户的GUI操作，生成独立的Python脚本
"""

import os


class CodeRecorder:
    """代码录制器 - 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._is_recording = False
            self._file_path = None
            self._operations = []
            CodeRecorder._initialized = True

    @property
    def is_recording(self):
        return self._is_recording

    @property
    def file_path(self):
        return self._file_path

    @property
    def operation_count(self):
        return len(self._operations)

    def start_recording(self, file_path=None):
        self._is_recording = True
        self._file_path = file_path
        self._operations = []
        if file_path:
            self._operations.append({
                'type': 'file_open',
                'filepath': file_path
            })

    def stop_recording(self):
        self._is_recording = False

    def clear(self):
        self._operations = []
        self._file_path = None

    def record_file_open(self, filepath):
        if not self._is_recording:
            return
        self._file_path = filepath
        if not self._operations or self._operations[0]['type'] != 'file_open':
            self._operations.insert(0, {
                'type': 'file_open',
                'filepath': filepath
            })
        else:
            self._operations[0]['filepath'] = filepath

    def record_spatial_plot(self, var, time_indices, styles, xunit, yunit,
                            log_x, log_y, xlim, ylim, show_legend,
                            coord_system='XC'):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'spatial_plot',
            'var': var,
            'time_indices': list(time_indices),
            'styles': styles,
            'xunit': xunit,
            'yunit': yunit,
            'coord_system': coord_system,
            'log_x': log_x,
            'log_y': log_y,
            'xlim': xlim,
            'ylim': ylim,
            'show_legend': show_legend
        })

    def record_global_temporal(self, var, time_unit, color, linestyle, yunit,
                               log_x, log_y, xlim, ylim, show_legend):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'global_temporal',
            'var': var,
            'time_unit': time_unit,
            'color': color,
            'linestyle': linestyle,
            'yunit': yunit,
            'log_x': log_x,
            'log_y': log_y,
            'xlim': xlim,
            'ylim': ylim,
            'show_legend': show_legend
        })

    def record_cell_temporal(self, var, cell_indices, styles, time_unit, yunit,
                             log_x, log_y, xlim, ylim, show_legend):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'cell_temporal',
            'var': var,
            'cell_indices': list(cell_indices),
            'styles': styles,
            'time_unit': time_unit,
            'yunit': yunit,
            'log_x': log_x,
            'log_y': log_y,
            'xlim': xlim,
            'ylim': ylim,
            'show_legend': show_legend
        })

    def record_heatmap(self, var, xunit, time_unit, cmap, vmin, vmax,
                       log_color, transpose, xlim, ylim,
                       mark_positions, mark_times, coord_system='XC',
                       value_unit='', value_factor=1.0):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'heatmap',
            'var': var,
            'xunit': xunit,
            'coord_system': coord_system,
            'time_unit': time_unit,
            'cmap': cmap,
            'vmin': vmin,
            'vmax': vmax,
            'log_color': log_color,
            'transpose': transpose,
            'xlim': xlim,
            'ylim': ylim,
            'mark_positions': mark_positions,
            'mark_times': mark_times,
            'value_unit': value_unit,
            'value_factor': value_factor
        })

    def record_extreme_finder(self, profiles, find_max, find_min,
                              show_derivative, show_legend,
                              heatmap_settings):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'extreme_finder',
            'profiles': profiles,
            'find_max': find_max,
            'find_min': find_min,
            'show_derivative': show_derivative,
            'show_legend': show_legend,
            'heatmap_settings': heatmap_settings
        })

    def record_profile_extraction(self, start_pos, end_pos, var, xunit, time_unit):
        if not self._is_recording:
            return
        self._operations.append({
            'type': 'profile_extraction',
            'start_pos': start_pos,
            'end_pos': end_pos,
            'var': var,
            'xunit': xunit,
            'time_unit': time_unit
        })

    def generate_script(self, output_path):
        from utils.code_recorder_template import ScriptGenerator
        return ScriptGenerator.generate(self._file_path, self._operations, output_path)
