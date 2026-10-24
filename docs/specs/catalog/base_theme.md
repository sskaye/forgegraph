# Catalog specification: base_theme

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[theme\]; The theme this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the base theme.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; Each parameter not listed is taken from this catalog. If None, this file must list every parameter.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, drawn with the theme this catalog shows.*\
 \
baselines:          *# Numbered baselines: the baseline with one or more changes, named for variations' from; numbered in order of first use. None if none.*\
    narrow: {figure.width: 120}          *# \[parameters and their values, or non-standard\]; A narrower plot, where the tick algorithms choose differently.*\
    log_x: {axis.x.scale: log}          *# \[parameters and their values, or non-standard\]; A log x axis, so the log tick algorithm acts.*\
    minor_ticks: {axis.tick.minor.num: 4}          *# \[parameters and their values, or non-standard\]; Minor tick sizes act only on minor ticks.*\
    grid_shown: {grid.show: true}          *# \[parameters and their values, or non-standard\]; The grid's parameters act only on a shown grid.*\
    styled_by_size: {encoding.line_style: Cell Size}          *# \[parameters and their values, or non-standard\]; series.line.style acts only with encoding.line_style set.*\
    shaped_by_size: {encoding.marker_shape: Cell Size}          *# \[parameters and their values, or non-standard\]; series.marker.shape acts only with encoding.marker_shape set.*\
    filled_by_size: {encoding.marker_fill: Cell Size}          *# \[parameters and their values, or non-standard\]; series.marker.fill acts only with encoding.marker_fill set.*\
    colored_by_temperature: {encoding.color: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric encoding.color, so a color bar is drawn.*\
    fanned: {data.file: fanned.parquet}          *# \[parameters and their values, or non-standard\]; Curves ending at the same current: their labels fit only past the line ends.*\
    thick_lines: {series.line.width: 1.2}          *# \[parameters and their values, or non-standard\]; Thick lines, so their corners show.*\
    key_shown: {legend.method: key}          *# \[parameters and their values, or non-standard\]; Series named in a key, so the key's parameters act.*\
    key_framed: {legend.method: key, legend.key.frame: true}          *# \[parameters and their values, or non-standard\]; The key, framed, so the frame's width acts.*\
    non_standard: non-standard          *# \[parameters and their values, or non-standard\]; Drawn on after ForgeGraph finished, so the watermark shows.*\
    footnoted: footnoted          *# \[parameters and their values, non-standard, or footnoted\]; With a footnote, as a scheduled run's stamp.*\
    dated: {data.file: dated.parquet, axis.x.data.column: Date, axis.x.title: Day}          *# \[parameters and their values, or non-standard\]; Daily dates on x, so date labels show.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar, so the bar parameters act.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    grouped:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run side by side, so the gap acts.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: Run\
        encoding.color_type: categorical\
        encoding.detail: None\
        legend.key.title.text: column_name\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        series.offset: side_by_side\
        series.bar.width: 1.8\
        series.benchmark.bar.width: 1.8\
    labelled:          *# \[parameters and their values, or non-standard\]; The bars, each with its value, so the value label parameters act.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        series.value_label.show: true\
    wrapped:          *# \[parameters and their values, or non-standard\]; The bars, with a cell name wider than the space between ticks, so it wraps.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        data.file: reinforced.parquet\
    error_bars:          *# \[parameters and their values, or non-standard\]; An error bar on every point, so the error bar parameters act.*\
        layers.spread.type: error_bar\
        layers.spread.value.lower: 0.02\
        layers.spread.value.upper: 0.02\
    target:          *# \[parameters and their values, or non-standard\]; A labelled reference line, so its parameters act.*\
        layers.target.type: reference_line\
        layers.target.axis: y\
        layers.target.value: 1.2\
        layers.target.label.text: Target\
    noted:          *# \[parameters and their values, or non-standard\]; A note, so its parameters act.*\
        layers.conditions.type: note\
        layers.conditions.text: "60 °C, 1 atm, H\_{2}/air"\
 \
variations:          *# Every parameter of the theme, by category: its card's value. {value, from, with}: start from a numbered baseline, or change other parameters too. no_card: no card.*\
    font:\
        family: IBM Plex Serif          *# \[text\]; Typeface for all text.*\
        weight: light          *# \[light, regular, medium, semibold, bold\]; Weight of text without its own: tick labels, value labels, notes.*\
        color: "#D62728"          *# \[hex color\]; Text color, unless set elsewhere.*\
    background:\
        color: "#D62728"          *# \[None, hex color\]; Figure and plot background. None: transparent.*\
    title:\
        size: 1.89          *# \[positive float\]; Title size, × base size.*\
        weight: light          *# \[light, regular, medium, semibold, bold\]; Title weight.*\
        gap: 1.5          *# \[positive float\]; Gap below the title's letters, × base size.*\
    axis:\
        title:\
            size: 1.89          *# \[positive float\]; Axis title size, × base size.*\
            weight: light          *# \[light, regular, medium, semibold, bold\]; Axis title weight.*\
            gap: 1.5          *# \[positive float\]; Gap from tick labels to the title's letters, × base size.*\
        tick:\
            direction: in          *# \[in, out, both\]; Tick direction.*\
            sides: \[left, bottom, top, right\]          *# \[left, right, top, bottom, None\]; Sides with ticks. None: none.*\
            length: 0.54          *# \[positive float\]; Tick length, × base size.*\
            width: 0.126          *# \[positive float\]; Tick width, × base size.*\
            algorithm: {value: wilkinson, from: narrow}          *# \[extended_wilkinson, wilkinson, heckbert, nelder, r_pretty, matplotlib\]; Published algorithm placing major ticks on linear axes.*\
            log_algorithm: {value: matplotlib, from: log_x}          *# \[breaks_log, matplotlib\]; Published algorithm placing major ticks on log axes. breaks_log: R's scales::breaks_log, as many labels as axis.tick.algorithm gives an axis of the same length. matplotlib: powers of ten only.*\
            label:\
                size: 1.62          *# \[positive float\]; Tick label size, × base size.*\
                gap: 1          *# \[positive float\]; Gap from tick to label, × base size.*\
                x_rotation: 45          *# \[0-90\]; x tick label angle, degrees. 0: horizontal.*\
                date_order: {value: day_month, from: dated}          *# \[month_day, day_month\]; Day and month in automatic date tick labels: Jul 6, or 6 Jul.*\
                max_wrap: {value: 0, from: wrapped}          *# \[int\]; Times a label may wrap onto a new line. 0: never.*\
            minor:\
                num: 4          *# \[int\]; Minor ticks between major ticks. 0: none.*\
                length: {value: 0.3, from: minor_ticks}          *# \[positive float\]; Minor tick length, × base size.*\
                width: {value: 0.12, from: minor_ticks}          *# \[positive float\]; Minor tick width, × base size.*\
    plot_area:\
        sides: \[left, bottom\]          *# \[left, right, top, bottom, None\]; Sides with a border line. None: none.*\
        line_color: "#D62728"          *# \[hex color\]; Border line color.*\
        line_width: 0.144          *# \[positive float\]; Border line width, × base size.*\
        aspect: 2          *# \[positive float\]; Plot area width ÷ height.*\
        margin: 0.3          *# \[0-1\]; Gap between data and the plot area's edge, × axis range.*\
    grid:\
        show: true          *# \[true, false\]; Draw a grid.*\
        line_style: {value: dashed, from: grid_shown}          *# \[solid, dashed, dotted\]; Grid line style.*\
        color: {value: "#D62728", from: grid_shown}          *# \[hex color\]; Grid color.*\
        line_width: {value: 0.09, from: grid_shown}          *# \[positive float\]; Grid line width, × base size.*\
    series:\
        colors: tol_bright          *# \[okabe_ito, tol_bright, tol_muted, tableau_10, color_blind, hex colors\]; Colors for encoding.color groups, in order, then repeating: a named palette, or a list of colors.*\
        line:\
            style: {value: \[dotted, solid\], from: styled_by_size}          *# \[solid, dashed, dotted, dashdot\]; Line styles for encoding.line_style groups, in order.*\
            width: 0.18          *# \[positive float\]; Line width, × base size.*\
            cap: butt          *# \[butt, round, projecting\]; Shape of a line's ends.*\
            join: {value: miter, from: thick_lines}          *# \[miter, round, bevel\]; Shape of a line's corners.*\
        marker:\
            shape: {value: \[diamond, circle\], from: shaped_by_size}          *# \[circle, square, triangle_up, triangle_down, diamond, cross, plus\]; Marker shapes for encoding.marker_shape groups, in order.*\
            fill: {value: \[open, filled\], from: filled_by_size}          *# \[filled, open\]; Marker fills for encoding.marker_fill groups, in order. open: outline only.*\
            size: 0.9          *# \[positive float\]; Marker size, × base size.*\
            edge_color: None          *# \[None, hex color\]; Outline color of filled markers. None: none.*\
            edge_width: 0.09          *# \[positive float\]; Marker outline width, × base size.*\
        bar:\
            width: {value: 1.5, from: bars}          *# \[positive float\]; Bar width, × base size. Bars that would overlap are an error.*\
            gap: {value: 0.6, from: grouped}          *# \[0-2\]; Gap between side-by-side bars, × base size.*\
            edge_color: {value: None, from: bars}          *# \[None, hex color\]; Bar outline color. None: none.*\
            edge_width: {value: 0.2, from: bars}          *# \[positive float\]; Bar outline width, × base size.*\
        value_label:\
            size: {value: 1.4, from: labelled}          *# \[positive float\]; Value label size, × base size.*\
            gap: {value: 1, from: labelled}          *# \[positive float\]; Gap from the mark to the label's letters, × base size.*\
        benchmark:\
            color: "#D62728"          *# \[hex color\]; Benchmark color.*\
            line:\
                style: dashed          *# \[solid, dashed, dotted, dashdot\]; Benchmark line style.*\
                width: 0.36          *# \[positive float\]; Benchmark line width, × base size.*\
            marker:\
                shape: square          *# \[circle, square, triangle_up, triangle_down, diamond, cross, plus\]; Benchmark marker shape.*\
                fill: open          *# \[filled, open\]; Benchmark marker fill.*\
                size: 0.9          *# \[positive float\]; Benchmark marker size, × base size.*\
                edge_color: "#CC0000"          *# \[None, hex color\]; Outline color of a filled benchmark marker. None: none.*\
                edge_width: 0.2          *# \[positive float\]; Benchmark marker outline width, × base size.*\
            bar:\
                width: {value: 1.5, from: bars}          *# \[positive float\]; Benchmark bar width, × base size.*\
                edge_color: {value: "#CC0000", from: bars}          *# \[None, hex color\]; Benchmark bar outline color. None: none.*\
                edge_width: {value: 0.2, from: bars}          *# \[positive float\]; Benchmark bar outline width, × base size.*\
    legend:\
        methods: no_card          *# \[auto, direct, key, none\]; Methods graphs may use to name series, in auto's order of preference. direct: names beside the lines. key: a boxed list.*\
        label:\
            size: 1.5          *# \[positive float\]; Series name size, × base size.*\
            weight: light          *# \[light, regular, medium, semibold, bold\]; Series name weight.*\
        direct:\
            clearance: 0.4          *# \[positive float\]; Minimum gap around a direct label, × base size.*\
            max_relative_distance: 0.5          *# \[0-1\]; Most a label's distance to its series may be, ÷ its distance to the next nearest.*\
            max_axis_extension: {value: 0.4, from: fanned}          *# \[0-1\]; Most the x-axis may grow to fit labels, × its range.*\
        key:\
            frame: {value: true, from: key_shown}          *# \[true, false\]; Box around the key.*\
            frame_width: {value: 0.15, from: key_framed}          *# \[positive float\]; Frame line width, × base size.*\
            background: {value: "#FFE680", from: key_shown}          *# \[None, hex color\]; Fill behind the key. None: none.*\
            padding: {value: 1.2, from: key_shown}          *# \[positive float\]; Gap inside the frame, every side, × base size.*\
            inset: {value: 1.5, from: key_shown}          *# \[positive float\]; Gap from the plot area to the key, × base size.*\
            row_gap: {value: 1.2, from: key_shown}          *# \[positive float\]; Gap between entries, × base size.*\
            title:\
                weight: {value: light, from: key_shown}          *# \[light, regular, medium, semibold, bold\]; Key title weight.*\
                align: {value: center, from: key_shown}          *# \[left, center, right\]; Key title alignment.*\
                gap: {value: 1.5, from: key_shown}          *# \[positive float\]; Gap from the title to the first entry, × base size.*\
            sample:\
                length: {value: 3.5, from: key_shown}          *# \[positive float\]; Line sample length, × base size.*\
                gap: {value: 1.5, from: key_shown}          *# \[positive float\]; Gap from the line sample to the name, × base size.*\
                marker_size: {value: 0.9, from: key_shown}          *# \[positive float\]; Marker size in key samples, × base size; series.marker.size sets the plot's.*\
        color_bar:\
            layout: {value: title_along, from: colored_by_temperature}          *# \[title_above, title_along, below\]; title_above: bar right of the plot, title above it. title_along: title beside the bar, reading down. below: horizontal bar under the plot.*\
            colors: {value: magma, from: colored_by_temperature}          *# \[viridis, cividis, plasma, inferno, magma, greys, blues, red_blue, hex color, two hex colors\]; Colors for a numeric encoding.color: a named scale, one hex color (light to it) or two (first to second).*\
            width: {value: 1.5, from: colored_by_temperature}          *# \[positive float\]; Bar thickness, × base size.*\
            gap: {value: 2, from: colored_by_temperature}          *# \[positive float\]; Gap from the plot area to the bar, × base size.*\
    layer:\
        error_bar:\
            cap_size: {value: 0.8, from: error_bars}          *# \[positive float\]; Cap width, × base size.*\
            color: {value: "#000000", from: error_bars}          *# \[series, hex color\]; Error bar color. series: the series' color.*\
            line_width: {value: 0.25, from: error_bars}          *# \[positive float\]; Line width, × base size.*\
        reference_line:\
            line_style: {value: dotted, from: target}          *# \[solid, dashed, dotted, dashdot\]; Line style.*\
            color: {value: "#CC0000", from: target}          *# \[hex color\]; Line and label color, unless drawn per series.*\
            line_width: {value: 0.25, from: target}          *# \[positive float\]; Line width, × base size.*\
            label:\
                size: {value: 1.4, from: target}          *# \[positive float\]; Label size, × base size.*\
                gap: {value: 1, from: target}          *# \[positive float\]; Gap from the line to the label's letters, × base size.*\
        note:\
            size: {value: 1.3, from: noted}          *# \[positive float\]; Note size, × base size.*\
            color: {value: "#CC0000", from: noted}          *# \[hex color\]; Note color.*\
            inset: {value: 2, from: noted}          *# \[positive float\]; Gap between the plot area's edges and the note, × base size.*\
    watermark:\
        text: {value: DRAFT, from: non_standard}          *# \[text\]; Watermark on non-standard graphs.*\
        color: {value: "#4C78A8", from: non_standard}          *# \[hex color\]; Watermark color.*\
        opacity: {value: 0.48, from: non_standard}          *# \[0-1\]; Watermark opacity.*\
        weight: {value: regular, from: non_standard}          *# \[light, regular, medium, semibold, bold\]; Watermark weight.*\
        angle: {value: 0, from: non_standard}          *# \[-90-90\]; Watermark angle, degrees counterclockwise.*\
        span: {value: 0.5, from: non_standard}          *# \[0-1\]; Share of the plot area's width or height it spans, whichever it reaches first.*\
    footnote:\
        size: {value: 1, from: footnoted}          *# \[positive float\]; Size of footnotes below the figure, × base size.*\
        color: {value: "#D62728", from: footnoted}          *# \[hex color\]; Footnote color.*\
        gap: {value: 2, from: footnoted}          *# \[positive float\]; Gap from the lowest text or line above a footnote to its letters, × base size.*
