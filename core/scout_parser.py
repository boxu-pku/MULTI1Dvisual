"""
Parser for MULTI1D output files: Scout.txt and TSout.txt
Supports spatial data (SCout.txt) and time-series data (TSout.txt)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SpatialData:
    """Container for spatial data at a specific time step"""
    time: float
    cell_indices: np.ndarray  # Grid cell indices (0, 1, 2, ...)
    data: Dict[str, np.ndarray]  # Variable values for each cell


@dataclass
class TemporalData:
    """Container for time-series data"""
    times: np.ndarray
    variables: Dict[str, np.ndarray]


class ScoutParser:
    """Parser for SCout.txt (spatial curves) files"""

    # Variable names as they appear in SCout.txt header
    SPATIAL_VAR_ORDER = ['XC', 'DENE', 'EE', 'EI', 'P', 'PT', 'R', 'T',
                          'TI', 'ZI', 'TR', 'V', 'D', 'EA', 'F', 'X', 'S',
                          'Splus', 'Smin']

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath
        self.spatial_data: List[SpatialData] = []  # List of time steps
        self.variable_names: List[str] = self.SPATIAL_VAR_ORDER.copy()
        self.loaded = False

    def parse(self, filepath: Optional[str] = None) -> bool:
        """
        Parse SCout.txt file

        File format:
        - Line 1-2: Comments
        - Line 3: Variable names header
        - Line 4: Time value
        - Line 5-N: N lines of data (N = number of cells)
        - Empty line
        - Line N+2: Next time value
        - ... (repeats)
        """
        if filepath:
            self.filepath = filepath

        if not self.filepath:
            raise ValueError("No filepath provided")

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Skip first 2 lines (comments)
            idx = 2

            # Parse variable names line
            header_line = lines[idx].strip()
            if header_line.startswith('#'):
                header_line = header_line[1:].strip()
            self.variable_names = header_line.split('\t')
            idx += 1

            # Parse time blocks
            self.spatial_data = []

            while idx < len(lines):
                line = lines[idx].strip()

                # Skip empty lines
                if not line:
                    idx += 1
                    continue

                # Try to parse as time value
                try:
                    time_val = float(line)
                    idx += 1
                except ValueError:
                    # Not a time value, skip
                    idx += 1
                    continue

                # Read data rows for this time step
                cell_data = {var: [] for var in self.variable_names}

                while idx < len(lines):
                    data_line = lines[idx].strip()

                    if not data_line:
                        # Empty line marks end of this time step
                        idx += 1
                        break

                    # Parse data row
                    values = data_line.split('\t')
                    for i, var in enumerate(self.variable_names):
                        if i < len(values):
                            try:
                                cell_data[var].append(float(values[i]))
                            except ValueError:
                                cell_data[var].append(0.0)

                    idx += 1

                # Convert to numpy arrays
                n_cells = len(next(iter(cell_data.values()), []))
                if n_cells > 0:
                    for var in self.variable_names:
                        cell_data[var] = np.array(cell_data[var])

                    # Add spatial data for this time step
                    self.spatial_data.append(SpatialData(
                        time=time_val,
                        cell_indices=np.arange(n_cells),
                        data=cell_data
                    ))

            self.loaded = True
            return True

        except Exception as e:
            print(f"Error parsing SCout.txt: {e}")
            return False

    def get_time_steps(self) -> np.ndarray:
        """Get all time step values"""
        return np.array([sd.time for sd in self.spatial_data])

    def get_num_cells(self, time_idx: int = 0) -> int:
        """Get number of cells at a given time step"""
        if 0 <= time_idx < len(self.spatial_data):
            return len(self.spatial_data[time_idx].cell_indices)
        return 0

    def get_spatial_data(self, variable: str, time_idx: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Get spatial data for a variable at a specific time step

        Returns: (cell_indices, values) or None if invalid
        """
        if 0 <= time_idx < len(self.spatial_data):
            if variable in self.spatial_data[time_idx].data:
                return (
                    self.spatial_data[time_idx].cell_indices,
                    self.spatial_data[time_idx].data[variable]
                )
        return None

    def get_time_series(self, variable: str, cell_idx: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Get time series data for a variable at a specific cell

        Returns: (times, values) or None if invalid
        """
        times = []
        values = []

        for sd in self.spatial_data:
            if cell_idx < len(sd.cell_indices):
                if variable in sd.data:
                    times.append(sd.time)
                    values.append(sd.data[variable][cell_idx])

        if times:
            return np.array(times), np.array(values)
        return None

    def get_available_variables(self) -> List[str]:
        """Get list of available variable names"""
        return self.variable_names


class TSParser:
    """Parser for TSout.txt (time-series) files"""

    # Variable names as they appear in TSout.txt header
    TEMPORAL_VAR_ORDER = ['t', 'Enie', 'Enii', 'Enki', 'Enlas', 'Enque',
                           'Ealpha', 'Enag', 'Enal', 'Enrad', 'Eyield',
                           'ILeft', 'IRight', 'Enrg1', 'Enrg2', 'Enrg3',
                           'Enrg4', 'Enrl1', 'Enrl2', 'Enrl3', 'Enrl4']

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath
        self.temporal_data: Optional[TemporalData] = None
        self.variable_names: List[str] = self.TEMPORAL_VAR_ORDER.copy()
        self.loaded = False

    def parse(self, filepath: Optional[str] = None) -> bool:
        """
        Parse TSout.txt file

        File format:
        - Line 1: Comment
        - Line 2: Variable names header
        - Line 3+: Data rows (each row is one time step)
        """
        if filepath:
            self.filepath = filepath

        if not self.filepath:
            raise ValueError("No filepath provided")

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Skip first line (comment)
            idx = 1

            # Parse variable names line
            header_line = lines[idx].strip()
            if header_line.startswith('#'):
                header_line = header_line[1:].strip()
            self.variable_names = header_line.split('\t')
            idx += 1

            # Parse data rows
            data_dict = {var: [] for var in self.variable_names}

            while idx < len(lines):
                line = lines[idx].strip()

                if not line:
                    idx += 1
                    continue

                values = line.split('\t')
                for i, var in enumerate(self.variable_names):
                    if i < len(values):
                        try:
                            data_dict[var].append(float(values[i]))
                        except ValueError:
                            data_dict[var].append(0.0)

                idx += 1

            # Convert to numpy arrays
            for var in self.variable_names:
                data_dict[var] = np.array(data_dict[var])

            self.temporal_data = TemporalData(
                times=data_dict['t'] if 't' in data_dict else np.array([]),
                variables=data_dict
            )

            self.loaded = True
            return True

        except Exception as e:
            print(f"Error parsing TSout.txt: {e}")
            return False

    def get_time_series(self, variable: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Get time series data for a variable

        Returns: (times, values) or None if invalid
        """
        if not self.loaded or not self.temporal_data:
            return None

        if variable in self.temporal_data.variables:
            return (
                self.temporal_data.times,
                self.temporal_data.variables[variable]
            )
        return None

    def get_times(self) -> np.ndarray:
        """Get all time values"""
        if self.temporal_data:
            return self.temporal_data.times
        return np.array([])

    def get_available_variables(self) -> List[str]:
        """Get list of available variable names (excluding 't' for plotting)"""
        if 't' in self.variable_names:
            return [v for v in self.variable_names if v != 't']
        return self.variable_names


class DataManager:
    """Central data manager for the application"""

    def __init__(self):
        self.scout_file: Optional[str] = None
        self.ts_file: Optional[str] = None
        self.scout_parser: Optional[ScoutParser] = None
        self.ts_parser: Optional[TSParser] = None

    def load_scout_file(self, filepath: str) -> bool:
        """Load SCout.txt file"""
        self.scout_file = filepath
        self.scout_parser = ScoutParser(filepath)
        return self.scout_parser.parse()

    def load_ts_file(self, filepath: str) -> bool:
        """Load TSout.txt file"""
        self.ts_file = filepath
        self.ts_parser = TSParser(filepath)
        return self.ts_parser.parse()

    def is_scout_loaded(self) -> bool:
        """Check if SCout.txt is loaded"""
        return self.scout_parser is not None and self.scout_parser.loaded

    def is_ts_loaded(self) -> bool:
        """Check if TSout.txt is loaded"""
        return self.ts_parser is not None and self.ts_parser.loaded

    def clear(self):
        """Clear all loaded data"""
        self.scout_file = None
        self.ts_file = None
        self.scout_parser = None
        self.ts_parser = None
