# Catalog specification: xy

This page mirrors src/forgegraph/catalogs/graph_types/xy.yaml, which is the specification. A test fails if they ever differ.

name: xy          *# \[graph type\]; The graph type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the xy graph type.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; Each parameter not listed is taken from this catalog. If None, this file must list every parameter.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, drawn with the graph type this catalog shows.*\
 \
baselines:          *# Numbered baselines: the baseline with one or more changes, named for variations' from; numbered in order of first use. None if none.*\
    key_shown: {legend.method: key}          *# \[parameters and their values, or non-standard\]; Series named in a key, so the key's parameters act.*\
    colored_by_temperature: {encoding.color: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric encoding.color, so a color bar is drawn.*\
    colored_by_run: {encoding.color: Run}          *# \[parameters and their values, or non-standard\]; Colored by run, a column of numbers, so auto draws a color scale.*\
    temperatures:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density at each temperature it ran at.*\
        axis.x.data.column: "Temperature (°C)"\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        encoding.detail: None\
    x_manual: {axis.x.tick.algorithm: manual, axis.x.tick.step: 20}          *# \[parameters and their values, or non-standard\]; x ticks every 20, so the step acts.*\
    y_manual: {axis.y.tick.algorithm: manual, axis.y.tick.step: 0.05}          *# \[parameters and their values, or non-standard\]; y ticks every 0.05, so the step acts.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    sorted:          *# \[parameters and their values, or non-standard\]; The bars, in order of their values.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        axis.x.data.order.method: value\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    marked_bars:          *# \[parameters and their values, or non-standard\]; The bars, with a marker at each top.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
    overlaid:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run, the runs drawn over each other.*\
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
        series.bar.width: 1.8\
        series.benchmark.bar.width: 1.8\
    stacked:          *# \[parameters and their values, or non-standard\]; The runs' bars stacked.*\
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
        series.aggregation: sum\
        series.bar.width: 1.8\
        series.benchmark.bar.width: 1.8\
    labelled:          *# \[parameters and their values, or non-standard\]; The bars, each with its value.*\
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
 \
variations:          *# Every parameter of the graph type, by category: its card's value. {value, from, with}: start from a numbered baseline, or change other parameters too. no_card: no card.*\
    layer:\
        types: no_card          *# \[layer types\]; Layer types a GraphSpec of this graph type may list.*\
    axis:\
        x:\
            data:\
                column: "Power Density (mW/cm²)"          *# \[column\]; Horizontal axis column.*\
                type: {value: categorical, from: temperatures}          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto: datetime for dates, categorical for text, else decimal or integer.*\
                aggregation: no_card          *# \[none, mean, median, sum, min, max\]; Rows at one place in a series, combined. none: each drawn.*\
                order:\
                    method:          *# \[source, alphanumeric, value\]; Category order: as in the data, natural, or by the other axis's value.*\
                        value: value\
                        from: bars\
                    direction: {value: descending, from: sorted}          *# \[ascending, descending\]; The category order's direction.*\
            title: "Current (mA/cm^2)"          *# \[None, column_name, text\]; Axis title. column_name: the column's name. None: none.*\
            scale: log          *# \[linear, log\]; Axis scale.*\
            min: 20          *# \[None, float\]; Axis minimum. None: the lowest value, less plot_area.margin × the data's range.*\
            max: 60          *# \[None, float\]; Axis maximum. None: the highest value, plus plot_area.margin × the data's range.*\
            tick:\
                algorithm:          *# \[auto, all, manual\]; auto: the theme's algorithm; on dates, one calendar unit's boundaries. all: one per value. manual: every tick.step.*\
                    value: manual\
                    with:\
                        axis.x.tick.step: 20\
                step: {value: 50, from: x_manual}          *# \[None, positive float, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: ".1f"          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
        y:\
            data:\
                column: "iR-Free Voltage (V)"          *# \[columns\]; Vertical axis column, or columns for one series each.*\
                type: no_card          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto: datetime for dates, categorical for text, else decimal or integer.*\
                aggregation: {value: mean, from: bars}          *# \[none, mean, median, sum, min, max\]; Rows at one place in a series, combined. none: each drawn.*\
                order:\
                    method: no_card          *# \[source, alphanumeric, value\]; Category order: as in the data, natural, or by the other axis's value.*\
                    direction: no_card          *# \[ascending, descending\]; The category order's direction.*\
            title: "Voltage (V)"          *# \[None, column_name, text\]; Axis title. column_name: the column's name; with several columns, use text or None. None: none.*\
            scale: log          *# \[linear, log\]; Axis scale.*\
            min: 1.2          *# \[None, float\]; Axis minimum. None: the lowest value, less plot_area.margin × the data's range.*\
            max: 1.5          *# \[None, float\]; Axis maximum. None: the highest value, plus plot_area.margin × the data's range.*\
            tick:\
                algorithm:          *# \[auto, all, manual\]; auto: the theme's algorithm; on dates, one calendar unit's boundaries. all: one per value. manual: every tick.step.*\
                    value: manual\
                    with:\
                        axis.y.tick.step: 0.05\
                step: {value: 0.2, from: y_manual}          *# \[None, positive float, text\]; With manual: distance between ticks, e.g. 5 or "2 week"; on log, a factor.*\
                label:\
                    format: ".2f"          *# \[auto, text\]; Number format, e.g. ",.0f", or date format, e.g. "%b %-d". auto: from the values; dates, by their tick unit.*\
    encoding:\
        color: Cell Size          *# \[None, column_name, column\]; A color per value of this column. column_name: per y column. None: one color.*\
        color_type: {value: categorical, from: colored_by_run}          *# \[auto, categorical, continuous\]; categorical: a palette color per value. continuous: a color scale and color bar, for numbers. auto: continuous for numbers.*\
        line_style: Cell Size          *# \[None, column_name, column\]; A line style per value of this column. column_name: per y column. None: one style.*\
        marker_shape: Cell Size          *# \[None, column_name, column\]; A marker shape per value of this column. column_name: per y column. None: one shape.*\
        marker_fill: Cell Size          *# \[None, column_name, column\]; A marker fill per value of this column. column_name: per y column. None: one fill.*\
        detail: None          *# \[None, columns\]; Columns splitting rows into separate lines, e.g. replicates. Each y column is always its own line.*\
        order: data          *# \[sorted, data\]; Group order: sorted, or as first seen.*\
    series:\
        base_axis:          *# \[x, y\]; The axis series are drawn along: bars stand on it, and aggregation adds along the other.*\
            value: y\
            from: bars\
            with:\
                axis.x.data.column: Power Density (mW/cm²)\
                axis.y.data.column: Cell\
                axis.x.data.aggregation: max\
                axis.y.data.aggregation: none\
                axis.x.tick.algorithm: auto\
                axis.y.tick.algorithm: all\
        aggregation:          *# \[none, sum, percent\]; Series at the same place: drawn as they are, stacked, or stacked to 100 %.*\
            value: sum\
            from: overlaid\
        offset: {value: side_by_side, from: overlaid}          *# \[none, side_by_side\]; side_by_side: series at the same place are drawn beside each other.*\
        value_label:\
            show: {value: true, from: bars}          *# \[true, false\]; Write each value by its mark.*\
            position:          *# \[auto, inside, outside\]; Inside a bar's end, beyond the mark, or inside where it fits.*\
                value: outside\
                from: labelled\
            format: {value: ".1f", from: labelled}          *# \[auto, text\]; Number format, e.g. ",.0f". auto: as the value axis's tick labels.*\
            total:          *# \[true, false\]; With aggregation sum, also write each stack's total.*\
                value: true\
                from: stacked\
    benchmark:\
        data_column:          *# \[None, column_name, column\]; Column marking the benchmark. column_name: a y column. None: no benchmark.*\
            value: None\
            with:\
                benchmark.value: None\
        value: Cell A          *# \[None, text, float\]; The benchmark's value in data_column (for column_name, a y column's name), drawn in series.benchmark style. Set with data_column.*\
        side: {value: end, from: bars}          *# \[start, end\]; Where the benchmark goes on a categorical axis it's a value of: before the other categories or after them.*\
    mark:\
        line:\
            show: false          *# \[true, false\]; Draw lines.*\
            connect_order: data          *# \[x, data\]; Point order along each line: by x, or by row.*\
            missing_values: gap          *# \[drop, gap\]; Rows missing x or y. drop: the line joins its neighbors. gap: the line breaks. Both are counted in lint's dropped-rows.*\
        marker:\
            show: false          *# \[true, false\]; Draw markers.*\
        bar:\
            show:          *# \[true, false\]; Draw bars, from 0 (1 on log); the value axis then includes it.*\
                value: false\
                from: marked_bars\
    legend:\
        method: key          *# \[auto, direct, key, none\]; This graph's method: one of the theme's legend.methods.*\
        key:\
            positions: {value: \[top_center\], from: key_shown}          *# \[top_left, top_center, top_right, bottom_left, bottom_center, bottom_right, right_top, right_center, right_bottom\]; Tried in order: the first clear one.*\
            inside: {value: false, from: key_shown}          *# \[true, false\]; Inside the plot area, or outside it: top\_\* above it, bottom\_\* below the x-axis title, right\_\* to its right.*\
            title:\
                text:          *# \[None, column_name, text\]; Key title. column_name: the encoding.color column's name. None: none.*\
                    value: None\
                    from: key_shown\
        color_bar:\
            title:\
                text:          *# \[None, column_name, text\]; Color bar title. column_name: the encoding.color column's name. None: none.*\
                    value: None\
                    from: colored_by_temperature
