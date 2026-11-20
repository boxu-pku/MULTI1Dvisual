"""Language management for MULTI1D Visualizer"""

import json
import os


class LanguageManager:
    """语言管理器"""

    # 语言配置文件路径
    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.MULTI1D可视化工具', 'language_config.json')

    # 当前语言
    current_language = 'zh'  # 'zh' 或 'en'

    # 界面文本映射
    TEXTS = {
        'zh': {
            # 主菜单
            'app_name': 'MULTI1D可视化工具',
            'menu_file': '文件(&F)',
            'menu_open': '打开二进制文件...',
            'menu_view': '视图(&V)',
            'menu_export': '导出(&E)',
            'menu_tools': '工具(&T)',
            'menu_settings': '设置(&S)',
            'menu_help': '帮助(&H)',
            'menu_change_language': '更改语言',
            'menu_about': '关于',

            # 工具菜单
            'tool_annotation': '标注工具',
            'tool_heatmap_profile': '热图分布提取',
            'tool_extreme_finder': '极值寻找工具',
            'tool_shock_detector': '冲击波检测',

            # 设置菜单
            'settings_language': '语言设置',
            'settings_appearance': '外观设置',
            'line_style_menu': '线条样式',
            'color_menu': '颜色',
            'linestyle_menu': '线型',
            'custom_color': '自定义颜色',
            'solid_line': '实线',
            'dashed_line': '虚线',
            'dash_dot_line': '点划线',
            'dotted_line': '点线',

            # 帮助菜单
            'help_doc': '使用文档',
            'manual_open_failed': '请检查手册文件是否存在，并使用 PDF 阅读器打开。',
            'help_shortcuts': '快捷键',
            'help_about': '关于本软件',

            # 空间图标签页
            'spatial_title': '空间图',
            'variable': '变量',
            'variable_selection': '变量选择',
            'y_variable': 'Y轴变量',
            'moments': '时刻选择',
            'select_all': '全选',
            'select_inverse': '反选',
            'clear': '清空',
            'remove': '删除',
            'remove_selected': '删除选中',
            'restore': '恢复',
            'cancel_delete': '取消删除',
            'plot': '绘制',
            'export_current': '导出当前',
            'export_all': '导出全部',
            'axis_settings': '坐标设置',
            'xunit': '位置单位',
            'coord_system': '坐标系',
            'timeunit': '时间单位',
            'xlim': 'X范围',
            'ylim': 'Y范围',
            'auto': '自动',
            'color_settings': '颜色设置',
            'style_settings': '样式设置',
            'colormap': '颜色映射',
            'color': '颜色',
            'line_style': '线型',
            'line_width': '线宽',
            'apply': '应用',
            'vmin': '最小值',
            'vmax': '最大值',
            'log_color': '对数色标',
            'clear_plot': '清空画布',
            'no_data': '未加载数据',
            'log_x_axis': 'LOG X轴',
            'log_y_axis': 'LOG Y轴',

            # 时间图标签页
            'temporal_title': '时间图',
            'global_var': '全局时间变量',
            'spatial_var': '空间变量',
            'select_cell': '选择网格',
            'unit': '单位',
            'apply_style': '应用样式',
            'apply_styles': '应用样式',

            # 热图标签页
            'heatmap_title': '热图',
            'coord_direction': '坐标方向',
            'time_x_axis': '横轴: 时间  纵轴: 位置',
            'pos_x_axis': '横轴: 位置  纵轴: 时间',
            'mark_positions': '位置标记',
            'mark_times': '时间标记',

            # 极值寻找工具
            'extreme_finder_title': '极值寻找工具',
            'extreme_help': '''1. 点击"添加Profile"添加检测线
2. 在列表中选中Profile可编辑其极值范围
3. 点击"提取并寻找极值"开始分析
4. 可保存当前配置为默认配置''',
            'add_profile': '添加Profile',
            'extract_type': '提取类型',
            'fixed_position': '固定位置 (沿时间)',
            'fixed_time': '固定时间 (沿位置)',
            'coord_value': '坐标值',
            'coord_value_placeholder': '如: 100, 500, 1000',
            'profile_list': 'Profile列表与极值范围',
            'profile_col': 'Profile',
            'range_col': '极值范围',
            'action_col': '操作',
            'all_ranges': '全范围',
            'remove_selected': '删除选中',
            'clear_all': '清空全部',
            'extreme_options': '极值检测选项',
            'find_max': '寻找极大值',
            'find_min': '寻找极小值',
            'show_derivative': '显示导数曲线',
            'show_legend': '显示图例',
            'default_config': '默认配置',
            'save_config': '保存为默认配置',
            'load_config': '加载默认配置',
            'extreme_info': '检测到的极值',
            'extract_and_find': '提取并寻找极值',
            'save_image': '保存当前图片',
            'save_all_images': '保存所有图片',
            'export_data': '导出数据...',
            'close': '关闭',
            'no_extreme': '未检测到极值',
            'maxima': '【极大值】',
            'minima': '【极小值】',
            'position_at': '位置=',
            'extreme_at_time': '极值在 时间=',
            'extreme_at_pos': '极值在 位置=',
            'time_at': '时间=',
            'value_equals': '值=',
            'heatmap_tab': '热图',
            'profile_curve': '分布曲线',
            'derivative_curve': '导数曲线',
            'config_saved_to': '配置已保存至',
            'save_config_failed': '保存配置失败',
            'config_loaded': '已加载默认配置',
            'load_config_failed': '加载配置失败',
            'image_saved_to': '图片已保存至',
            'data_exported_to': '数据已导出至',
            'extract_distribution_failed': '提取分布失败',
            'position_value_out_of_range': '位置值超出范围',
            'time_value_out_of_range': '时间值超出范围',
            'parse_range_failed': '解析范围失败',
            'plot_heatmap_failed_extreme': '绘制热图失败',

            # 标注工具
            'annotation_title': '标注工具',
            'annotation_help': '''1. 选择标注工具
2. 设置样式属性
3. 在画布上操作:
   - 直线/箭头/矩形/椭圆: 拖动鼠标
   - 文字: 单击位置输入''',
            'annotation_help_en': '''1. Select annotation tool
2. Set style properties
3. Operate on canvas:
   - Line/Arrow/Rectangle/Ellipse: Drag mouse
   - Text: Click to input''',

            # 热图分布提取
            'heatmap_profile_title': '热图分布提取工具',
            'heatmap_profile_help': '''1. 确保已绘制热图
2. 点击"开始提取"按钮
3. 在热图上拖拽绘制直线
4. 释放鼠标后自动显示分布曲线''',
            'heatmap_profile_help_en': '''1. Make sure heatmap is plotted
2. Click "Start Extraction" button
3. Drag to draw a line on heatmap
4. Release mouse to auto-show distribution curve''',
            'instructions': '使用说明',
            'status_ready': '状态: 就绪',
            'start_extraction': '开始提取',
            'stop': '停止',
            'clear_marks': '清除标记',
            'annotation_tools': '标注工具',
            'type': '类型',
            'line_width': '线宽',
            'opacity': '透明度',
            'text_style': '文字样式',
            'font_size': '字号',
            'select_font': '选择字体',
            'clear_all_annotations': '清除所有标注',
            'export_annotated_image': '导出带标注图片',
            'annotation_list': '标注列表',
            'delete_selected': '删除选中',
            'refresh_list': '刷新列表',

            # 通用
            'yes': '是',
            'no': '否',
            'ok': '确定',
            'cancel': '取消',
            'save': '保存',
            'open': '打开',
            'close': '关闭',
            'export': '导出',
            'delete': '删除',
            'clear': '清空',
            'edit': '编辑',
            'add': '添加',
            'remove': '删除',
            'apply': '应用',
            'language_changed': '语言已更改，请重启程序以应用所有更改',
            'language_saved': '语言设置已保存',

            # 对话框消息
            'error': '错误',
            'warning': '警告',
            'info': '提示',
            'success': '成功',
            'load_file_first': '请先加载数据文件',
            'no_canvas_available': '当前标签页没有可用的绘图画布，请先绘制图形',
            'switch_to_heatmap_first': '请先切换到热图标签页并绘制热图',
            'plot_heatmap_first': '请先绘制热图',
            'cannot_load_file': '无法加载文件',
            'export_failed': '导出失败',
            'data_exported_successfully': '数据已成功导出',
            'need_pandas_for_csv': '需要安装pandas库才能导出CSV',
            'current_tab_no_save_support': '当前标签页不支持保存图片',
            'extremes_not_found': '未检测到极值',
            'select_at_least_one_moment': '请选择至少一个时刻',
            'select_at_least_one_cell': '请选择至少一个网格',
            'select_variable': '请选择变量',
            'plot_heatmap_failed': '绘制热图失败',
            'cannot_get_data': '无法获取数据',
            'no_data_loaded': '没有加载数据',
            'select_var_and_plot_heatmap_first': '请先选择变量并绘制热图',
            'cannot_get_heatmap_data': '无法获取热图数据',
            'enter_coord_value': '请输入坐标值',
            'enter_valid_coord_value': '请输入有效的坐标值',
            'add_profile_first': '请先添加Profile',
            'no_data_to_export': '没有可导出的数据',
            'no_data_to_plot': '没有可绘制的数据',
            'cannot_get_data_deleted': '无法获取数据（可能全部被删除）',
            'select_moments_to_export': '请选择要导出的时刻',
            'select_cells_to_export': '请选择要导出的网格',

            # Temporal Tab additional
            'plot_mode': '绘图模式',
            'cell_time_evolution': '网格时间演化',
            'assign_mid_color': '按MID分配颜色',
            'no_mid_data': '当前文件没有 MID（材料标识）数据。\n仅 ASCII (.case) 格式可用。',
            'mid_color_assigned': '已按MID分配颜色',
            'restore_selected_plot': '恢复选中（恢复绘制）',
            'global_mode_style_note': '全局模式: 样式将在绘制时应用',
            'drawn_curve': '已绘制',
            'time_evolution_curve': '时间演化曲线',
            'drawn_curves': '已绘制',
            'curves': '条曲线',
            'image_saved': '图片已保存:',
            'data_exported': '数据已导出:',
            'export_failed_error': '导出失败:',
            'marked_cells_not_plotting': '已标记',
            'cells_not_plotting': '个网格为不绘制',
            'restored_cells': '已恢复',
            'cells': '个网格',
            'save_image_title': '保存图片',
            'png_files': 'PNG图片 (*.png)',
            'pdf_files': 'PDF文件 (*.pdf)',
            'all_files': '所有文件 (*)',
            'export_data_title': '导出数据',
            'csv_files': 'CSV文件 (*.csv)',
            'line_style_settings': '线条样式',

            # Annotation Dialog additional
            'select_color': '选择颜色',
            'confirm': '确认',
            'confirm_clear_all': '确定要清除所有标注吗？',
            'confirm_clear_title': '确认',
            'export_annotated_image_title': '导出带标注图片',
            'svg_files': 'SVG文件 (*.svg)',
            'image_exported_to': '图片已导出至:',
            'success': '成功',
            'enter_text_title': '输入文字',
            'enter_text_prompt': '请输入标注文字:',

            # 代码录制工具
            'tool_code_recorder': '记录代码',
            'start_recording': '开始录制',
            'stop_recording': '停止录制',
            'generate_script': '生成脚本',
            'clear_recording': '清除记录',
            'recorded_operations': '已记录操作',
            'status_recording': '状态: 正在录制...',
            'status_stopped_with_data': '状态: 录制已停止（有数据）',
            'status_ready': '状态: 就绪',
            'no_operations_to_generate': '没有可生成的操作记录',
            'script_generated_to': '脚本已生成至',
            'script_generation_failed': '脚本生成失败',

            # 冲击波检测工具
            'shock_detector_title': '冲击波检测工具',
            'shock_help': '''1. 选择要检测的物理变量（通常为密度R）
2. 设置参考时刻和搜索范围以锁定冲击波位置
3. 设置连续性约束（相邻时刻最大位置偏差）
4. 点击"开始检测"进行冲击波轨迹追踪
5. 冲击波轨迹将显示在热图上
6. 使用"可视化时刻"下拉框查看特定时刻的密度分布''',
            'visualization_settings': '可视化设置',
            'visualize_time': '可视化时刻',
            'auto_update_visualization': '自动更新可视化',
            'auto_update_vis_tooltip': '检测后自动更新可视化曲线',
            'reference_time_settings': '参考时刻设置',
            'reference_time': '参考时刻',
            'search_range': '搜索范围',
            'time_step': '时间步',
            'add_ref_time': '添加参考',
            'remove_ref_time': '移除参考',
            'min_value': '最小值',
            'max_value': '最大值',
            'continuity_constraint': '连续性约束',
            'max_position_deviation': '最大位置偏差',
            'allow_multiple_shocks': '允许多条冲击波',
            'profile_range_settings': '密度分布曲线范围',
            'density_value': '密度值',
            'detection_options': '检测选项',
            'density_threshold': '密度变化阈值',
            'show_derivative_curve': '显示导数曲线',
            'show_trajectory': '显示轨迹',
            'velocity_curve': '冲击波速度',
            'velocity_range': '速度时间范围',
            'velocity_range_tooltip': '仅计算指定时间区间内的冲击波速度',
            'enable_smoothing': '启用平滑',
            'smoothing_params': '平滑参数',
            'window_size': '窗口大小',
            'poly_order': '多项式阶数',
            'hugoniot_relation': 'Hugoniot关系',
            'pre_shock_pressure': '冲击前压强 P₀',
            'pre_shock_density': '冲击前密度 ρ₀',
            'default_config': '默认配置',
            'detection_results': '检测结果',
            'no_results_yet': '暂无检测结果',
            'start_detection': '开始检测',
            'save_heatmap': '保存热图',
            'save_trajectory': '保存轨迹',
            'no_shock_detected': '未检测到冲击波',
            'shock_detected_info': '检测到 {n} 个冲击波位置点\n起始: t={first_t}, pos={first_p:.1f} um\n终止: t={last_t}, pos={last_p:.1f} um',
            'config_saved': '配置已保存至',
            'no_peaks_found_at_ref_time': '参考时刻未找到峰值',
            'no_peaks_in_search_range': '搜索范围内未找到峰值',
            'select_variable_first': '请先选择变量',
            'cannot_get_data': '无法获取数据',
            'detection_failed': '检测失败',
            'no_trajectory_to_save': '没有可保存的轨迹数据',
            'save_failed': '保存失败',
            'trajectory_saved': '轨迹数据已保存至',
            'density_profile': '密度分布',
            'help': '使用说明',
            'shock_front': '冲击波前',
        },

        'en': {
            # Main Menu
            'app_name': 'MULTI1D Visualizer',
            'menu_file': 'File(&F)',
            'menu_open': 'Open Binary File...',
            'menu_view': 'View(&V)',
            'menu_export': 'Export(&E)',
            'menu_tools': 'Tools(&T)',
            'menu_settings': 'Settings(&S)',
            'menu_help': 'Help(&H)',
            'menu_change_language': 'Change Language',
            'menu_about': 'About',

            # Tools Menu
            'tool_annotation': 'Annotation Tool',
            'tool_heatmap_profile': 'Heatmap Profile Extractor',
            'tool_extreme_finder': 'Extreme Finder Tool',
            'tool_shock_detector': 'Shock Wave Detector',

            # Settings Menu
            'settings_language': 'Language Settings',
            'settings_appearance': 'Appearance Settings',
            'line_style_menu': 'Line Style',
            'color_menu': 'Color',
            'linestyle_menu': 'Line Type',
            'custom_color': 'Custom Color',
            'solid_line': 'Solid',
            'dashed_line': 'Dashed',
            'dash_dot_line': 'Dash-dot',
            'dotted_line': 'Dotted',

            # Help Menu
            'help_doc': 'Documentation',
            'manual_open_failed': 'Check that the manual exists and open it with a PDF reader.',
            'help_shortcuts': 'Keyboard Shortcuts',
            'help_about': 'About',

            # Spatial Tab
            'spatial_title': 'Spatial Plot',
            'variable': 'Variable',
            'variable_selection': 'Variable Selection',
            'y_variable': 'Y Variable',
            'moments': 'Time Moments',
            'select_all': 'Select All',
            'select_inverse': 'Inverse Select',
            'clear': 'Clear',
            'remove': 'Remove',
            'remove_selected': 'Remove Selected',
            'restore': 'Restore',
            'cancel_delete': 'Cancel Delete',
            'plot': 'Plot',
            'export_current': 'Export Current',
            'export_all': 'Export All',
            'axis_settings': 'Axis Settings',
            'xunit': 'Position Unit',
            'coord_system': 'Coord System',
            'timeunit': 'Time Unit',
            'xlim': 'X Range',
            'ylim': 'Y Range',
            'auto': 'Auto',
            'color_settings': 'Color Settings',
            'style_settings': 'Style Settings',
            'colormap': 'Colormap',
            'color': 'Color',
            'line_style': 'Line Style',
            'line_width': 'Line Width',
            'apply': 'Apply',
            'vmin': 'Min',
            'vmax': 'Max',
            'log_color': 'Log Color',
            'clear_plot': 'Clear Plot',
            'no_data': 'No Data Loaded',

            # Temporal Tab
            'temporal_title': 'Temporal Plot',
            'global_var': 'Global Temporal Variable',
            'spatial_var': 'Spatial Variable',
            'select_cell': 'Select Cell',
            'unit': 'Unit',
            'apply_style': 'Apply Style',
            'apply_styles': 'Apply Styles',
            'log_x_axis': 'Log X Axis',
            'log_y_axis': 'Log Y Axis',

            # Heatmap Tab
            'heatmap_title': 'Heatmap',
            'coord_direction': 'Coordinate Direction',
            'time_x_axis': 'X: Time  Y: Position',
            'pos_x_axis': 'X: Position  Y: Time',
            'mark_positions': 'Position Marks',
            'mark_times': 'Time Marks',

            # Extreme Finder Tool
            'extreme_finder_title': 'Extreme Finder Tool',
            'extreme_help': '''1. Click "Add Profile" to add detection lines
2. Select a profile to edit its extreme value range
3. Click "Extract & Find Extremes" to start analysis
4. Save current configuration as default''',
            'add_profile': 'Add Profile',
            'extract_type': 'Extraction Type',
            'fixed_position': 'Fixed Position (vs Time)',
            'fixed_time': 'Fixed Time (vs Position)',
            'coord_value': 'Position Value',
            'coord_value_placeholder': 'e.g. 100, 500, 1000',
            'profile_list': 'Profile List & Ranges',
            'profile_col': 'Profile',
            'range_col': 'Range',
            'action_col': 'Action',
            'all_ranges': 'All Range',
            'remove_selected': 'Remove Selected',
            'clear_all': 'Clear All',
            'extreme_options': 'Extreme Options',
            'find_max': 'Find Maxima',
            'find_min': 'Find Minima',
            'show_derivative': 'Show Derivative',
            'show_legend': 'Show Legend',
            'default_config': 'Default Config',
            'save_config': 'Save as Default',
            'load_config': 'Load Default',
            'extreme_info': 'Detected Extremes',
            'extract_and_find': 'Extract & Find Extremes',
            'save_image': 'Save Current Image',
            'save_all_images': 'Save All Images',
            'export_data': 'Export Data...',
            'close': 'Close',
            'no_extreme': 'No Extremes Detected',
            'maxima': '[Maxima]',
            'minima': '[Minima]',
            'position_at': 'Position=',
            'extreme_at_time': 'Extreme at Time=',
            'extreme_at_pos': 'Extreme at Position=',
            'time_at': 'Time=',
            'value_equals': 'Value=',
            'heatmap_tab': 'Heatmap',
            'profile_curve': 'Profile Curve',
            'derivative_curve': 'Derivative Curve',
            'config_saved_to': 'Configuration saved to',
            'save_config_failed': 'Failed to save configuration',
            'config_loaded': 'Default configuration loaded',
            'load_config_failed': 'Failed to load configuration',
            'image_saved_to': 'Image saved to',
            'data_exported_to': 'Data exported to',
            'extract_distribution_failed': 'Failed to extract distribution',
            'position_value_out_of_range': 'Position value out of range',
            'time_value_out_of_range': 'Time value out of range',
            'parse_range_failed': 'Failed to parse range',
            'plot_heatmap_failed_extreme': 'Failed to plot heatmap',

            # Annotation Tool
            'annotation_title': 'Annotation Tool',
            'annotation_help_en': '''1. Select annotation tool
2. Set style properties
3. Operate on canvas:
   - Line/Arrow/Rectangle/Ellipse: Drag mouse
   - Text: Click to input''',

            # Heatmap Profile Extractor
            'heatmap_profile_title': 'Heatmap Profile Extractor',
            'heatmap_profile_help_en': '''1. Make sure heatmap is plotted
2. Click "Start Extraction" button
3. Drag to draw a line on heatmap
4. Release mouse to auto-show distribution curve''',
            'instructions': 'Instructions',
            'status_ready': 'Status: Ready',
            'start_extraction': 'Start Extraction',
            'stop': 'Stop',
            'clear_marks': 'Clear Marks',
            'annotation_tools': 'Annotation Tools',
            'type': 'Type',
            'line_width': 'Line Width',
            'opacity': 'Opacity',
            'text_style': 'Text Style',
            'font_size': 'Font Size',
            'select_font': 'Select Font',
            'clear_all_annotations': 'Clear All Annotations',
            'export_annotated_image': 'Export Annotated Image',
            'annotation_list': 'Annotation List',
            'delete_selected': 'Delete Selected',
            'refresh_list': 'Refresh List',

            # Common
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'cancel': 'Cancel',
            'save': 'Save',
            'open': 'Open',
            'close': 'Close',
            'export': 'Export',
            'delete': 'Delete',
            'clear': 'Clear',
            'edit': 'Edit',
            'add': 'Add',
            'remove': 'Remove',
            'apply': 'Apply',
            'language_changed': 'Language changed. Please restart the application for full changes.',
            'language_saved': 'Language settings saved',

            # Dialog messages
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'success': 'Success',
            'load_file_first': 'Please load data file first',
            'no_canvas_available': 'Current tab has no available plot canvas, please plot graphics first',
            'switch_to_heatmap_first': 'Please switch to Heatmap tab and plot heatmap first',
            'plot_heatmap_first': 'Please plot heatmap first',
            'cannot_load_file': 'Cannot load file',
            'export_failed': 'Export failed',
            'data_exported_successfully': 'Data exported successfully',
            'need_pandas_for_csv': 'Need to install pandas library to export CSV',
            'current_tab_no_save_support': 'Current tab does not support saving image',
            'extremes_not_found': 'No extremes detected',
            'select_at_least_one_moment': 'Please select at least one moment',
            'select_at_least_one_cell': 'Please select at least one cell',
            'select_variable': 'Please select a variable',
            'plot_heatmap_failed': 'Plot heatmap failed',
            'cannot_get_data': 'Cannot get data',
            'no_data_loaded': 'No data loaded',
            'select_var_and_plot_heatmap_first': 'Please select variable and plot heatmap first',
            'cannot_get_heatmap_data': 'Cannot get heatmap data',
            'enter_coord_value': 'Please enter coordinate value',
            'enter_valid_coord_value': 'Please enter valid coordinate value',
            'add_profile_first': 'Please add profile first',
            'no_data_to_export': 'No data to export',
            'no_data_to_plot': 'No data to plot',
            'cannot_get_data_deleted': 'Cannot get data (possibly all deleted)',
            'select_moments_to_export': 'Please select moments to export',
            'select_cells_to_export': 'Please select cells to export',

            # Temporal Tab additional
            'plot_mode': 'Plot Mode',
            'cell_time_evolution': 'Cell Time Evolution',
            'assign_mid_color': 'Color by Material (MID)',
            'no_mid_data': 'No MID (material ID) data in this file.\nOnly ASCII (.case) format is supported.',
            'mid_color_assigned': 'Colors assigned by MID',
            'restore_selected_plot': 'Restore Selected (Restore Plotting)',
            'global_mode_style_note': 'Global mode: Style will be applied when plotting',
            'drawn_curve': 'Drawn',
            'time_evolution_curve': 'time evolution curve',
            'drawn_curves': 'Drawn',
            'curves': 'curves',
            'image_saved': 'Image saved:',
            'data_exported': 'Data exported:',
            'export_failed_error': 'Export failed:',
            'marked_cells_not_plotting': 'Marked',
            'cells_not_plotting': 'cells as not plotting',
            'restored_cells': 'Restored',
            'cells': 'cells',
            'save_image_title': 'Save Image',
            'png_files': 'PNG Images (*.png)',
            'pdf_files': 'PDF Files (*.pdf)',
            'all_files': 'All Files (*)',
            'export_data_title': 'Export Data',
            'csv_files': 'CSV Files (*.csv)',
            'line_style_settings': 'Line Style Settings',

            # Annotation Dialog additional
            'select_color': 'Select Color',
            'confirm': 'Confirm',
            'confirm_clear_all': 'Are you sure to clear all annotations?',
            'confirm_clear_title': 'Confirm',
            'export_annotated_image_title': 'Export Annotated Image',
            'svg_files': 'SVG Files (*.svg)',
            'image_exported_to': 'Image exported to:',
            'success': 'Success',
            'enter_text_title': 'Enter Text',
            'enter_text_prompt': 'Please enter annotation text:',

            # Code Recorder Tool
            'tool_code_recorder': 'Code Recorder',
            'start_recording': 'Start Recording',
            'stop_recording': 'Stop Recording',
            'generate_script': 'Generate Script',
            'clear_recording': 'Clear Recording',
            'recorded_operations': 'Recorded operations',
            'status_recording': 'Status: Recording...',
            'status_stopped_with_data': 'Status: Stopped (has data)',
            'status_ready': 'Status: Ready',
            'no_operations_to_generate': 'No operations to generate',
            'script_generated_to': 'Script generated to',
            'script_generation_failed': 'Script generation failed',

            # Shock Wave Detector Tool
            'shock_detector_title': 'Shock Wave Detector',
            'shock_help': '''1. Select physical variable to detect (usually density R)
2. Set reference time and search range to lock shock position
3. Set continuity constraint (max position deviation between adjacent times)
4. Click "Start Detection" to track shock trajectory
5. Shock trajectory will be displayed on heatmap
6. Use "Visualization Time" dropdown to view density distribution at specific moments''',
            'visualization_settings': 'Visualization Settings',
            'visualize_time': 'Visualization Time',
            'auto_update_visualization': 'Auto Update Visualization',
            'auto_update_vis_tooltip': 'Automatically update visualization curves after detection',
            'reference_time_settings': 'Reference Time Settings',
            'reference_time': 'Reference Time',
            'search_range': 'Search Range',
            'time_step': 'Time Step',
            'add_ref_time': 'Add Ref',
            'remove_ref_time': 'Remove Ref',
            'min_value': 'Min',
            'max_value': 'Max',
            'continuity_constraint': 'Continuity Constraint',
            'max_position_deviation': 'Max Position Deviation',
            'allow_multiple_shocks': 'Allow Multiple Shocks',
            'profile_range_settings': 'Profile Range Settings',
            'density_value': 'Density Value',
            'detection_options': 'Detection Options',
            'density_threshold': 'Density Threshold',
            'show_derivative_curve': 'Show Derivative Curve',
            'show_trajectory': 'Show Trajectory',
            'velocity_curve': 'Shock Velocity',
            'velocity_range': 'Velocity Time Range',
            'velocity_range_tooltip': 'Only calculate velocity within the specified time range',
            'enable_smoothing': 'Enable Smoothing',
            'smoothing_params': 'Smoothing Parameters',
            'window_size': 'Window Size',
            'poly_order': 'Poly Order',
            'hugoniot_relation': 'Hugoniot Relation',
            'pre_shock_pressure': 'Pre-shock Pressure P₀',
            'pre_shock_density': 'Pre-shock Density ρ₀',
            'default_config': 'Default Config',
            'detection_results': 'Detection Results',
            'no_results_yet': 'No results yet',
            'start_detection': 'Start Detection',
            'save_heatmap': 'Save Heatmap',
            'save_trajectory': 'Save Trajectory',
            'no_shock_detected': 'No shock detected',
            'shock_detected_info': 'Detected {n} shock front points\nStart: t={first_t}, pos={first_p:.1f} um\nEnd: t={last_t}, pos={last_p:.1f} um',
            'config_saved': 'Configuration saved to',
            'no_peaks_found_at_ref_time': 'No peaks found at reference time',
            'no_peaks_in_search_range': 'No peaks found in search range',
            'select_variable_first': 'Please select a variable first',
            'cannot_get_data': 'Cannot get data',
            'detection_failed': 'Detection failed',
            'no_trajectory_to_save': 'No trajectory data to save',
            'save_failed': 'Save failed',
            'trajectory_saved': 'Trajectory data saved to',
            'density_profile': 'Density Profile',
            'help': 'Instructions',
            'shock_front': 'Shock Front',
        },
    }

    @classmethod
    def get_text(cls, key):
        """获取指定键的文本"""
        return cls.TEXTS.get(cls.current_language, {}).get(key, key)

    @classmethod
    def set_language(cls, language):
        """设置当前语言"""
        if language in cls.TEXTS:
            cls.current_language = language

    @classmethod
    def get_current_language(cls):
        """获取当前语言"""
        return cls.current_language

    @classmethod
    def save_language_config(cls):
        """保存语言配置"""
        try:
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            config = {
                'language': cls.current_language
            }
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存语言配置失败: {e}")

    @classmethod
    def load_language_config(cls):
        """加载语言配置"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cls.current_language = config.get('language', 'zh')
                    return True
        except Exception as e:
            print(f"加载语言配置失败: {e}")
        return False

    @classmethod
    def get_available_languages(cls):
        """获取可用语言列表"""
        return [
            ('zh', '简体中文'),
            ('en', 'English')
        ]

    @classmethod
    def get_language_name(cls, code):
        """获取语言名称"""
        for lang_code, lang_name in cls.get_available_languages():
            if lang_code == code:
                return lang_name
        return code

    @classmethod
    def refresh_ui_texts(cls):
        """刷新所有UI文本（在语言切换后调用）"""
        # 这个方法会在语言切换后由主程序调用
        # 具体实现在各个UI类中
        pass
