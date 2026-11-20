# MULTI1D Visualizer v2.3.1

<img src="resources/icons/multi1dvisual.png" alt="MULTI1Dvisual" width="64">

[Linux and Windows installers](#installation-guide) · [中文](README.md)

## Version Information
- **Version**: v2.3.1
- **Release Date**: June 1, 2026
- **Author**: Bo Xu
- **Major Update**: Coordinate system switching (XC/X), per-timestep grid position fix

---

## Table of Contents
- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
- [Tools Description](#tools-description)
- [Variable List](#variable-list)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Project Structure](#project-structure)
- [FAQ](#faq)
- [Changelog](#changelog)
- [License](#license)

---

## Project Overview

MULTI1D Visualizer is a specialized GUI application for visualizing output results from the MULTI1D simulation program. Key features include:

- **Direct Binary File Reading**: Read fort.10 binary files directly without needing `writeAscii.py` pre-conversion
- **Rich Visualization Types**: Three main visualization methods - Spatial Plot, Temporal Plot, and Heatmap
- **Professional Scientific Plotting**: Chart styles compliant with research paper standards
- **User-Friendly Interface**: Modern PyQt5-based GUI design
- **Complete Bilingual Support**: Interface language can be switched freely between English and Chinese
- **Powerful Data Export**: Support for multiple image and data export formats
- **Code Recording**: Record GUI operations and generate standalone Python replay scripts for batch processing

---

## Key Features

### 1. Data Source
- **Direct Reading** of fort.10 binary files
- No need for writeAscii.py pre-conversion to ASCII format
- Reuses scanFile.py parsing logic
- Support for multiple file loading and switching

### 2. Three Types of Visualization

#### Spatial Plot
Plot variables vs position/grid.

**Features**:
- Select multiple time moments for overlay display
- Customize color, line style, and line width for each moment
- Select All, Inverse Select, Clear functions
- Apply unified style to selected moments
- Support for linear/logarithmic coordinate axes
- Position unit switching (cm, um)
- Delete/restore specific moment data

**Typical Use Cases**:
- Observe spatial distribution of physical quantities at a specific time
- Compare spatial distribution changes at different times
- Analyze shock wave propagation

#### Temporal Plot
Plot variables vs time.

**Features**:
- **Global Variable Mode**: Plot global temporal variables (ENIE, ENII, ENKI, etc.)
- **Cell Mode**: Plot time evolution of specific grid cells
- Support for logarithmic axes (X/Y)
- Time unit switching (s, ns)
- Multi-cell display
- Delete/restore specific cell data

**Typical Use Cases**:
- Observe system energy evolution
- Monitor temperature/density changes at specific locations
- Analyze energy absorption and conversion processes

#### Heatmap
Plot spatiotemporal distribution heatmaps.

**Features**:
- Interpolation for handling inconsistent grid counts
- Multiple colormap options (jet, viridis, plasma, inferno, etc.)
- Logarithmic color scale
- Position markers and time markers
- Customizable color range (vmin, vmax)
- Switchable coordinate axis directions

**Typical Use Cases**:
- Observe spatiotemporal evolution of physical quantities
- Identify wavefront propagation paths
- Analyze temperature/density distribution patterns

### 3. Data Export

**Image Export**:
- Supported formats: PNG, PDF, SVG
- Adjustable DPI (default 300)
- Research paper-quality image output

**Data Export**:
- ASCII format (SCout.txt, TSout.txt)
- CSV format (for Excel, MATLAB, etc.)

### 4. Advanced Tools

#### Annotation Tool
- Line, arrow, rectangle, ellipse, text annotations
- Customizable color, line style, line width, opacity
- Annotation list management (view, delete)
- Export annotated images

#### Extreme Finder Tool
- Extract distribution curves from heatmaps
- Automatically detect maxima/minima
- Customizable extreme value search range
- Display derivative curves for auxiliary analysis
- Support for fixed position/fixed time extraction modes

#### Heatmap Profile Extractor
- Draw arbitrary lines on heatmaps
- Automatically extract data distribution along lines
- Display distribution curve plots
- Export distribution data

#### Code Recorder
- Record GUI visualization operations (file open, spatial/temporal plot, heatmap, extreme finder, profile extraction)
- Generate standalone Python replay scripts that reproduce all operations without the GUI
- Support batch processing and script customization
- Generated scripts depend only on `numpy`, `matplotlib`, `scipy`, and `Fort10Parser`
- Automatically save all figures with output matching the GUI exactly

### 5. User Interface

**Interface Features**:
- Modern PyQt5 interface
- Split layout: control panel on left, plot canvas on right
- Complete menu bar: File, View, Export, Tools, Settings, Help
- Status bar showing current operation state
- Toolbar shortcuts
- Resizable panels

**Language Support**:
- Complete bilingual English/Chinese interface
- Switch language anytime via menu
- Persistent language settings

---

## System Requirements

### Operating Systems
- Ubuntu, Debian or Fedora graphical desktop
- Windows 10/11 x64 with the setup wizard
- macOS from a source checkout

### Python Environment for Running from Source
- Python 3.7 or higher
- Python 3.8+ recommended

### Dependencies
- PyQt5 5.12+ (GUI framework)
- NumPy 1.18+ (Numerical computing)
- Matplotlib 3.1+ (Plotting)
- SciPy 1.3+ (Scientific computing)
- Pandas 1.0+ (ASCII input and table export)

### Hardware Requirements
- At least 2 GB RAM. The Linux package manager displays the disk space needed for any missing dependencies.
- Recommended: 4GB+ RAM, more memory needed for large datasets

---

## Installation Guide

| Desktop | Installer | How to install |
| --- | --- | --- |
| Ubuntu / Debian | `multi1dvisual_2.3.1-1_all.deb` | Double-click the file, open it with your system package installer and select **Install**. |
| Fedora | `multi1dvisual-2.3.1-1.noarch.rpm` | Double-click the file, open it in Software or Discover and select **Install**. |
| Windows 10/11 x64 | `MULTI1Dvisual-Setup-2.3.1-x64.exe` | Open the installer, choose the language and select a desktop shortcut if desired. Python and the runtime libraries are included. |

On Linux, the package manager installs missing dependencies from your distribution repositories. The first installation may need Internet access. Open **MULTI1Dvisual** from the applications menu. To install from a terminal, run the matching command in the download directory.

```sh
# Ubuntu / Debian
sudo apt install ./multi1dvisual_2.3.1-1_all.deb

# Fedora
sudo dnf install ./multi1dvisual-2.3.1-1.noarch.rpm
```

Open a newer package to upgrade. To uninstall, use the system software manager, `sudo apt remove multi1dvisual` or `sudo dnf remove multi1dvisual`. Settings and logs live in `~/.MULTI1D可视化工具/`.

For a source checkout, run `python -m pip install -r requirements.txt` in a virtual environment at the project root, then run `python main.py`. To build the installers, see the [packaging instructions](packaging/README.md).

---

## Quick Start

### Basic Workflow

1. **Launch Program**: Open **MULTI1Dvisual** from the applications menu or the Windows Start menu. On a Linux desktop you can also run `multi1dvisual`.
2. **Open Data File**:
   - Click "Open fort.10..." button on toolbar
   - Or via menu: File → Open fort.10
   - Or use shortcut Ctrl+O
3. **Select File**: Choose fort.10 file in file dialog
4. **Wait for Loading**: Status bar shows loading progress
5. **Select Tab**: Switch to Spatial Plot, Temporal Plot, or Heatmap tab
6. **Set Parameters**: Select variables, units, and other plot parameters
7. **Plot**: Click "Plot" button
8. **Save Results**: Use Save/Export buttons to save images or data

---

## Detailed Usage

### Spatial Plot Details

#### Interface Layout
- **Top Left**: Variable selection (choose physical quantity to plot)
- **Middle Left**: Unit settings (X-axis position unit, time unit)
- **Bottom Left**: Time moment selection (multi-select list)
- **Right**: Style settings, axis settings, action buttons
- **Bottom**: Plot area

#### Plotting Steps

1. **Select Variable**: Choose variable from dropdown (e.g., temperature T, density R)
2. **Set Units**:
   - X-axis unit: cm (centimeters) or um (micrometers)
   - Time unit: s (seconds) or ns (nanoseconds)
3. **Select Moments**:
   - Click to select single moment
   - Ctrl+click for multiple selection
   - Use "Select All", "Inverse Select", "Clear" buttons for quick selection
4. **Set Styles** (optional):
   - Select moments to style
   - Choose color, line style, line width
   - Click "Apply Styles"
5. **Set Axes** (optional):
   - Check "LOG X Axis" for logarithmic X-axis
   - Check "LOG Y Axis" for logarithmic Y-axis
   - Set X/Y range (uncheck "Auto" to manually enter values)
6. **Plot**: Click "Plot" button

#### Advanced Features

**Delete Specific Moments**:
1. Select moments in list
2. Click "Remove Selected" button
3. Grayed-out moments won't be plotted
4. Restore with "Cancel Delete"

**Quick Style Application**:
1. Select multiple moments
2. Set unified color and line style
3. Click "Apply Styles"
4. All selected moments get same style

---

### Temporal Plot Details

#### Two Plotting Modes

**Global Variable Mode**:
- Plot global temporal variables (system-level integrals)
- Variables include: ENIE (electron internal energy), ENII (ion internal energy), ENKI (kinetic energy), etc.
- Suitable for observing overall system energy evolution

**Cell Mode**:
- Plot time evolution of specific grid cells (spatial positions)
- First select spatial variable, then select cell numbers
- Suitable for observing local physical quantity changes

#### Plotting Steps

**Global Variable Mode**:
1. Select "Global Temporal Variable" radio button
2. Select global variable from dropdown
3. Set time unit (s or ns)
4. Set color, line style
5. Set axis options
6. Click "Plot"

**Cell Mode**:
1. Select "Cell Time Evolution" radio button
2. Select spatial variable from dropdown
3. Select cells in list (multi-select available)
4. Set styles (can set different styles for different cells)
5. Click "Plot"

#### Multi-Cell Management

**Select Cells**:
- Single click for single cell
- Ctrl+click for multiple selection
- Shift+click for continuous selection
- Use "Select All", "Inverse Select", "Clear" buttons

**Set Styles**:
1. Select one or more cells
2. Choose color, line style
3. Click "Apply Styles"
4. Selected cells apply new style

**Delete/Restore Cells**:
- Delete: Select cells then click "Remove Selected", cells won't show in plot
- Restore: Select deleted cells, click "Cancel Delete"

---

### Heatmap Details

#### Interface Layout
- **Top Left**: Variable selection
- **Middle Left**: Coordinate settings (direction, units)
- **Bottom Left**: Color settings (colormap, range)
- **Right**: Plot area and marker tools

#### Plotting Steps

1. **Select Variable**: Choose variable from dropdown
2. **Set Coordinate Direction**:
   - Time on X-axis: X=Time, Y=Position
   - Position on X-axis: X=Position, Y=Time
3. **Set Units**:
   - Position unit: cm or um
   - Time unit: s or ns
4. **Set Colormap**:
   - Choose colormap scheme (jet, viridis, plasma, etc.)
   - Set color range (vmin, vmax)
   - Check "Log Color" for logarithmic color mapping
5. **Plot**: Click "Plot Heatmap"

#### Add Markers

**Position Markers**:
1. Enter position values (multiple, comma-separated)
2. Click "Add Position Marks"
3. Vertical lines appear on heatmap

**Time Markers**:
1. Enter time values (multiple, comma-separated)
2. Click "Add Time Marks"
3. Horizontal lines appear on heatmap

**Clear Markers**:
- Click "Clear Position Marks" to remove all position markers
- Click "Clear Time Marks" to remove all time markers

---

## Tools Description

### Annotation Tool

**Launch**: Menu → Tools → Annotation Tool

**Steps**:
1. Launch annotation tool
2. Select annotation type from dropdown:
   - Line: Draw straight lines
   - Arrow: Draw arrows
   - Rectangle: Draw rectangles
   - Ellipse: Draw ellipses/circles
   - Text: Add text labels
3. Set style properties:
   - Color: Click color block to choose color
   - Line width: Adjust thickness
   - Line style: Select solid, dashed, etc.
   - Opacity: Adjust transparency
4. Operate on chart:
   - Line/Arrow/Rectangle/Ellipse: Drag with left mouse button
   - Text: Click location, enter text in dialog
5. Manage annotations:
   - View all annotations in right list
   - Select annotation and click "Delete Selected" to remove
   - Click "Refresh List" to update display
6. Export: Click "Export Annotated Image" to save

**Tips**:
- Annotation tool requires chart to be plotted first
- Closing dialog automatically disconnects mouse events
- Annotations saved in memory, lost when main program closes

---

### Extreme Finder Tool

**Launch**: Menu → Tools → Extreme Finder Tool

**Features**:
- Extract distribution curves along fixed position or time from heatmaps
- Automatically detect curve maxima and minima
- Display extreme value locations, values, etc.

**Steps**:
1. **Add Profile**:
   - Select extraction type:
     - Fixed Position (vs Time): Extract time variation at fixed position
     - Fixed Time (vs Position): Extract spatial variation at fixed time
   - Enter coordinate values (multiple, comma-separated)
   - Click "Add Profile"
2. **Set Extreme Range** (optional):
   - Select profile in list
   - Click "Range" cell
   - Enter range (format: min,max)
   - Click "All Range" to restore full range search
3. **Set Extreme Options**:
   - Check "Find Maxima": Detect maxima
   - Check "Find Minima": Detect minima
   - Check "Show Derivative": Display derivative for analysis
   - Check "Show Legend": Display legend
4. **Extract and Find Extremes**:
   - Click "Extract & Find Extremes" button
   - View results in "Heatmap", "Profile Curve", "Derivative Curve" tabs
5. **Save Results**:
   - Click "Save Image" to save chart
   - Click "Export Data" to export extreme data
6. **Configuration Management**:
   - Click "Save as Default" to save current settings
   - Click "Load Default" to restore saved settings

**Extreme Value Information**:
- [Maxima]/[Minima]: Extreme type
- Position/Time: Profile position or time
- Extreme at...: Coordinate location of extreme
- Value=: Extreme value

---

### Heatmap Profile Extractor

**Launch**: Menu → Tools → Heatmap Profile Extractor

**Features**:
- Draw arbitrary lines on heatmaps
- Automatically extract data distribution along lines
- Display distribution curves and values

**Steps**:
1. Ensure heatmap is plotted in Heatmap tab
2. Launch heatmap profile extractor tool
3. Click "Start Extraction" button
4. Drag on heatmap with left mouse button to draw line
5. Release mouse to auto-show distribution curve dialog
6. In dialog you can:
   - View distribution curve
   - Click "Save Image" to save distribution plot
   - Click "Export Data" to export distribution data (CSV format)
7. To extract another line:
   - Keep tool dialog open
   - Repeat steps 3-5
8. When done:
   - Click "Clear Marks" to clear extraction line on heatmap
   - Click "Stop" to stop extraction mode
   - Or simply close dialog

**Tips**:
- Extraction line shows as white line on heatmap
- Distribution curve dialog shows distance and corresponding values
- Exported CSV file contains two columns: distance and values

---

### Code Recorder Tool

**Launch**: Menu → Tools → Code Recorder Tool (shortcut Ctrl+R)

**Features**:
- Record GUI operations and generate standalone Python scripts
- Support all visualization operation types
- Generated scripts run without GUI (using Agg backend)

**Steps**:
1. Launch the Code Recorder tool
2. Click "Start Recording"
3. Perform visualization operations in the GUI (open file, plot spatial/temporal/heatmap, use extreme finder, etc.)
4. Click "Stop Recording" when done
5. Click "Generate Script" and choose save location
6. Run the generated script: `python <script_name>.py`

**Recorded Operation Types**:
- File open
- Spatial plot (variable, time moments, styles, axis settings)
- Temporal plot (global variable mode, cell mode)
- Heatmap (variable, colormap, marker lines)
- Extreme finder (profile extraction, range settings, extrema detection)
- Heatmap profile extraction (data extraction along lines)

**Tips**:
- Generated script defaults to `<data_filename>_replay.py`
- Script automatically saves all figures as PNG (300 DPI)
- Extreme finder generates multiple figures: heatmap+markers, profile curves, derivative curves

---

## Variable List

### Spatial Variables

| Variable | English Name | Description | Unit |
|----------|--------------|-------------|------|
| XC | Centroid | Centroid coordinate | cm |
| DENE | Electron Density | Electron density | cm⁻³ |
| EE | Electron Energy | Electron energy | erg |
| EI | Ion Energy | Ion energy | erg |
| P | Pressure | Pressure | dyn/cm² (internal; UI defaults to GPa, switchable to Mbar) |
| PT | Total Pressure | Total pressure | dyn/cm² (internal; UI defaults to GPa, switchable to Mbar) |
| R | Density | Density | g/cm³ |
| T | Electron Temperature | Electron temperature | eV |
| TI | Ion Temperature | Ion temperature | eV |
| ZI | Ion Charge | Ion charge number | - |
| TR | Radiation Temperature | Radiation temperature | eV |
| V | Velocity | Velocity | cm/s |
| D | Depth | Depth | cm |
| EA | Absorbed Energy | Absorbed energy | erg |
| F | Flux | Flux | erg/(cm²·s) |
| X | Position | Position | cm |
| S | Source | Source term | - |
| S+ | Positive Source | Positive source term | - |
| S- | Negative Source | Negative source term | - |

### Temporal Variables

#### Global Energy Variables
| Variable | English Name | Description | Unit |
|----------|--------------|-------------|------|
| ENIE | Electron Internal Energy | Electron internal energy | erg |
| ENII | Ion Internal Energy | Ion internal energy | erg |
| ENKI | Kinetic Energy | Kinetic energy | erg |
| ENLAS | Incident Laser Energy | Incident laser energy | erg |
| ENQUE | Absorbed Laser Energy | Absorbed laser energy | erg |
| EALFA | Alpha Particle Energy | Alpha particle energy | erg |
| ENAG | Fusion Energy/5 | Fusion energy/5 | erg |
| ENAL | Alpha Loss Energy | Alpha particle loss energy | erg |
| ENRAD | Radiation Energy | Radiation energy | erg |
| EYIELD | Neutron Yield | Neutron yield | - |

#### Boundary Spectrum Variables
| Variable | English Name | Description |
|----------|--------------|-------------|
| I-Left | Left Boundary Spectrum | Left boundary spectrum |
| I-Right | Right Boundary Spectrum | Right boundary spectrum |

#### Energy Group Variables
| Variable | English Name | Description |
|----------|--------------|-------------|
| ENRG1-4 | Energy Group 1-4 | Energy group 1-4 energy |
| ENRL1-4 | Energy Radiation 1-4 | Energy group 1-4 radiation |

---

## Keyboard Shortcuts

### File Operations
| Shortcut | Function |
|----------|----------|
| Ctrl+O | Open fort.10 file |
| Ctrl+S | Save current image |
| Ctrl+Q | Exit program |

### View Switching
| Shortcut | Function |
|----------|----------|
| Ctrl+1 | Switch to Spatial Plot tab |
| Ctrl+2 | Switch to Temporal Plot tab |
| Ctrl+3 | Switch to Heatmap tab |

### Other Operations
| Shortcut | Function |
|----------|----------|
| Ctrl+R | Open Code Recorder tool |
| Ctrl+W | Close current tab (if multiple documents) |
| F1 | Show help documentation |

---

## Project Structure

```
MULTI1Dvisual/
├── main.py                    # Program entry point
├── run.bat                    # Windows startup script
├── packaging/                 # Native Linux packages and Windows setup wizard
├── requirements.txt           # Python dependencies list
├── README.md                  # Project documentation (Chinese)
├── README_EN.md               # Project documentation (English)
│
├── legacy/                    # Original code (reference)
│   ├── scanFile.py           # fort.10 parser (original version)
│   └── writeAscii.py         # ASCII conversion tool
│
├── core/                      # Core modules
│   ├── __init__.py
│   ├── fort10_parser.py      # Fort10Parser: Parse fort.10 binary files
│   ├── data_manager.py       # DataManager: Manage multiple file instances
│   ├── plot_engine.py        # PlotEngine: Plotting engine (Matplotlib wrapper)
│   └── scout_parser.py       # ScoutParser: ASCII format parser
│
├── ui/                        # User interface modules
│   ├── __init__.py
│   ├── main_window.py        # MainWindow: Main window
│   ├── spatial_tab.py        # SpatialTab: Spatial plot tab
│   ├── temporal_tab.py       # TemporalTab: Temporal plot tab
│   ├── heatmap_tab.py        # HeatmapTab: Heatmap tab
│   ├── annotation_dialog.py  # AnnotationDialog: Annotation tool dialog
│   ├── extreme_finder_dialog.py  # ExtremeFinderDialog: Extreme finder tool
│   ├── heatmap_profile_dialog.py # HeatmapProfileDialog: Heatmap profile extractor
│   └── code_recorder_dialog.py   # CodeRecorderDialog: Code recorder tool dialog
│
└── utils/                     # Utility modules
    ├── __init__.py
    ├── config.py             # Config: Configuration management
    ├── logger.py             # Logger: Logging
    ├── language.py           # LanguageManager: Language management
    ├── code_recorder.py      # CodeRecorder: Operation recorder (singleton)
    ├── code_recorder_template.py  # ScriptGenerator: Script generation template
    └── shock_detector.py     # ShockDetector: Shock wave detection (unused)
```

---

## FAQ

### Q1: Program won't start?

**Possible causes and solutions**:

1. **Python version too old**
   - Check Python version: `python --version`
   - Ensure version ≥ 3.7, 3.8+ recommended

2. **Dependencies not installed**
   - Reinstall dependencies: `pip install PyQt5 numpy matplotlib scipy pandas`

3. **Path issues**
   - Ensure running from project root directory
   - Check working directory is correct

4. **Check logs**
   - Log file location: `~/.MULTI1D可视化工具/logs/`
   - View latest log file for detailed error information

---

### Q2: Can't open fort.10 file?

**Possible causes and solutions**:

1. **Incorrect file format**
   - Confirm file is standard fort.10 binary format
   - Check if file is corrupted
   - Try verifying file with original scanFile.py

2. **File path issues**
   - Ensure no special characters in file path
   - Try copying file to simple path

3. **Permission issues**
   - Ensure read permission for file
   - Windows users: Run program as administrator

---

### Q3: Chart display abnormal?

**Possible causes and solutions**:

1. **Data range issues**
   - Try enabling logarithmic axes
   - Adjust color range (vmin, vmax)
   - Enable "Auto" range

2. **Insufficient memory**
   - Close other applications to free memory
   - Reduce amount of data plotted
   - Try exporting data and analyzing with other tools

3. **Matplotlib backend issues**
   - Windows users: Ensure PyQt5 is installed
   - Linux users: `export MPLBACKEND=Qt5Agg`

---

### Q4: Exported image quality not high?

**Solutions**:

1. **Increase DPI setting**
   - Modify DEFAULT_SAVE_DPI in Config.py
   - Recommended setting: 300 or 600

2. **Use vector formats**
   - Export as PDF or SVG format
   - Vector formats scale losslessly

3. **Adjust chart size**
   - Save in fullscreen mode
   - Or adjust FIGURE_SIZE in Config.py

---

### Q5: Some interface still in Chinese after language switch?

**Solutions**:

1. **Restart program**
   - Some interface elements need restart to take effect
   - Close and reopen program

2. **Clear language configuration**
   - Delete `~/.MULTI1D可视化工具/language_config.json`
   - Restart program and select language

---

### Q6: How to handle large-scale data?

**Recommendations**:

1. **Selective plotting**
   - Only plot necessary moments or cells
   - Use data export function and analyze with professional tools

2. **Adjust interpolation parameters**
   - Reduce heatmap interpolation points
   - Adjust related parameters in Config.py

3. **Use data sampling**
   - Export data and use MATLAB/Python for sampling analysis

---

## Changelog

### v2.3.1 (2026-08-20)
- 🐛 Fixed MULTI-IFE fort.10 loading: files whose section-2 header is written
  once followed by a continuous stream of record values (the actual layout of
  r94/MULTI-IFE-2015 m150304.f95) previously failed to parse
  (`invalid literal for int() ...`). Both layouts — streamed values and
  repeated per-record headers — are now auto-detected and supported.

### v2.3 (June 1, 2026)
- ✨ Added coordinate system switching: XC (Cell Center) / X (Cell Edge)
- 🐛 Fixed spatial/temporal plots using only timestep-0 coordinates, now uses per-timestep coordinates
- 🐛 Fixed heatmap interpolation using only initial coordinates, now interpolates per-timestep onto common grid
- ✨ Added code recording feature: record GUI operations and generate standalone Python replay scripts
- ✨ Support recording all visualization operation types (spatial plot, temporal plot, heatmap, extreme finder, profile extraction)
- ✨ Generated scripts use Agg backend, can run without GUI
- ✨ Added keyboard shortcut Ctrl+R to open Code Recorder tool
- 🐛 Fixed extreme finder range restriction not working in replay scripts
- 🐛 Fixed replay script marker line colors not matching GUI
- 📝 Updated project structure documentation

### v2.0 (April 3, 2026)
- ✨ Added complete English/Chinese bilingual support
- ✨ Added interactive annotation tool
- ✨ Added extreme finder tool
- ✨ Added heatmap profile extractor
- 🐛 Fixed duplicate code in heatmap profile extractor
- 🐛 Fixed language switching issues in annotation tool
- 🐛 Fixed display issues in extreme finder
- 📝 Improved documentation and usage instructions

### v1.0 (March 1, 2026)
- 🎉 Initial release
- ✨ Direct reading of fort.10 binary files
- ✨ Three visualization types: Spatial Plot, Temporal Plot, Heatmap
- ✨ Data export functionality
- ✨ Basic user interface

---

## Technical Support

### Contact Information
- **Author**: Bo Xu
- **Email**: boxu25@stu.pku.edu.cn
- **Affiliation**: Peking University

### Issue Reporting
If you encounter problems or have suggestions for improvement, please contact via email.

### License
Copyright © 2026 Bo Xu

All rights reserved.

---

## Acknowledgments

- Developers of MULTI1D simulation program professor Ramis
- Contributors to PyQt5, Matplotlib, NumPy and other open source projects

---

**Thank you for using MULTI1D Visualizer!**
