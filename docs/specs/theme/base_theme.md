# Theme specification: base_theme

This page mirrors src/forgegraph/packs/forgegraph_base/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[text\]; The name of the theme.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: The base theme that others can inherit from.          *# \[text\]; The description of the theme.*\
extends: None          *# \[None, theme\]; Each parameter not listed is inherited from this theme. If None, this file must list every parameter.*\
 \
fixed_parameters:          *# List of fixed parameters for the theme.*\
    font:\
        family: Roboto          *# \[text\]; Typeface for all text.*\
        color: "#000000"          *# \[hex color\]; Text color, unless set elsewhere.*\
        weight: regular          *# \[light, regular, medium, semibold, bold\]; Weight of text without its own: tick labels, value labels, notes.*\
    background:\
        color: "#FFFFFF"          *# \[None, hex color\]; Figure and plot background. None: transparent.*\
    title:\
        size: 1.05          *# \[positive float\]; Title size, × base size.*\
        weight: semibold          *# \[light, regular, medium, semibold, bold\]; Title weight.*\
        gap: 0.5          *# \[positive float\]; Gap below the title's letters, × base size.*\
    axis:\
        title:\
            size: 1.05          *# \[positive float\]; Axis title size, × base size.*\
            weight: semibold          *# \[light, regular, medium, semibold, bold\]; Axis title weight.*\
            gap: 0.5          *# \[positive float\]; Gap from tick labels to the title's letters, × base size.*\
        tick:\
            direction: out          *# \[in, out, both\]; Tick direction.*\
            sides: \[left, bottom\]          *# \[left, right, top, bottom, None\]; Sides with ticks. None: none.*\
            length: 0.3          *# \[positive float\]; Tick length, × base size.*\
            width: 0.07          *# \[positive float\]; Tick width, × base size.*\
            algorithm: extended_wilkinson          *# \[extended_wilkinson, wilkinson, heckbert, nelder, r_pretty, matplotlib\]; Published algorithm placing major ticks on linear axes.*\
            log_algorithm: breaks_log          *# \[breaks_log, matplotlib\]; Published algorithm placing major ticks on log axes. breaks_log: R's scales::breaks_log, as many labels as axis.tick.algorithm gives an axis of the same length. matplotlib: powers of ten only.*\
            label:\
                size: 0.9          *# \[positive float\]; Tick label size, × base size.*\
                gap: 0.3          *# \[positive float\]; Gap from tick to label, × base size.*\
                x_rotation: 0          *# \[0-90\]; x tick label angle, degrees. 0: horizontal.*\
                date_order: month_day          *# \[month_day, day_month\]; Day and month in automatic date tick labels: Jul 6, or 6 Jul.*\
                max_wrap: 1          *# \[int\]; Times a label may wrap onto a new line. 0: never.*\
            minor:\
                num: 0          *# \[int\]; Minor ticks between major ticks. 0: none.*\
                length: 0.15          *# \[positive float\]; Minor tick length, × base size.*\
                width: 0.05          *# \[positive float\]; Minor tick width, × base size.*\
    plot_area:\
        sides: \[left, bottom, top, right\]          *# \[left, right, top, bottom, None\]; Sides with a border line. None: none.*\
        line_width: 0.08          *# \[positive float\]; Border line width, × base size.*\
        line_color: "#000000"          *# \[hex color\]; Border line color.*\
        aspect: 1.1          *# \[positive float\]; Plot area width ÷ height.*\
        margin: 0.05          *# \[0-1\]; Gap between data and the plot area's edge, × axis range.*\
    grid:\
        color: "#E6E6E6"          *# \[hex color\]; Grid color.*\
        line_width: 0.05          *# \[positive float\]; Grid line width, × base size.*\
        line_style: solid          *# \[solid, dashed, dotted\]; Grid line style.*\
    series:\
        colors: okabe_ito          *# \[okabe_ito, tol_bright, tol_muted, tableau_10, color_blind, hex colors\]; Colors for encoding.color groups, in order, then repeating: a named palette, or a list of colors.*\
        line:\
            style: \[solid, dashed, dotted, dashdot\]          *# \[solid, dashed, dotted, dashdot\]; Line styles for encoding.line_style groups, in order.*\
            cap: projecting          *# \[butt, round, projecting\]; Shape of a line's ends.*\
            join: round          *# \[miter, round, bevel\]; Shape of a line's corners.*\
        marker:\
            shape: \[circle, square, triangle_up, diamond, triangle_down, cross\]          *# \[circle, square, triangle_up, triangle_down, diamond, cross, plus\]; Marker shapes for encoding.marker_shape groups, in order.*\
            fill: \[filled, open\]          *# \[filled, open\]; Marker fills for encoding.marker_fill groups, in order. open: outline only.*\
            edge_color: "#000000"          *# \[None, hex color\]; Outline color of filled markers. None: none.*\
        bar:\
            edge_color: "#000000"          *# \[None, hex color\]; Bar outline color. None: none.*\
        value_label:\
            size: 0.9          *# \[positive float\]; Value label size, × base size.*\
            gap: 0.25          *# \[positive float\]; Gap from the mark to the label's letters, × base size.*\
        benchmark:\
            color: "#808080"          *# \[hex color\]; Benchmark color.*\
            marker:\
                fill: filled          *# \[filled, open\]; Benchmark marker fill.*\
                edge_color: "#000000"          *# \[None, hex color\]; Outline color of a filled benchmark marker. None: none.*\
            bar:\
                edge_color: "#000000"          *# \[None, hex color\]; Benchmark bar outline color. None: none.*\
    legend:\
        methods: \[auto, direct, key\]          *# \[auto, direct, key, none\]; Methods graphs may use to name series, in auto's order of preference. direct: names beside the lines. key: a boxed list.*\
        label:\
            size: 1.0          *# \[positive float\]; Series name size, × base size.*\
            weight: semibold          *# \[light, regular, medium, semibold, bold\]; Series name weight.*\
        key:\
            frame: false          *# \[true, false\]; Box around the key.*\
            frame_width: 0.06          *# \[positive float\]; Frame line width, × base size.*\
            background: None          *# \[None, hex color\]; Fill behind the key. None: none.*\
            padding: 0.5          *# \[positive float\]; Gap inside the frame, every side, × base size.*\
            inset: 0.5          *# \[positive float\]; Gap from the plot area to the key, × base size.*\
            row_gap: 0.55          *# \[positive float\]; Gap between entries, × base size.*\
            title:\
                weight: semibold          *# \[light, regular, medium, semibold, bold\]; Key title weight.*\
                align: left          *# \[left, center, right\]; Key title alignment.*\
                gap: 0.55          *# \[positive float\]; Gap from the title to the first entry, × base size.*\
            sample:\
                length: 2.0          *# \[positive float\]; Line sample length, × base size.*\
                gap: 0.7          *# \[positive float\]; Gap from the line sample to the name, × base size.*\
        color_bar:\
            layout: title_above          *# \[title_above, title_along, below\]; title_above: bar right of the plot, title above it. title_along: title beside the bar, reading down. below: horizontal bar under the plot.*\
            width: 0.7          *# \[positive float\]; Bar thickness, × base size.*\
            gap: 0.8          *# \[positive float\]; Gap from the plot area to the bar, × base size.*\
    layer:\
        error_bar:\
            cap_size: 0.25          *# \[positive float\]; Cap width, × base size.*\
            line_width: 0.08          *# \[positive float\]; Line width, × base size.*\
            color: series          *# \[series, hex color\]; Error bar color. series: the series' color.*\
        reference_line:\
            color: "#808080"          *# \[hex color\]; Line and label color, unless drawn per series.*\
            line_style: dashed          *# \[solid, dashed, dotted, dashdot\]; Line style.*\
            line_width: 0.08          *# \[positive float\]; Line width, × base size.*\
            label:\
                size: 0.8          *# \[positive float\]; Label size, × base size.*\
                gap: 0.25          *# \[positive float\]; Gap from the line to the label's letters, × base size.*\
        note:\
            size: 0.8          *# \[positive float\]; Note size, × base size.*\
            color: "#404040"          *# \[hex color\]; Note color.*\
            inset: 0.5          *# \[positive float\]; Gap between the plot area's edges and the note, × base size.*\
    watermark:\
        text: NON-STANDARD          *# \[text\]; Watermark on non-standard graphs.*\
        color: "#CC0000"          *# \[hex color\]; Watermark color.*\
        opacity: 0.18          *# \[0-1\]; Watermark opacity.*\
        weight: bold          *# \[light, regular, medium, semibold, bold\]; Watermark weight.*\
        angle: 30          *# \[-90-90\]; Watermark angle, degrees counterclockwise.*\
        span: 0.8          *# \[0-1\]; Share of the plot area's width or height it spans, whichever it reaches first.*\
    footnote:\
        size: 0.7          *# \[positive float\]; Size of footnotes below the figure, × base size.*\
        color: "#808080"          *# \[hex color\]; Footnote color.*\
        gap: 0.5          *# \[positive float\]; Gap from the lowest text or line above a footnote to its letters, × base size.*\
 \
