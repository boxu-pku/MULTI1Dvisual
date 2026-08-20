"""ScriptGenerator - standalone replay script generator
Embeds Fort10Parser + scanFile.py so the script is portable.
"""

import os
import sys
import re


class ScriptGenerator:
    """Script generator for standalone replay scripts."""

    @staticmethod
    def _read_source(path: str) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _build_embedded_parser():
        """Read scanFile.py + fort10_parser.py and make them self-contained."""
        base = os.path.dirname(os.path.abspath(__file__))
        # Read scanFile.py (it's in legacy/ one level up from utils/)
        scan_path = os.path.join(base, '..', 'legacy', 'scanFile.py')
        scan_code = ScriptGenerator._read_source(scan_path)
        # Strip shebang, keep everything else
        scan_lines = []
        for line in scan_code.split('\n'):
            if line.startswith('#!/'):
                continue
            scan_lines.append(line)
        scan_code = '\n'.join(scan_lines)

        # Read fort10_parser.py (it's in core/ one level up from utils/)
        parser_path = os.path.join(base, '..', 'core', 'fort10_parser.py')
        parser_source = ScriptGenerator._read_source(parser_path)
        parser_lines = parser_source.split('\n')

        # Transformations:
        transformed = []
        # 1. A dummy Logger that just prints
        transformed.append('')
        transformed.append('class _DummyLogger:')
        transformed.append('    @staticmethod')
        transformed.append('    def get_logger(name):')
        transformed.append('        return _DummyLogger()')
        transformed.append('    def warning(self, msg):')
        transformed.append('        print(f"WARN: {msg}")')
        transformed.append('Logger = _DummyLogger')
        transformed.append('')

        in_path_block = False
        for line in parser_lines:
            # Remove the sys.path manipulation block (any line referencing _legacy_path or _root_path)
            _stripped = line.strip()
            if '_legacy_path' in _stripped or '_root_path' in _stripped:
                in_path_block = True
                continue
            if in_path_block and ('sys.path.insert' in _stripped or 'sys.path.append' in _stripped or 'sys.path' in _stripped):
                continue
            if in_path_block and _stripped == '':
                in_path_block = False
                continue

            # Replace Logger import
            if 'from utils.logger import Logger' in line:
                continue  # Already added dummy above

            # Replace scanFile import: keep original, scanFile module registered below
            if 'from scanFile import readFileContents' in line:
                transformed.append('            from scanFile import readFileContents')
                continue

            # Replace Config-based get_variable_display_name with inline dict
            if 'from utils.config import Config' in line:
                continue
            if 'Config.VARIABLE_DISPLAY' in line:
                continue

            transformed.append(line)

        # Append a standalone get_variable_display_name that uses an inline dict
        var_display = ScriptGenerator._get_variable_display_dict()
        transformed.append('')
        transformed.append('    def get_variable_display_name(self, var):')
        transformed.append('        _display = {')
        for k, v in var_display.items():
            transformed.append(f'            {repr(k)}: {repr(v)},')
        transformed.append('        }')
        transformed.append('        return _display.get(var, var)')
        transformed.append('')

        parser_code = '\n'.join(transformed)

        # Combine: scanFile code + Fort10Parser
        combined = scan_code + '\n\n\n' + parser_code
        return combined

    @staticmethod
    def _get_variable_display_dict():
        try:
            from utils.config import Config
            return dict(Config.VARIABLE_DISPLAY)
        except Exception:
            return {}

    @staticmethod
    def generate(file_path, operations, output_path):
        lines = []
        lines.append('#!/usr/bin/env python')
        lines.append('# -*- coding: utf-8 -*-')
        _path_comment = str(file_path).replace('\\', '/') if file_path else ''
        lines.append('"""')
        lines.append('MULTI1D Visualizer - auto-generated standalone replay script')
        lines.append('Data file: ' + _path_comment)
        lines.append('"""')
        lines.append('')

        # Imports
        lines.append('import sys, os, struct')
        lines.append('import numpy as np')
        lines.append('import matplotlib')
        lines.append("matplotlib.use('Agg')")
        lines.append('import matplotlib.pyplot as plt')
        lines.append('from matplotlib.colors import Normalize, LogNorm')
        lines.append('from scipy.interpolate import interp1d, RegularGridInterpolator')
        lines.append('')

        # Embedded parser
        parser_code = ScriptGenerator._build_embedded_parser()
        for pline in parser_code.split('\n'):
            lines.append(pline)
        lines.append('')
        lines.append('# Register scanFile module so Fort10Parser can import readFileContents')
        lines.append('import types')
        lines.append('_sf_mod = types.ModuleType("scanFile")')
        lines.append('_sf_mod.readFileContents = readFileContents')
        lines.append('sys.modules["scanFile"] = _sf_mod')
        lines.append('')

        # Data loading �?use absolute path for reliability
        data_path = file_path if file_path else 'fort.10'
        abs_data_path = os.path.abspath(data_path)
        lines.append('# ======== Load Data ========')
        lines.append('_DATA_FILE = r"' + str(abs_data_path) + '"')
        lines.append('if not os.path.exists(_DATA_FILE):')
        lines.append('    _DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "' + os.path.basename(str(data_path)) + '")')
        lines.append('parser = Fort10Parser(_DATA_FILE)')
        lines.append('parser.parse()')
        lines.append('print(f"Loaded: {_DATA_FILE}")')
        lines.append('print(f"  Timesteps: {parser.get_n_timesteps()}, Cells: {parser.get_n_cells()}")')
        lines.append('')

        # Plot style �?IM_tool P-up 风格
        lines.append('# ======== Plot Style ========')
        lines.append("plt.rcParams['font.family'] = 'serif'")
        lines.append("plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Computer Modern Roman']")
        lines.append("plt.rcParams['mathtext.fontset'] = 'dejavuserif'")
        lines.append("plt.rcParams['axes.unicode_minus'] = True")
        lines.append("plt.rcParams['font.size'] = 18")
        lines.append("plt.rcParams['axes.titlesize'] = 20")
        lines.append("plt.rcParams['axes.labelsize'] = 20")
        lines.append("plt.rcParams['xtick.labelsize'] = 16")
        lines.append("plt.rcParams['ytick.labelsize'] = 16")
        lines.append("plt.rcParams['legend.fontsize'] = 16")
        lines.append("plt.rcParams['figure.titlesize'] = 20")
        lines.append("plt.rcParams['axes.linewidth'] = 1.2")
        lines.append("plt.rcParams['axes.grid'] = False")
        lines.append("plt.rcParams['xtick.major.width'] = 1.2")
        lines.append("plt.rcParams['ytick.major.width'] = 1.2")
        lines.append("plt.rcParams['xtick.minor.width'] = 0.8")
        lines.append("plt.rcParams['ytick.minor.width'] = 0.8")
        lines.append("plt.rcParams['xtick.major.size'] = 6")
        lines.append("plt.rcParams['ytick.major.size'] = 6")
        lines.append("plt.rcParams['xtick.minor.size'] = 4")
        lines.append("plt.rcParams['ytick.minor.size'] = 4")
        lines.append("plt.rcParams['lines.linewidth'] = 1.2")
        lines.append("plt.rcParams['lines.markersize'] = 6")
        lines.append("plt.rcParams['legend.frameon'] = False")
        lines.append("plt.rcParams['legend.handlelength'] = 1.5")
        lines.append('')
        lines.append('def _latex_unit(unit):')
        lines.append('    import re')
        lines.append('    if not unit: return unit')
        lines.append("    s = unit.replace('um', '$\\\\mu$m').replace('\\xb7', '$\\\\cdot$')")
        lines.append("    s = re.sub(r'\\^(\\d+)', r'$^{\\1}$', s)")
        lines.append('    return s')
        lines.append('')
        lines.append('def _apply_style(ax):')
        lines.append('    for s in [\"top\",\"right\",\"left\",\"bottom\"]:')
        lines.append('        ax.spines[s].set_visible(True)')
        lines.append('        ax.spines[s].set_linewidth(1.2)')
        lines.append('    ax.tick_params(axis=\"both\", which=\"major\", direction=\"in\", top=False, right=False, width=1.2, length=6)')
        lines.append('    ax.tick_params(axis=\"both\", which=\"minor\", direction=\"in\", top=False, right=False, width=0.8, length=4)')
        lines.append('    import matplotlib.ticker as _tk')
        lines.append('    ax.xaxis.set_major_locator(_tk.MaxNLocator(nbins=6))')
        lines.append('    ax.yaxis.set_major_locator(_tk.MaxNLocator(nbins=6))')
        lines.append('    ax.minorticks_on()')
        lines.append('')

        # Pressure unit from GUI session (for global temporal)
        try:
            from utils.config import Config as _Cfg
            _gui_pressure_unit = _Cfg.get_pressure_unit()
            _gui_pressure_factor = _Cfg.get_pressure_factor()
        except Exception:
            _gui_pressure_unit = 'GPa'
            _gui_pressure_factor = 1e-10
        lines.append('# Pressure unit from GUI session')
        lines.append(f'_PRESSURE_FACTOR = {_gui_pressure_factor}')
        lines.append(f'_PRESSURE_UNIT = {repr(_gui_pressure_unit)}')
        lines.append('')

        # Per-operation generation
        fig_counter = 0
        for i, op in enumerate(operations):
            op_type = op['type']
            if op_type == 'file_open':
                continue
            fig_counter += 1
            lines.append('# ======== Operation ' + str(i) + ': ' + op_type + ' (Figure ' + str(fig_counter) + ') ========')
            lines.append('fig' + str(fig_counter) + ', ax' + str(fig_counter) + ' = plt.subplots(figsize=(10, 7))')
            lines.append('_apply_style(ax' + str(fig_counter) + ')')
            lines.append('')

            if op_type == 'spatial_plot':
                ScriptGenerator._gen_spatial(lines, fig_counter, op)
            elif op_type == 'global_temporal':
                ScriptGenerator._gen_global_temporal(lines, fig_counter, op)
            elif op_type == 'cell_temporal':
                ScriptGenerator._gen_cell_temporal(lines, fig_counter, op)
            elif op_type == 'heatmap':
                ScriptGenerator._gen_heatmap(lines, fig_counter, op)
            elif op_type == 'extreme_finder':
                extra_figs = ScriptGenerator._gen_extreme_finder(lines, fig_counter, op, output_path)
                fig_counter += extra_figs
                continue
            elif op_type == 'profile_extraction':
                ScriptGenerator._gen_profile_extraction(lines, fig_counter, op)

            base = os.path.splitext(os.path.basename(output_path))[0]
            save_name = base + '_fig' + str(fig_counter) + '_' + op_type + '.png'
            lines.append('fig' + str(fig_counter) + '.savefig(r"' + save_name + '", dpi=300, bbox_inches="tight")')
            lines.append('print("Saved: ' + save_name + '")')
            lines.append('')

        lines.append('print("All done.")')
        lines.append('# plt.show()')

        script_text = '\n'.join(lines)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script_text)

        return output_path

    # ------------------------------------------------------------------
    # All generators use plain string concat so that {var} in output
    # is a literal f-string expression in the generated script.
    # ------------------------------------------------------------------

    @staticmethod
    def _get_var_factor_from_config(var, yunit):
        if not yunit:
            return 1.0
        try:
            from utils.config import Config
            return Config.get_var_factor(var, yunit)
        except Exception:
            return 1.0

    @staticmethod
    def _format_var_label(var, yunit):
        try:
            from utils.config import Config
            return Config.format_var_label(var, yunit) if yunit else Config.format_var_label(var)
        except Exception:
            return var

    @staticmethod
    def _is_pressure_var(var):
        try:
            from utils.config import Config
            return Config.is_pressure_var(var)
        except Exception:
            return False

    @staticmethod
    def _gen_spatial(lines, fig_n, op):
        var = op['var']
        xunit = op['xunit']
        yunit = op.get('yunit', '')
        coord_system = op.get('coord_system', 'XC')
        time_indices = op['time_indices']
        styles = op['styles']
        log_x = op['log_x']
        log_y = op['log_y']
        xlim = op['xlim']
        ylim = op['ylim']
        show_legend = op['show_legend']
        fign = str(fig_n)

        yfactor = ScriptGenerator._get_var_factor_from_config(var, yunit)
        ylabel = ScriptGenerator._format_var_label(var, yunit)

        lines.append('_var = ' + repr(var))
        lines.append('_xunit = ' + repr(xunit))
        lines.append('_coord_system = ' + repr(coord_system))
        lines.append('_yfactor = ' + str(yfactor))
        lines.append('_times_ns = parser.get_time_array(unit="ns")')
        lines.append('')

        for j, tidx in enumerate(time_indices):
            s = styles.get(str(tidx), styles.get(tidx, {}))
            color = repr(s.get('color', 'black'))
            ls = repr(s.get('linestyle', '-'))
            lw = s.get('linewidth', 1.5)

            lines.append('# Curve ' + str(j + 1) + ': time index ' + str(tidx))
            lines.append('_grid_' + str(j) + ', _vals_' + str(j) + ' = parser.get_spatial_data(_var, ' + str(tidx) + ', coord_system=_coord_system)')
            lines.append('_vals_' + str(j) + ' = _vals_' + str(j) + ' * _yfactor')
            lines.append('ax' + fign + '.plot(_grid_' + str(j) + ', _vals_' + str(j) + ', color=' + color + ', linestyle=' + ls + ', linewidth=' + str(lw) + ', label=f"t={_times_ns[' + str(tidx) + ']:.3f}ns")')
            lines.append('')

        lines.append('ax' + fign + '.set_xlabel(_latex_unit(f"Position ({_xunit})"))')
        lines.append('ax' + fign + '.set_ylabel(_latex_unit(' + repr(ylabel) + '))')
        if log_x:
            lines.append('ax' + fign + '.set_xscale("log")')
        if log_y:
            lines.append('ax' + fign + '.set_yscale("log")')
        if xlim:
            lines.append('ax' + fign + '.set_xlim(' + str(xlim) + ')')
        if ylim:
            lines.append('ax' + fign + '.set_ylim(' + str(ylim) + ')')
        if show_legend:
            lines.append('ax' + fign + '.legend(loc="best", fontsize=8)')
        lines.append('fig' + fign + '.tight_layout()')
        lines.append('')

    @staticmethod
    def _gen_global_temporal(lines, fig_n, op):
        var = op['var']
        time_unit = op['time_unit']
        color = repr(op['color'])
        linestyle = repr(op['linestyle'])
        yunit = op.get('yunit', '')
        log_x = op['log_x']
        log_y = op['log_y']
        xlim = op['xlim']
        ylim = op['ylim']
        show_legend = op['show_legend']
        fign = str(fig_n)

        lines.append('_var = ' + repr(var))
        lines.append('_time_unit = ' + repr(time_unit))
        lines.append('_times, _values = parser.get_time_series_global(_var)')
        lines.append('if _time_unit == "ns":')
        lines.append('    _times = _times * 1e9')
        is_pv = ScriptGenerator._is_pressure_var(var)
        if is_pv:
            lines.append('_values = _values * _PRESSURE_FACTOR')
            lines.append('_ylabel_ = _var + " (" + _PRESSURE_UNIT + ")"')
            lines.append('ax' + fign + '.plot(_times, _values, color=' + color + ', linestyle=' + linestyle + ', linewidth=1.5, label=_var)')
            ylabel_set = '_ylabel_'
        elif yunit:
            yfactor = ScriptGenerator._get_var_factor_from_config(var, yunit)
            lines.append('_values = _values * ' + str(yfactor))
            ylabel_val = ScriptGenerator._format_var_label(var, yunit)
            lines.append('_ylabel_ = ' + repr(ylabel_val))
            lines.append('ax' + fign + '.plot(_times, _values, color=' + color + ', linestyle=' + linestyle + ', linewidth=1.5, label=_var)')
        else:
            ylabel_val = ScriptGenerator._format_var_label(var, None)
            lines.append('_ylabel_ = ' + repr(ylabel_val))
            lines.append('ax' + fign + '.plot(_times, _values, color=' + color + ', linestyle=' + linestyle + ', linewidth=1.5, label=_var)')
        lines.append('ax' + fign + '.set_xlabel(_latex_unit(f"Time ({_time_unit})"))')
        lines.append('ax' + fign + '.set_ylabel(_latex_unit(_ylabel_))')
        if log_x:
            lines.append('ax' + fign + '.set_xscale("log")')
        if log_y:
            lines.append('ax' + fign + '.set_yscale("log")')
        if xlim:
            lines.append('ax' + fign + '.set_xlim(' + str(xlim) + ')')
        if ylim:
            lines.append('ax' + fign + '.set_ylim(' + str(ylim) + ')')
        if show_legend:
            lines.append('ax' + fign + '.legend(loc="best", fontsize=8)')

        lines.append('fig' + fign + '.tight_layout()')
        lines.append('')

    @staticmethod
    def _gen_cell_temporal(lines, fig_n, op):
        var = op['var']
        time_unit = op['time_unit']
        yunit = op.get('yunit', '')
        cell_indices = op['cell_indices']
        styles = op['styles']
        log_x = op['log_x']
        log_y = op['log_y']
        xlim = op['xlim']
        ylim = op['ylim']
        show_legend = op['show_legend']
        fign = str(fig_n)

        yfactor = ScriptGenerator._get_var_factor_from_config(var, yunit)
        ylabel = ScriptGenerator._format_var_label(var, yunit)

        lines.append('_var = ' + repr(var))
        lines.append('_time_unit = ' + repr(time_unit))
        lines.append('_yfactor = ' + str(yfactor))
        lines.append('_times = parser.get_time_array(unit=_time_unit)')
        lines.append('')

        for j, cidx in enumerate(cell_indices):
            s = styles.get(str(cidx), styles.get(cidx, {}))
            color = repr(s.get('color', 'black'))
            ls = repr(s.get('linestyle', '-'))
            lw = s.get('linewidth', 1.5)

            lines.append('# Curve ' + str(j + 1) + ': cell ' + str(cidx))
            lines.append('_t_' + str(j) + ', _v_' + str(j) + ' = parser.get_time_series_at_cell(_var, ' + str(cidx) + ')')
            lines.append('_v_' + str(j) + ' = _v_' + str(j) + ' * _yfactor')
            lines.append('ax' + fign + '.plot(_times, _v_' + str(j) + ', color=' + color + ', linestyle=' + ls + ', linewidth=' + str(lw) + ', label="Cell #' + str(cidx) + '")')
            lines.append('')

        lines.append('ax' + fign + '.set_xlabel(_latex_unit(f"Time ({_time_unit})"))')
        lines.append('ax' + fign + '.set_ylabel(_latex_unit(' + repr(ylabel) + '))')
        if log_x:
            lines.append('ax' + fign + '.set_xscale("log")')
        if log_y:
            lines.append('ax' + fign + '.set_yscale("log")')
        if xlim:
            lines.append('ax' + fign + '.set_xlim(' + str(xlim) + ')')
        if ylim:
            lines.append('ax' + fign + '.set_ylim(' + str(ylim) + ')')
        if show_legend:
            lines.append('ax' + fign + '.legend(loc="best", fontsize=8)')

        lines.append('fig' + fign + '.tight_layout()')
        lines.append('')

    @staticmethod
    def _gen_heatmap(lines, fig_n, op):
        var = op['var']
        xunit = op['xunit']
        coord_system = op.get('coord_system', 'XC')
        time_unit = op['time_unit']
        cmap = op['cmap']
        vmin = op['vmin']
        vmax = op['vmax']
        log_color = op['log_color']
        transpose = op['transpose']
        xlim = op['xlim']
        ylim = op['ylim']
        mark_positions = op['mark_positions']
        mark_times = op['mark_times']
        value_unit = op.get('value_unit', '')
        value_factor = op.get('value_factor', 1.0)
        fign = str(fig_n)

        ylabel = ScriptGenerator._format_var_label(var, value_unit or '')

        lines.append('_var = ' + repr(var))
        lines.append('_xunit = ' + repr(xunit))
        lines.append('_coord_system = ' + repr(coord_system))
        lines.append('_time_unit = ' + repr(time_unit))
        lines.append('_value_factor = ' + str(value_factor))
        lines.append('_times = parser.get_time_array(unit=_time_unit)')
        lines.append('_grid = parser.get_grid_positions(unit=_xunit, coord_system=_coord_system)')
        lines.append('_data = parser.get_spatial_data_all_times(_var)')
        lines.append('if not isinstance(_data, np.ndarray):')
        lines.append('    _data = np.array(_data)')
        lines.append('_data = _data * _value_factor')
        lines.append('')

        lines.append('_n_interp = 500')
        if transpose:
            lines.append('# Transpose: X=Time, Y=Position')
            lines.append('_t_grid = np.linspace(np.min(_times), np.max(_times), _n_interp)')
            lines.append('_interp_data = []')
            lines.append('for _i in range(len(_grid)):')
            lines.append('    _col = _data[:, _i] if _data.ndim > 1 else _data[_i]')
            lines.append('    _t_orig = _times[:min(len(_times), len(_col))]')
            lines.append('    if len(_t_orig) >= 2:')
            lines.append('        _f = interp1d(_t_orig, _col[:len(_t_orig)], kind="linear", bounds_error=False, fill_value=np.nan)')
            lines.append('        _interp_data.append(_f(_t_grid))')
            lines.append('    else:')
            lines.append('        _interp_data.append(np.full(_n_interp, np.nan))')
            lines.append('_interp_data = np.array(_interp_data)')
            lines.append('_X, _Y = np.meshgrid(_t_grid, _grid)')
            lines.append('_xlabel, _ylabel = "Time", "Position"')
            lines.append('_xunit_label, _yunit_label = _time_unit, _xunit')
        else:
            lines.append('# No transpose: X=Position, Y=Time')
            lines.append('_x_grid = np.linspace(np.min(_grid), np.max(_grid), _n_interp)')
            lines.append('_interp_data = []')
            lines.append('for _i in range(len(_times)):')
            lines.append('    _row = _data[_i] if _i < len(_data) else np.full(len(_grid), np.nan)')
            lines.append('    if not isinstance(_row, np.ndarray): _row = np.array(_row)')
            lines.append('    _n_pts = min(len(_grid), len(_row))')
            lines.append('    if _n_pts >= 2:')
            lines.append('        _f = interp1d(_grid[:_n_pts], _row[:_n_pts], kind="linear", bounds_error=False, fill_value=np.nan)')
            lines.append('        _interp_data.append(_f(_x_grid))')
            lines.append('    else:')
            lines.append('        _interp_data.append(np.full(_n_interp, np.nan))')
            lines.append('_interp_data = np.array(_interp_data)')
            lines.append('_X, _Y = np.meshgrid(_x_grid, _times)')
            lines.append('_xlabel, _ylabel = "Position", "Time"')
            lines.append('_xunit_label, _yunit_label = _xunit, _time_unit')

        lines.append('')
        if log_color:
            lines.append('_norm = LogNorm(vmin=' + str(vmin) + ', vmax=' + str(vmax) + ')')
        else:
            lines.append('_norm = Normalize(vmin=' + str(vmin) + ', vmax=' + str(vmax) + ')')
        lines.append('_im = ax' + fign + '.pcolormesh(_X, _Y, _interp_data, cmap="' + cmap + '", norm=_norm, shading="gouraud")')
        lines.append('fig' + fign + '.colorbar(_im, ax=ax' + fign + ', label=_latex_unit(' + repr(ylabel) + '))')
        lines.append('ax' + fign + '.set_xlabel(_latex_unit(f"{_xlabel} ({_xunit_label})"))')
        lines.append('ax' + fign + '.set_ylabel(_latex_unit(f"{_ylabel} ({_yunit_label})"))')
        if xlim:
            lines.append('ax' + fign + '.set_xlim(' + str(xlim) + ')')
        if ylim:
            lines.append('ax' + fign + '.set_ylim(' + str(ylim) + ')')
        if mark_positions:
            lines.append('for _mp in ' + repr(mark_positions) + ':')
            lines.append('    ax' + fign + '.axhline(y=_mp, color="white", linestyle="--", linewidth=1, alpha=0.8)')
        if mark_times:
            lines.append('for _mt in ' + repr(mark_times) + ':')
            lines.append('    ax' + fign + '.axvline(x=_mt, color="white", linestyle="--", linewidth=1, alpha=0.8)')
        lines.append('fig' + fign + '.tight_layout()')
        lines.append('')

    @staticmethod
    def _gen_extreme_finder(lines, fig_n, op, output_path):
        profiles = op['profiles']
        find_max = op['find_max']
        find_min = op['find_min']
        show_derivative = op['show_derivative']
        show_legend = op['show_legend']
        hm = op.get('heatmap_settings', {})
        fign = str(fig_n)
        base = os.path.splitext(os.path.basename(output_path))[0]

        var = hm.get('var', '')
        xunit = hm.get('xunit', 'um')
        coord_system = hm.get('coord_system', 'XC')
        time_unit = hm.get('time_unit', 'ns')
        axis_direction = hm.get('axis_direction', 0)
        cmap = hm.get('cmap', 'jet')
        vmin = hm.get('vmin', 0)
        vmax = hm.get('vmax', 1)
        log_color = hm.get('log_color', False)
        value_unit = hm.get('value_unit', '')
        value_factor = hm.get('value_factor', 1.0)
        transpose = (axis_direction == 0)

        ylabel = ScriptGenerator._format_var_label(var, value_unit or '')

        # ---- Common data loading ----
        lines.append('_var = ' + repr(var))
        lines.append('_xunit = ' + repr(xunit))
        lines.append('_coord_system = ' + repr(coord_system))
        lines.append('_time_unit = ' + repr(time_unit))
        lines.append('_value_factor = ' + str(value_factor))
        lines.append('_times = parser.get_time_array(unit=_time_unit)')
        lines.append('_grid = parser.get_grid_positions(unit=_xunit, coord_system=_coord_system)')
        lines.append('_data = parser.get_spatial_data_all_times(_var)')
        lines.append('if not isinstance(_data, np.ndarray): _data = np.array(_data)')
        lines.append('_data = _data * _value_factor')
        lines.append('')

        # ---- Extract all profile data first ----
        colors_list = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                       '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        lines.append('# ---- Extract profiles ----')
        lines.append('_all_profiles = []')
        for j, prof in enumerate(profiles):
            coord_type = prof.get('coord_type', 'position')
            coord_value = prof.get('coord_value', 0.0)
            c = colors_list[j % len(colors_list)]

            lines.append('# Profile ' + str(j + 1) + ': ' + coord_type + '=' + str(coord_value))
            if coord_type == 'position':
                lines.append('_prof_x_' + str(j) + ' = _times.copy()')
                lines.append('_prof_y_' + str(j) + ' = []')
                lines.append('for _ti in range(len(_times)):')
                lines.append('    if _ti < len(_data):')
                lines.append('        _row = _data[_ti]')
                lines.append('        _n_pts = min(len(_grid), len(_row))')
                lines.append('        if _n_pts >= 2:')
                lines.append('            _f = interp1d(_grid[:_n_pts], _row[:_n_pts], kind="linear", bounds_error=False, fill_value=np.nan)')
                lines.append('            _prof_y_' + str(j) + '.append(_f(' + str(coord_value) + '))')
                lines.append('        else:')
                lines.append('            _prof_y_' + str(j) + '.append(np.nan)')
                lines.append('    else:')
                lines.append('        _prof_y_' + str(j) + '.append(np.nan)')
                lines.append('_prof_y_' + str(j) + ' = np.array(_prof_y_' + str(j) + ')')
                lines.append('_all_profiles.append({"coord_type": "position", "coord_value": ' + str(coord_value) + ', "x_data": _prof_x_' + str(j) + ', "y_data": _prof_y_' + str(j) + ', "color": "' + c + '"})')
            else:
                lines.append('_time_idx = np.argmin(np.abs(_times - ' + str(coord_value) + '))')
                lines.append('if _time_idx < len(_data):')
                lines.append('    _row = _data[_time_idx]')
                lines.append('    _n_pts = min(len(_grid), len(_row))')
                lines.append('    _prof_x_' + str(j) + ' = _grid[:_n_pts].copy()')
                lines.append('    _prof_y_' + str(j) + ' = np.array(_row[:_n_pts])')
                lines.append('else:')
                lines.append('    _prof_x_' + str(j) + ' = np.array([])')
                lines.append('    _prof_y_' + str(j) + ' = np.array([])')
                lines.append('_all_profiles.append({"coord_type": "time", "coord_value": ' + str(coord_value) + ', "x_data": _prof_x_' + str(j) + ', "y_data": _prof_y_' + str(j) + ', "color": "' + c + '"})')
            lines.append('')

        # ---- Find extrema ----
        lines.append('# ---- Find extrema (with range support) ----')
        lines.append('def _find_extrema(_xd, _yd, _ranges, _find_max, _find_min):')
        lines.append('    _valid_mask = ~np.isnan(_yd)')
        lines.append('    _x_valid = _xd[_valid_mask]')
        lines.append('    _y_valid = _yd[_valid_mask]')
        lines.append('    _results = []')
        lines.append('    if len(_y_valid) < 1:')
        lines.append('        return _results')
        lines.append('    if not _ranges:')
        lines.append('        if _find_max and len(_y_valid) > 0:')
        lines.append('            _idx = np.argmax(_y_valid)')
        lines.append('            _results.append((_x_valid[_idx], _y_valid[_idx], True))')
        lines.append('        if _find_min and len(_y_valid) > 0:')
        lines.append('            _idx = np.argmin(_y_valid)')
        lines.append('            _results.append((_x_valid[_idx], _y_valid[_idx], False))')
        lines.append('    else:')
        lines.append('        for _rmin, _rmax in _ranges:')
        lines.append('            _rmask = (_x_valid >= _rmin) & (_x_valid <= _rmax)')
        lines.append('            _xr = _x_valid[_rmask]')
        lines.append('            _yr = _y_valid[_rmask]')
        lines.append('            if len(_yr) > 0:')
        lines.append('                if _find_max:')
        lines.append('                    _idx = np.argmax(_yr)')
        lines.append('                    _results.append((_xr[_idx], _yr[_idx], True))')
        lines.append('                if _find_min:')
        lines.append('                    _idx = np.argmin(_yr)')
        lines.append('                    _results.append((_xr[_idx], _yr[_idx], False))')
        lines.append('    return _results')
        lines.append('')
        lines.append('_all_extremes = []')
        for j in range(len(profiles)):
            ranges_j = profiles[j].get('ranges', [])
            lines.append('if len(_all_profiles[' + str(j) + ']["y_data"]) > 0:')
            lines.append('    _extrema_' + str(j) + ' = _find_extrema(')
            lines.append('        _all_profiles[' + str(j) + ']["x_data"],')
            lines.append('        _all_profiles[' + str(j) + ']["y_data"],')
            lines.append('        ' + repr(ranges_j) + ',')
            lines.append('        ' + repr(find_max) + ', ' + repr(find_min) + ')')
            lines.append('    for _ex, _ey, _is_mx in _extrema_' + str(j) + ':')
            lines.append('        _all_extremes.append((' + str(j) + ', _ex, _ey, _is_mx))')
            lines.append('        _lbl = "max" if _is_mx else "min"')
            lines.append('        print(f"  Profile ' + str(j + 1) + ' {_lbl}: {_ex:.4f}, value={_ey:.4e}")')
        lines.append('')

        # Figure A: Heatmap with markers
        lines.append('# ---- Figure ' + fign + ': Heatmap with markers ----')
        lines.append('_n_interp = 500')
        if transpose:
            lines.append('_t_grid = np.linspace(np.min(_times), np.max(_times), _n_interp)')
            lines.append('_interp_data = []')
            lines.append('for _i in range(len(_grid)):')
            lines.append('    _col = _data[:, _i] if _data.ndim > 1 else _data[_i]')
            lines.append('    _t_orig = _times[:min(len(_times), len(_col))]')
            lines.append('    if len(_t_orig) >= 2:')
            lines.append('        _f = interp1d(_t_orig, _col[:len(_t_orig)], kind="linear", bounds_error=False, fill_value=np.nan)')
            lines.append('        _interp_data.append(_f(_t_grid))')
            lines.append('    else:')
            lines.append('        _interp_data.append(np.full(_n_interp, np.nan))')
            lines.append('_interp_data = np.array(_interp_data)')
            lines.append('_X, _Y = np.meshgrid(_t_grid, _grid)')
        else:
            lines.append('_x_grid = np.linspace(np.min(_grid), np.max(_grid), _n_interp)')
            lines.append('_interp_data = []')
            lines.append('for _i in range(len(_times)):')
            lines.append('    if _i < len(_data):')
            lines.append('        _row = _data[_i]')
            lines.append('        _n_pts = min(len(_grid), len(_row))')
            lines.append('        if _n_pts >= 2:')
            lines.append('            _f = interp1d(_grid[:_n_pts], _row[:_n_pts], kind="linear", bounds_error=False, fill_value=np.nan)')
            lines.append('            _interp_data.append(_f(_x_grid))')
            lines.append('        else:')
            lines.append('            _interp_data.append(np.full(_n_interp, np.nan))')
            lines.append('    else:')
            lines.append('        _interp_data.append(np.full(_n_interp, np.nan))')
            lines.append('_interp_data = np.array(_interp_data)')
            lines.append('_X, _Y = np.meshgrid(_x_grid, _times)')

        if log_color:
            lines.append('_norm = LogNorm(vmin=' + str(vmin) + ', vmax=' + str(vmax) + ')')
        else:
            lines.append('_norm = Normalize(vmin=' + str(vmin) + ', vmax=' + str(vmax) + ')')
        lines.append('_im = ax' + fign + '.pcolormesh(_X, _Y, _interp_data, cmap="' + cmap + '", norm=_norm, shading="gouraud")')
        lines.append('fig' + fign + '.colorbar(_im, ax=ax' + fign + ', label=_latex_unit(' + repr(ylabel) + '))')

        lines.append('for _p in _all_profiles:')
        if transpose:
            lines.append('    if _p["coord_type"] == "position":')
            lines.append('        ax' + fign + '.axhline(y=_p["coord_value"], color="red", linestyle="--", linewidth=2, alpha=0.9)')
            lines.append('    else:')
            lines.append('        ax' + fign + '.axvline(x=_p["coord_value"], color="white", linestyle="--", linewidth=1.5, alpha=0.8)')
        else:
            lines.append('    if _p["coord_type"] == "position":')
            lines.append('        ax' + fign + '.axvline(x=_p["coord_value"], color="white", linestyle="--", linewidth=1.5, alpha=0.8)')
            lines.append('    else:')
            lines.append('        ax' + fign + '.axhline(y=_p["coord_value"], color="red", linestyle="--", linewidth=2, alpha=0.9)')

        lines.append('# Extreme annotations')
        lines.append('for _pidx, _ex, _ey, _is_max in _all_extremes:')
        lines.append('    _prof = _all_profiles[_pidx]')
        lines.append('    if _prof["coord_type"] == "position":')
        if transpose:
            lines.append('        _hmap_x, _hmap_y = _ex, _prof["coord_value"]')
            lines.append('        ax' + fign + '.axvline(x=_ex, color="white", linestyle="--", linewidth=2, alpha=0.8)')
            lines.append('        _yl = ax' + fign + '.get_ylim()')
            lines.append('        ax' + fign + '.text(_ex, _yl[1] * 0.95, f"{_ex:.2f}", color="white", fontsize=9, ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.5))')
        else:
            lines.append('        _hmap_x, _hmap_y = _prof["coord_value"], _ex')
            lines.append('        ax' + fign + '.axhline(y=_ex, color="white", linestyle="--", linewidth=2, alpha=0.8)')
            lines.append('        _xl = ax' + fign + '.get_xlim()')
            lines.append('        ax' + fign + '.text(_xl[1] * 0.95, _ex, f"{_ex:.2f}", color="white", fontsize=9, va="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.5))')
        lines.append('    else:')
        if transpose:
            lines.append('        _hmap_x, _hmap_y = _prof["coord_value"], _ex')
            lines.append('        ax' + fign + '.axhline(y=_ex, color="white", linestyle="--", linewidth=2, alpha=0.8)')
            lines.append('        _xl = ax' + fign + '.get_xlim()')
            lines.append('        ax' + fign + '.text(_xl[1] * 0.95, _ex, f"{_ex:.2f}", color="white", fontsize=9, va="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.5))')
        else:
            lines.append('        _hmap_x, _hmap_y = _ex, _prof["coord_value"]')
            lines.append('        ax' + fign + '.axvline(x=_ex, color="white", linestyle="--", linewidth=2, alpha=0.8)')
            lines.append('        _yl = ax' + fign + '.get_ylim()')
            lines.append('        ax' + fign + '.text(_ex, _yl[1] * 0.95, f"{_ex:.2f}", color="white", fontsize=9, ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.5))')
        lines.append('    ax' + fign + '.plot(_hmap_x, _hmap_y, "yo", markersize=6, markeredgecolor="black", markeredgewidth=1.5)')

        lines.append('fig' + fign + '.tight_layout()')
        save_a = base + '_fig' + fign + '_extreme_heatmap.png'
        lines.append('fig' + fign + '.savefig(r"' + save_a + '", dpi=300, bbox_inches="tight")')
        lines.append('print("Saved: ' + save_a + '")')
        lines.append('')

        # Figure B: Profile curves
        fig_b = fig_n + 1
        figb = str(fig_b)
        lines.append('# ---- Figure ' + figb + ': Profile curves ----')
        lines.append('fig' + figb + ', ax' + figb + ' = plt.subplots(figsize=(10, 7))')
        lines.append('_apply_style(ax' + figb + ')')

        lines.append('for _pidx, _p in enumerate(_all_profiles):')
        lines.append('    ax' + figb + '.plot(_p["x_data"], _p["y_data"], color=_p["color"], linewidth=1.5, label=f"{_p[\'coord_type\']}={_p[\'coord_value\']:.2f}")')

        lines.append('for _pidx, _ex, _ey, _is_max in _all_extremes:')
        lines.append('    if _is_max:')
        lines.append('        ax' + figb + '.plot(_ex, _ey, "r^", markersize=8)')
        lines.append('    else:')
        lines.append('        ax' + figb + '.plot(_ex, _ey, "gv", markersize=8)')

        lines.append('if len(_all_profiles) > 0:')
        lines.append('    ax' + figb + '.set_xlabel(_latex_unit(_all_profiles[0]["x_data"].__class__.__name__ and ("Time (" + _time_unit + ")" if _all_profiles[0]["coord_type"] == "position" else "Position (" + _xunit + ")")))')
        lines.append('    ax' + figb + '.set_ylabel(_latex_unit(' + repr(ylabel) + '))')
        if show_legend:
            lines.append('ax' + figb + '.legend(loc="best", fontsize=8)')
        lines.append('fig' + figb + '.tight_layout()')
        save_b = base + '_fig' + figb + '_extreme_profile.png'
        lines.append('fig' + figb + '.savefig(r"' + save_b + '", dpi=300, bbox_inches="tight")')
        lines.append('print("Saved: ' + save_b + '")')
        lines.append('')

        extra_figs = 1

        # Figure C: Derivative curves
        if show_derivative:
            fig_c = fig_n + 2
            figc = str(fig_c)
            lines.append('# ---- Figure ' + figc + ': Derivative curves ----')
            lines.append('fig' + figc + ', ax' + figc + ' = plt.subplots(figsize=(10, 7))')
            lines.append('_apply_style(ax' + figc + ')')
            lines.append('for _pidx, _p in enumerate(_all_profiles):')
            lines.append('    _xd = _p["x_data"]')
            lines.append('    _yd = _p["y_data"]')
            lines.append('    _vmask = ~np.isnan(_yd)')
            lines.append('    if np.sum(_vmask) >= 2:')
            lines.append('        _dy = np.gradient(_yd[_vmask], _xd[_vmask])')
            lines.append('        ax' + figc + '.plot(_xd[_vmask], _dy, color=_p["color"], linewidth=1.5, alpha=0.7, label=f"{_p[\'coord_type\']}={_p[\'coord_value\']:.2f}")')

            lines.append('if len(_all_profiles) > 0:')
            lines.append('    ax' + figc + '.set_xlabel(_latex_unit(_all_profiles[0]["x_data"].__class__.__name__ and ("Time (" + _time_unit + ")" if _all_profiles[0]["coord_type"] == "position" else "Position (" + _xunit + ")")))')
            lines.append('    ax' + figc + '.set_ylabel(_latex_unit("d/dx " + ' + repr(ylabel) + '))')
            if show_legend:
                lines.append('ax' + figc + '.legend(loc="best", fontsize=8)')
            lines.append('fig' + figc + '.tight_layout()')
            save_c = base + '_fig' + figc + '_extreme_derivative.png'
            lines.append('fig' + figc + '.savefig(r"' + save_c + '", dpi=300, bbox_inches="tight")')
            lines.append('print("Saved: ' + save_c + '")')
            lines.append('')
            extra_figs = 2

        return extra_figs

    @staticmethod
    def _gen_profile_extraction(lines, fig_n, op):
        start_pos = op['start_pos']
        end_pos = op['end_pos']
        var = op['var']
        xunit = op['xunit']
        coord_system = op.get('coord_system', 'XC')
        time_unit = op['time_unit']
        fign = str(fig_n)

        lines.append('_var = ' + repr(var))
        lines.append('_xunit = ' + repr(xunit))
        lines.append('_coord_system = ' + repr(coord_system))
        lines.append('_time_unit = ' + repr(time_unit))
        lines.append('_times = parser.get_time_array(unit=_time_unit)')
        lines.append('_grid = parser.get_grid_positions(unit=_xunit, coord_system=_coord_system)')
        lines.append('_data = parser.get_spatial_data_all_times(_var)')
        lines.append('if not isinstance(_data, np.ndarray): _data = np.array(_data)')
        lines.append('')

        lines.append('# Extract profile from (' + str(start_pos[0]) + ', ' + str(start_pos[1]) + ') to (' + str(end_pos[0]) + ', ' + str(end_pos[1]) + ')')
        lines.append('_n_samples = 200')
        lines.append('_xvals = np.linspace(' + repr(start_pos[0]) + ', ' + repr(end_pos[0]) + ', _n_samples)')
        lines.append('_yvals = np.linspace(' + repr(start_pos[1]) + ', ' + repr(end_pos[1]) + ', _n_samples)')
        lines.append('_x_grid_interp = np.linspace(np.min(_grid), np.max(_grid), 500)')
        lines.append('_t_grid_interp = np.linspace(np.min(_times), np.max(_times), 500)')
        lines.append('# Build 2D interpolated data grid')
        lines.append('_interp_2d = []')
        lines.append('for _i in range(len(_times)):')
        lines.append('    if _i < len(_data):')
        lines.append('        _row = _data[_i]')
        lines.append('        _n_pts = min(len(_grid), len(_row))')
        lines.append('        if _n_pts >= 2:')
        lines.append('            _f = interp1d(_grid[:_n_pts], _row[:_n_pts], kind="linear", bounds_error=False, fill_value=np.nan)')
        lines.append('            _interp_2d.append(_f(_x_grid_interp))')
        lines.append('        else:')
        lines.append('            _interp_2d.append(np.full(500, np.nan))')
        lines.append('    else:')
        lines.append('        _interp_2d.append(np.full(500, np.nan))')
        lines.append('_interp_2d = np.array(_interp_2d)')
        lines.append('_rg_interp = RegularGridInterpolator((_t_grid_interp, _x_grid_interp), _interp_2d, method="linear", bounds_error=False, fill_value=np.nan)')
        lines.append('_pts = np.column_stack([_yvals, _xvals])')
        lines.append('_profile_vals = _rg_interp(_pts)')
        lines.append('_distances = np.sqrt((_xvals - ' + repr(start_pos[0]) + ')**2 + (_yvals - ' + repr(start_pos[1]) + ')**2)')
        lines.append('ax' + fign + '.plot(_distances, _profile_vals, "b-", linewidth=1.5)')
        lines.append('ax' + fign + '.set_xlabel(_latex_unit("Distance along line"))')
        lines.append('ax' + fign + '.set_ylabel(_latex_unit(f"{_var} (color value)"))')
        lines.append('ax' + fign + '.set_title("Profile along extracted line")')

        lines.append('fig' + fign + '.tight_layout()')
        lines.append('')
