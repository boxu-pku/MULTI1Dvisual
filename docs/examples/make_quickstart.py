"""Build the small synthetic output archive used in both user manuals (stdlib only)."""

import math
import struct
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def record(data):
    marker = struct.pack("<i", len(data))
    return marker + data + marker


def names_and_size(names):
    return record(struct.pack("<i", len(names))) + record(
        b"".join(name.ljust(8).encode("ascii") for name in names)
    )


def values_record(values):
    return record(struct.pack(f"<{len(values)}d", *values))


def moving_edge_example():
    """Formatted output for a known moving edge, sampled without a solver."""
    cells = 60
    centers_um = [i + 0.5 for i in range(cells)]
    edges_um = list(range(cells + 1))
    static_names = ["NC"] * cells + ["NI"] * len(edges_um)
    indices = list(range(1, cells + 1))
    interface_indices = list(range(1, cells + 2))
    static_indices = indices + interface_indices
    field_names = ["TIME"] + ["XC"] * cells + ["X"] * len(edges_um) + ["R"] * cells
    field_indices = [1] + indices + interface_indices + indices
    # Each label, index and value occupies one line in formatted fort.10 output.
    lines = [str(len(static_names)), *static_names, *map(str, static_indices),
             *map(str, static_indices), str(len(field_names)), *field_names,
             *map(str, field_indices)]
    centers_cm = [x * 1e-4 for x in centers_um]
    edges_cm = [x * 1e-4 for x in edges_um]
    for time_ns in range(13):
        edge_um = 18.5 + time_ns
        density = [1.25 + 0.25 * math.tanh((x - edge_um) / 2) for x in centers_um]
        values = [time_ns * 1e-9, *centers_cm, *edges_cm, *density]
        lines.extend(f"{value:.12E}" for value in values)
    grid_label = (
        "! Synthetic grid metadata for the plotting example.\n"
        "&layer\n  nc=60, thick=0.006, r0=1.0, material='Demo grid'\n/\n"
    )
    return {
        "moving-edge/fort.10": ("\n".join(lines) + "\n").encode("ascii"),
        "moving-edge/data.in": grid_label.encode("ascii"),
    }


def build_archive(destination):
    positions = [5 * j for j in range(21)]  # micrometres
    serials = list(range(1, len(positions) + 1))
    centers = ["# TIME\tXC\tNC\tT\tR"]
    scalars = ["# TIME\tENIE"]
    binary = BytesIO()
    binary.write(names_and_size(["NC"] * len(serials)))
    binary.write(values_record(serials))
    binary.write(names_and_size(["TIME", "ENIE"] + ["XC"] * 21 + ["T"] * 21 + ["R"] * 21))
    for step in range(9):
        time_ns = step / 2
        seconds = time_ns * 1e-9
        energy = 10 + 2 * time_ns
        temperature = [2 + 6 * math.exp(-0.5 * ((x - 30 - 10 * time_ns) / 10) ** 2)
                       for x in positions]
        density = [1 + 0.002 * x for x in positions]
        cm = [x * 1e-4 for x in positions]
        scalars.append(f"{seconds:.12e}\t{energy:.12e}")
        centers.extend(f"{seconds:.12e}\t{x:.12e}\t{n}\t{t:.12e}\t{r:.12e}"
                       for x, n, t, r in zip(cm, serials, temperature, density))
        binary.write(values_record([seconds, energy, *cm, *temperature, *density]))
    members = {
        "quickstart.case": b"! Synthetic visualization example; see the accompanying output tables.\n",
        "quickstart.center.dat": ("\n".join(centers) + "\n").encode("ascii"),
        "quickstart.scalars.dat": ("\n".join(scalars) + "\n").encode("ascii"),
        "quickstart.out": binary.getvalue(),
        **moving_edge_example(),
    }
    with ZipFile(destination, "w") as archive:
        for name, data in members.items():
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


if __name__ == "__main__":
    build_archive(Path(__file__).with_name("quickstart.zip"))