variable_parameters:          *# List of variable parameters for the theme, None if none.*\
    grid:\
        show: false          *# \[true, false\]; Draw a grid.*\
    series:\
        line:\
            width: 0.15          *# \[positive float\]; Line width, × base size.*\
        marker:\
            size: 0.5          *# \[positive float\]; Marker size, × base size.*\
            edge_width: 0.05          *# \[positive float\]; Marker outline width, × base size.*\
        bar:\
            width: 2.5          *# \[positive float\]; Bar width, × base size. Bars that would overlap are an error.*\
            gap: 0.15          *# \[0-2\]; Gap between side-by-side bars, × base size.*\
            edge_width: 0.05          *# \[positive float\]; Bar outline width, × base size.*\
        benchmark:\
            line:\
                style: solid          *# \[solid, dashed, dotted, dashdot\]; Benchmark line style.*\
                width: 0.15          *# \[positive float\]; Benchmark line width, × base size.*\
            marker:\
                shape: circle          *# \[circle, square, triangle_up, triangle_down, diamond, cross, plus\]; Benchmark marker shape.*\
                size: 0.5          *# \[positive float\]; Benchmark marker size, × base size.*\
                edge_width: 0.05          *# \[positive float\]; Benchmark marker outline width, × base size.*\
            bar:\
                width: 2.5          *# \[positive float\]; Benchmark bar width, × base size.*\
                edge_width: 0.05          *# \[positive float\]; Benchmark bar outline width, × base size.*\
    legend:\
        key:\
            sample:\
                marker_size: 0.5          *# \[positive float\]; Marker size in key samples, × base size; series.marker.size sets the plot's.*\
        direct:\
            clearance: 0.2          *# \[positive float\]; Minimum gap around a direct label, × base size.*\
            max_relative_distance: 0.8          *# \[0-1\]; Most a label's distance to its series may be, ÷ its distance to the next nearest.*\
            max_axis_extension: 0.15          *# \[0-1\]; Most the x-axis may grow to fit labels, × its range.*\
        color_bar:\
            colors: viridis          *# \[viridis, cividis, plasma, inferno, magma, greys, blues, red_blue, hex color, two hex colors\]; Colors for a numeric encoding.color: a named scale, one hex color (light to it) or two (first to second).*
