# Graph type specification: xy

This page mirrors src/forgegraph/graph_types/xy.yaml, which is the specification. A test fails if they ever differ.

name: xy          *# \[text\]; The name of the graph type.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Draws y against x, one series per group of rows.          *# \[text\]; The description of the graph type.*\
extends: None          *# \[None, graph type\]; Each parameter not listed is inherited from this graph type. If None, this file must list every parameter.*\
 \
fixed_parameters:          *# List of fixed parameters for the graph type, None if none.*\
    layer:\
        types: \[reference_line, note, error_bar\]          *# \[layer types\]; Layer types a GraphSpec of this graph type may list.*\
 \
variable_parameters:          *# List of variable parameters for the graph type, None if none.*\
    axis:\
        x:\
            data:\
                column: None          *# \[column\]; Horizontal axis column. A GraphSpec must set it.*\
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
                step: None          *# \[None, positive float, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: auto          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
        y:\
            data:\
                column: None          *# \[columns\]; Vertical axis column, or columns for one series each. A GraphSpec must set it.*\
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
                step: None          *# \[None, positive float, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: auto          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
    encoding:\
        color:\
            column: column_name          *# \[None, column_name, column\]; A color per value of this column. column_name: per y column. None: one color.*\
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
            column: None          *# \[None, columns\]; Columns splitting rows into separate lines, e.g. replicates. Each y column is always its own line.*\
        order: sorted          *# \[sorted, data\]; Group order: sorted, or as first seen.*\
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
    benchmark:\
        data_column: None          *# \[None, column_name, column\]; Column marking the benchmark. column_name: a y column. None: no benchmark.*\
        value: None          *# \[None, text, float, date\]; The benchmark's value in data_column (for column_name, a y column's name; for a date column, a date), drawn in series.benchmark style. Set with data_column.*\
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
        key:\
            positions: \[top_right, top_left, bottom_right, bottom_left\]          *# \[top_left, top_center, top_right, bottom_left, bottom_center, bottom_right, right_top, right_center, right_bottom\]; Tried in order: the first clear one.*\
            inside: true          *# \[true, false\]; Inside the plot area, or outside it: top\_\* above it, bottom\_\* below the x-axis title, right\_\* to its right.*\
            title:\
                text: column_name          *# \[None, column_name, text\]; Every key's title. column_name: each key's own column's name. None: none. A text: one key only.*\
        color_bar:\
            title:\
                text: column_name          *# \[None, column_name, text\]; Color bar title. column_name: the encoding.color.column column's name. None: none.*
