# GraphSpec specification: graphspec_example

This page mirrors src/forgegraph/packs/forgegraph_base/graphspecs/graphspec_example.yaml, which is the specification. A test fails if they ever differ.

name: graphspec_example          *# \[text\]; The name of the GraphSpec.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Polarization curves for cells A–C against the benchmark.          *# \[text\]; The description of the GraphSpec.*\
extends: None          *# \[None, graphspec\]; Each parameter not listed is inherited from this GraphSpec. If None, this file must list every parameter.*\
 \
parameters: !var          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        graph_type: xy          *# \[graph type\];*\
        theme: forgegraph_base/base_theme          *# \[theme\];*\
        format: forgegraph_base/base_format          *# \[format\];*\
    text:\
        title: Polarization, 60 °C          *# \[None, text\]; Graph title. None: none.*\
    data:\
        file: polarization.parquet          *# \[None, text\]; Parquet file holding the DataFrame to draw: an absolute path, one starting with ~, or one relative to the folder of the file that sets it. None: passed through the Python API.*\
        preprocessing: None          *# \[None, text\]; Where the code that made the data is: a path, a URL, a note. Recorded in provenance, never read. None: not given.*\
    axis:\
        x:\
            data:\
                column: "Cell Current (mA/cm²)"          *# \[column\]; Horizontal axis column.*\
                type: auto          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto: datetime for dates, categorical for text, else decimal or integer.*\
                aggregation: none          *# \[none, mean, median, sum, min, max\]; Rows at one place in a series, combined. none: each drawn.*\
                order:\
                    method: source          *# \[source, alphanumeric, value\]; Category order: as in the data, natural, or by the other axis's value.*\
                    direction: ascending          *# \[ascending, descending\]; The category order's direction.*\
            title: column_name          *# \[None, column_name, text\]; Axis title. column_name: the column's name. None: none.*\
            scale: linear          *# \[linear, log\]; Axis scale.*\
            min: None          *# \[None, float, date\]; Axis minimum. On a datetime axis, a date, e.g. 2025-08-25 or "2025-08-25T06:00". None: the lowest value, less plot_area.margin × the data's range.*\
            max: None          *# \[None, float, date\]; Axis maximum. On a datetime axis, a date, e.g. 2025-08-25 or "2025-08-25T06:00". None: the highest value, plus plot_area.margin × the data's range.*\
            tick:\
                algorithm: auto          *# \[auto, all, manual\]; auto: the theme's algorithm; on dates, one calendar unit's boundaries. all: one per value. manual: every tick.step.*\
                step: None          *# \[None, float > 0, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: auto          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
        y:\
            data:\
                column: "Cell Voltage (V)"          *# \[columns\]; Vertical axis column, or columns for one series each.*\
                type: auto          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto: datetime for dates, categorical for text, else decimal or integer.*\
                aggregation: none          *# \[none, mean, median, sum, min, max\]; Rows at one place in a series, combined. none: each drawn.*\
                order:\
                    method: source          *# \[source, alphanumeric, value\]; Category order: as in the data, natural, or by the other axis's value.*\
                    direction: ascending          *# \[ascending, descending\]; The category order's direction.*\
            title: column_name          *# \[None, column_name, text\]; Axis title. column_name: the column's name; with several columns, use text or None. None: none.*\
            scale: linear          *# \[linear, log\]; Axis scale.*\
            min: None          *# \[None, float, date\]; Axis minimum. On a datetime axis, a date, e.g. 2025-08-25 or "2025-08-25T06:00". None: the lowest value, less plot_area.margin × the data's range.*\
            max: None          *# \[None, float, date\]; Axis maximum. On a datetime axis, a date, e.g. 2025-08-25 or "2025-08-25T06:00". None: the highest value, plus plot_area.margin × the data's range.*\
            tick:\
                algorithm: auto          *# \[auto, all, manual\]; auto: the theme's algorithm; on dates, one calendar unit's boundaries. all: one per value. manual: every tick.step.*\
                step: None          *# \[None, float > 0, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: auto          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
    encoding:\
        color:\
            column: Cell          *# \[None, column_name, column\]; A color per value of this column. column_name: per y column. None: one color.*\
            type: auto          *# \[auto, categorical, continuous\]; categorical: a palette color per value. continuous: a color scale and color bar, for numbers. auto: continuous for numbers.*\
        line:\
            style:\
                column: None          *# \[None, column_name, column\]; A line style per value of this column. column_name: per y column. None: one style.*\
        marker:\
            shape:\
                column: None          *# \[None, column_name, column\]; A marker shape per value of this column. column_name: per y column. None: one shape.*\
            fill:\
                column: None          *# \[None, column_name, column\]; A marker fill per value of this column. column_name: per y column. None: one fill.*\
        detail:\
            column: \[Cell, Run\]          *# \[None, columns\]; Columns splitting rows into separate lines, e.g. replicates. Each y column is always its own line.*\
        order: sorted          *# \[sorted, data\]; Group order: sorted, or as first seen.*\
    benchmark:\
        data_column: Cell          *# \[None, column_name, column\]; Column marking the benchmark. column_name: a y column. None: no benchmark.*\
        value: Benchmark          *# \[None, text, float, date\]; The benchmark's value in data_column (for column_name, a y column's name; for a date column, a date), drawn in series.benchmark style. Set with data_column.*\
        side: start          *# \[start, end\]; Where the benchmark goes on a categorical axis it's a value of: before the other categories or after them.*\
    mark:\
        line:\
            show: true          *# \[true, false\]; Draw lines.*\
            connect_order: x          *# \[x, data\]; Point order along each line: by x, or by row.*\
            missing_values: drop          *# \[drop, gap\]; Rows missing x or y. drop: the line joins its neighbors. gap: the line breaks. Both are counted in lint's dropped-rows.*\
        marker:\
            show: true          *# \[true, false\]; Draw markers.*\
        bar:\
            show: false          *# \[true, false\]; Draw bars, from 0 (1 on log); the value axis then includes it.*\
    legend:\
        method: auto          *# \[auto, direct, key, none\]; This graph's method: one of the theme's legend.methods.*\
        direct:\
            clearance: 0.2          *# \[float > 0\]; Minimum gap around a direct label, × base size.*\
            max_relative_distance: 0.8          *# \[0-1\]; Most a label's distance to its series may be, ÷ its distance to the next nearest.*\
            max_axis_extension: 0.15          *# \[0-1\]; Most the x-axis may grow to fit labels, × its range.*\
        key:\
            positions: \[top_right, top_left, bottom_right, bottom_left\]          *# \[top_left, top_center, top_right, bottom_left, bottom_center, bottom_right, right_top, right_center, right_bottom\]; Tried in order: the first clear one.*\
            inside: true          *# \[true, false\]; Inside the plot area, or outside it: top\_\* above it, bottom\_\* below the x-axis title, right\_\* to its right.*\
            sample:\
                marker:\
                    size: 0.5          *# \[float > 0\]; Marker size in key samples, × base size; series.marker.size sets the plot's.*\
            title:\
                text: column_name          *# \[None, column_name, text\]; Every key's title. column_name: each key's own column's name. None: none. A text: one key only.*\
        color_bar:\
            colors: viridis          *# \[viridis, cividis, plasma, inferno, magma, greys, blues, red_blue, hex color, two hex colors\]; Colors for a numeric encoding.color.column: a named scale, one hex color (light to it) or two (first to second).*\
            title:\
                text: column_name          *# \[None, column_name, text\]; Color bar title. column_name: the encoding.color.column column's name. None: none.*\
    series:\
        base_axis: x          *# \[x, y\]; The axis series are drawn along: bars stand on it, and aggregation adds along the other.*\
        aggregation: none          *# \[none, sum, percent\]; Series at the same place: drawn as they are, stacked, or stacked to 100 %.*\
        offset: none          *# \[none, side_by_side\]; side_by_side: series at the same place are drawn beside each other.*\
        value_label:\
            show: false          *# \[true, false\]; Write each value by its mark.*\
            position: auto          *# \[auto, inside, outside\]; Inside a bar's end, beyond the mark, or inside where it fits.*\
            format: auto          *# \[auto, text\]; Number format, e.g. ",.0f"; on a date axis, a date format, e.g. "%H:%M". auto: as the value axis's tick labels.*\
            total:\
                show: false          *# \[true, false\]; With aggregation sum, also write each stack's total.*\
        line:\
            width: 0.15          *# \[float > 0\]; Line width, × base size.*\
        marker:\
            size: 0.5          *# \[float > 0\]; Marker size, × base size.*\
            edge:\
                width: 0.05          *# \[float > 0\]; Marker outline width, × base size.*\
        bar:\
            width: 2.5          *# \[float > 0\]; Bar width, × base size. Bars that would overlap are an error.*\
            gap: 0.15          *# \[0-2\]; Gap between side-by-side bars, × base size.*\
            edge:\
                width: 0.05          *# \[float > 0\]; Bar outline width, × base size.*\
        benchmark:\
            line:\
                style: solid          *# \[solid, dashed, dotted, dashdot\]; Benchmark line style.*\
                width: 0.15          *# \[float > 0\]; Benchmark line width, × base size.*\
            marker:\
                shape: circle          *# \[circle, square, triangle_up, triangle_down, diamond, cross, plus\]; Benchmark marker shape.*\
                size: 0.5          *# \[float > 0\]; Benchmark marker size, × base size.*\
                edge:\
                    width: 0.05          *# \[float > 0\]; Benchmark marker outline width, × base size.*\
            bar:\
                width: 2.5          *# \[float > 0\]; Benchmark bar width, × base size.*\
                edge:\
                    width: 0.05          *# \[float > 0\]; Benchmark bar outline width, × base size.*\
    grid:\
        show: false          *# \[true, false\]; Draw a grid.*\
    output:\
        file_types: \[png\]          *# \[png, jpg, tiff, svg, pdf, html\]; File types saved.*\
    provenance:\
        level: full          *# \[full, minimal, off\]; What each saved file records of how it was made. full: every value and the data file. minimal: the GraphSpec and specs, without them. off: nothing.*\
    layer:\
        error_bar:\
            color: "#000000"          *# \[series, hex color\]; Error bar color. series: the series' color.*\
    layers:          *# Layers drawn on the graph, each under a name of the GraphSpec's choosing, drawn in this order.*\
        target:\
            type: reference_line          *# \[layer type\]; The layer's type: one of the graph type's layer.types.*\
            axis: y          *# \[x, y\]; Axis the value is on: y draws a horizontal line.*\
            value: 1.2          *# \[float, date, column\]; The line's value, or a column to aggregate. On a datetime axis, a date, e.g. 2025-08-25.*\
            label:\
                text: Target 1.2 V          *# \[None, aggregation, value, aggregation_value, text\]; aggregation: e.g. Mean. value: e.g. 14.9. aggregation_value: Mean: 14.9. None: no label. Other text: written as given.*\
        conditions:\
            type: note          *# \[layer type\]; The layer's type: one of the graph type's layer.types.*\
            text: "60 °C, 1 atm, H₂/air"          *# \[text\]; The note, in label markup; a line break starts a new line.*
