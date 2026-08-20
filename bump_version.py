#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
版本号更新脚本
用法: python bump_version.py <新版本号> <日期>
示例: python bump_version.py 2.2 2026-06-01
"""

import sys
import os
import re

# 项目根目录 (脚本所在目录)
ROOT = os.path.dirname(os.path.abspath(__file__))
# 上级目录 (包含 CLAUDE.md 和外层 README)
PARENT = os.path.dirname(ROOT)

# 需要更新的文件和替换规则
# 每个条目: (文件路径, [(旧正则, 新模板), ...])
def get_replacements(old_ver, new_ver, old_date, new_date):
    """生成所有替换规则"""
    rules = []

    # === Python 源码 ===
    # config.py — APP_VERSION 和 APP_DATE
    rules.append((
        os.path.join(ROOT, 'utils', 'config.py'),
        [
            (rf'APP_VERSION = "{old_ver}"', f'APP_VERSION = "{new_ver}"'),
            (rf'APP_DATE = "{old_date}"', f'APP_DATE = "{new_date}"'),
            (rf'for MULTI1D Visualizer v{old_ver}', f'for MULTI1D Visualizer v{new_ver}'),
        ]
    ))

    # 所有 .py 文件的 docstring 注释中的版本号
    py_dirs = ['core', 'ui', 'utils', '.']
    for d in py_dirs:
        dirpath = os.path.join(ROOT, d)
        if not os.path.isdir(dirpath):
            continue
        for fname in os.listdir(dirpath):
            if fname.endswith('.py') and fname != 'bump_version.py':
                fpath = os.path.join(dirpath, fname)
                rules.append((
                    fpath,
                    [(rf'MULTI1D Visualizer v{old_ver}', f'MULTI1D Visualizer v{new_ver}')]
                ))

    # main.py 中的注释
    rules.append((
        os.path.join(ROOT, 'main.py'),
        [(rf'MULTI1D Visualizer v{old_ver}', f'MULTI1D Visualizer v{new_ver}')]
    ))

    # === Markdown 文件 ===
    # CLAUDE.md
    claude_md = os.path.join(PARENT, 'CLAUDE.md')
    if os.path.exists(claude_md):
        rules.append((claude_md, [
            (rf'MULTI1D Visualizer v{old_ver}', f'MULTI1D Visualizer v{new_ver}'),
        ]))

    # README.md (中文)
    readme_zh = os.path.join(ROOT, 'README.md')
    if os.path.exists(readme_zh):
        rules.append((readme_zh, [
            (rf'v{old_ver}', f'v{new_ver}'),
        ]))

    # README_EN.md (英文)
    readme_en = os.path.join(ROOT, 'README_EN.md')
    if os.path.exists(readme_en):
        rules.append((readme_en, [
            (rf'v{old_ver}', f'v{new_ver}'),
        ]))

    return rules


def main():
    if len(sys.argv) < 3:
        print("用法: python bump_version.py <新版本号> <日期>")
        print("示例: python bump_version.py 2.2 2026-06-01")
        sys.exit(1)

    new_ver = sys.argv[1]
    new_date = sys.argv[2]

    # 从 config.py 读取当前版本号和日期
    config_path = os.path.join(ROOT, 'utils', 'config.py')
    old_ver = None
    old_date = None
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', line)
            if m:
                old_ver = m.group(1)
            m = re.search(r'APP_DATE\s*=\s*"([^"]+)"', line)
            if m:
                old_date = m.group(1)

    if not old_ver:
        print(f"错误: 无法从 {config_path} 读取当前版本号")
        sys.exit(1)

    print(f"版本: {old_ver} -> {new_ver}")
    print(f"日期: {old_date} -> {new_date}")
    print()

    rules = get_replacements(old_ver, new_ver, old_date, new_date)
    changed_files = 0

    for fpath, replacements in rules:
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        file_changed = False
        for old_pattern, new_pattern in replacements:
            if old_pattern in new_content:
                new_content = new_content.replace(old_pattern, new_pattern)
                file_changed = True

        if file_changed:
            with open(fpath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new_content)
            rel = os.path.relpath(fpath, PARENT)
            print(f"  已更新: {rel}")
            changed_files += 1

    print(f"\n完成! 共更新 {changed_files} 个文件。")
    print(f"\n提示: 请手动在 README.md 和 README_EN.md 中添加新版本的 changelog 条目。")


if __name__ == '__main__':
    main()
