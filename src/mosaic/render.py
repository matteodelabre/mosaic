import numpy as np

from .compute import Centers, Point, Region, Regions


# Paul Tol's "light qualitative" colorscheme
base_palette = [
    "#77AADD",
    "#EE8866",
    "#EEDD88",
    "#FFAABB",
    "#99DDFF",
    "#44BB99",
    "#BBCC33",
    "#AAAA00",
]


def sort_vertices(region: Region, center: Point) -> tuple[Point, ...]:
    """Sort vertices of a polyhedron in counterclockwise order about its center."""
    verts = np.array(list(region))

    if verts.shape[1] >= 2:
        delta = verts - center
        order = np.argsort(np.arctan2(delta[:, 0], delta[:, 1]))
        verts = verts[order]

    return tuple(tuple(float(coord) for coord in vertex) for vertex in verts)


def plot_regions_cetz(regions: Regions, centers: Centers) -> str:
    """
    Generate code to plot a set of regions in Typst using CeTZ.

    :param regions: set of regions to plot
    :param centers: center points of regions to plot
    :param colors: cycle list of colors to use
    :returns: Typst code
    """
    lines = []
    lines.append('#import "@preview/cetz:0.4.2"')
    lines.append('#import "@preview/cetz-plot:0.1.3": plot')
    lines.append("#cetz.canvas({")
    lines.append("plot.plot(size: (10, 10), {")

    for region, vectors in regions.items():
        verts = sort_vertices(region, centers[region])

        if len(verts) >= 3:
            shape = ', fill: true, fill-type: "shape"'
        elif len(verts) == 1:
            shape = ', mark: "x"'
        else:
            shape = ""

        label = ", ".join(map(str, vectors))
        lines.append(f"plot.add({verts}, label: [{label}]{shape})")

    lines.append("})")
    lines.append("})")
    return "\n".join(lines)


def plot_regions_pgfplots(regions: Regions, centers: Centers, colors=base_palette) -> str:
    """
    Generate code to plot a set of regions in LaTeX using PGFplots.

    :param regions: set of regions to plot
    :param centers: center points of regions to plot
    :param colors: cyclic list of colors to use, as `#000000` hexadecimal format strings
    :returns: LaTeX code
    """
    layers = [
        "axis background",
        "pre main",
        "main",
        "lines",
        "marks",
        "axis grid",
        "axis ticks",
        "axis lines",
        "axis tick labels",
        "axis descriptions",
        "axis foreground",
    ]

    lines = []
    lines.append(r"\documentclass[margin=.25cm]{standalone}")
    lines.append(r"\usepackage{tikz}")
    lines.append(r"\usepackage{pgfplots}")
    lines.append(r"\pgfplotsset{width=7cm,compat=1.18}")
    lines.append(
        r"\pgfplotsset{layers/mosaic/.define layer set={"
        + ",".join(layers)
        + "}{/pgfplots/layers/standard}}"
    )

    for i, color in enumerate(colors):
        lines.append(rf"\definecolor{{c{i}}}{{HTML}}{{{color[1:]}}}")

    lines.append(r"\begin{document}")
    lines.append(r"\begin{tikzpicture}")
    lines.append(r"\pgfplotsset{set layers=mosaic}")
    lines.append(
        r"\begin{axis}["
        + ", ".join(
            (
                "clip mode=individual",
                "legend style={"
                + ", ".join(
                    (
                        "legend pos=outer north east",
                        "cells={anchor=west, align=left}",
                        "nodes={scale=.75, transform shape}",
                    )
                )
                + "}",
                "grid=both",
                "grid style={black, opacity=.15, dashed}",
                "tick style={transparent}",
                "xtick distance=1",
                "ytick distance=1",
                "enlargelimits=false",
                r"xlabel={\(x\)}",
                r"ylabel={\(y\)}",
            )
        )
        + "]"
    )

    # Sort regions by lexicographic order of their first vector
    sorted_regions = sorted(regions.items(), key=lambda item: next(iter(item[1])))

    # Cycle through colors for each shape type
    next_color = {"area": 0, "line": 0, "mark": 0}

    for i, (region, vectors) in enumerate(sorted_regions):
        if len(region) == 0:
            continue

        verts = sort_vertices(region, centers[region])

        if len(verts[0]) != 2:
            raise ValueError("only 2-dimensional regions can be plotted")

        if len(verts) >= 3:
            color = f'c{next_color["area"]}'
            next_color["area"] = (next_color["area"] + 1) % len(colors)
            verts = verts + (verts[0],)
            style = ", ".join(
                ("area legend", "black", f"fill={color}!70!white", "mark=none")
            )
        elif len(verts) == 2:
            color = f'c{next_color["line"]}'
            next_color["line"] = (next_color["line"] + 1) % len(colors)
            style = ", ".join(
                (
                    "line legend",
                    "black",
                    "line width=2pt",
                    "line cap=round",
                    f"postaction={{draw, {color}!70!white, line width=1.3pt}}",
                    "on layer=lines",
                )
            )
        else:
            color = f'c{next_color["mark"]}'
            next_color["mark"] = (next_color["mark"] + 1) % len(colors)
            style = ", ".join(
                (
                    "line legend",
                    "black",
                    "mark=*",
                    "mark size=1.5pt",
                    f"fill={color}",
                    "on layer=marks",
                )
            )

        coords = " ".join("(" + ", ".join(map(str, vert)) + ")" for vert in verts)
        lines.append(rf"\addplot[{style}] coordinates {{ {coords} }};")

        label = r"\\".join(map(str, vectors))
        lines.append(rf"\addlegendentry{{{label}}}")

    lines.append(r"\end{axis}")
    lines.append(r"\end{tikzpicture}")
    lines.append(r"\end{document}")
    return "\n".join(lines)
