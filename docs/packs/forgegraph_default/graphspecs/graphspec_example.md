# Built-in pack: forgegraph_default/graphspec_example, a GraphSpec

This page mirrors src/forgegraph/packs/forgegraph_default/graphspecs/graphspec_example.yaml, which is the specification. A test fails if they ever differ.

name: graphspec_example          *# \[text\]; The name of the GraphSpec.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: The default pack's example GraphSpec for extension and the catalog.          *# \[text\]; The description of the GraphSpec.*\
extends: None          *# \[None, graphspec\]; Each parameter not listed is inherited from this GraphSpec. If None, this file must list every parameter.*\
 \
parameters: !var          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        graph_type: xy          *# \[graph type\];*\
        theme: forgegraph_default/light_theme          *# \[theme\];*\
        format: forgegraph_default/compact_format          *# \[format\];*\
    text:\
        title: Polarization, 60 °C          *# \[None, text\]; The graph's title. If None, there is no title.*\
    data:\
        file: polarization.parquet          *# \[None, text\]; A Parquet file holding the DataFrame to draw: an absolute path, a path starting with \~, or a path relative to the folder of the file that sets it. If None, the DataFrame is passed through the Python API.*\
        preprocessing: None          *# \[None, text\]; Where the code that made the data is: a path, a URL or a note. It's recorded in provenance and never read. If None, it's not given.*\
    axis:\
        x:\
            data:\
                column: "Cell Current (mA/cm²)"          *# \[None, column\]; The column on this axis when it's arrangement.base_axis, which a GraphSpec must then set. Otherwise, it must be None.*\
                type: auto          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto selects datetime for dates, categorical for text, and decimal or integer for numbers.*\
                order:\
                    method: source          *# \[source, alphanumeric, value\]; The order of the categories. source keeps the order in the data, alphanumeric sorts them naturally, and value sorts them by the other axis's value.*\
                    direction: ascending          *# \[ascending, descending\]; The direction of the category order.*\
            title: column_name          *# \[None, column_name, text\]; The axis title. column_name uses the name of axis.column if it's the base_axis or the series' column if it's not. With several series, use text or None.*\
            scale: linear          *# \[linear, log\]; The axis scale.*\
            min: None          *# \[None, float, date\]; The axis minimum. On a datetime axis, it's a date, e.g. 2025-08-25 or "2025-08-25T06:00". If None, it's the lowest value minus plot_area.gap × the data's range.*\
            max: None          *# \[None, float, date\]; The axis maximum. On a datetime axis, it's a date, e.g. 2025-08-25 or "2025-08-25T06:00". If None, it's the highest value plus plot_area.gap × the data's range.*\
            tick:\
                algorithm: auto          *# \[auto, all, manual\]; How the ticks are placed. auto uses the theme's algorithm, or on dates, the boundaries of one calendar unit. all places a tick at every value. manual places one every tick.step.*\
                step: None          *# \[None, float > 0, text\]; The distance between ticks when algorithm is manual, e.g. 5 or "2 week". On a log axis, it's a factor.*\
                label:\
                    format: auto          *# \[auto, format\]; The tick label format. auto chooses one from the values, and for dates, from the tick unit.*\
        y:\
            data:\
                column: None          *# \[None, column\]; The column on this axis when it's arrangement.base_axis, which a GraphSpec must then set. Otherwise, it must be None.*\
                type: auto          *# \[auto, decimal, integer, datetime, categorical\]; The column's type. auto selects datetime for dates, categorical for text, and decimal or integer for numbers.*\
                order:\
                    method: source          *# \[source, alphanumeric, value\]; The order of the categories. source keeps the order in the data, alphanumeric sorts them naturally, and value sorts them by the other axis's value.*\
                    direction: ascending          *# \[ascending, descending\]; The direction of the category order.*\
            title: column_name          *# \[None, column_name, text\]; The axis title. column_name uses the name of axis.column if it's the base_axis or the series' column if it's not. With several series, use text or None.*\
            scale: linear          *# \[linear, log\]; The axis scale.*\
            min: None          *# \[None, float, date\]; The axis minimum. On a datetime axis, it's a date, e.g. 2025-08-25 or "2025-08-25T06:00". If None, it's the lowest value minus plot_area.gap × the data's range.*\
            max: None          *# \[None, float, date\]; The axis maximum. On a datetime axis, it's a date, e.g. 2025-08-25 or "2025-08-25T06:00". If None, it's the highest value plus plot_area.gap × the data's range.*\
            tick:\
                algorithm: auto          *# \[auto, all, manual\]; How the ticks are placed. auto uses the theme's algorithm, or on dates, the boundaries of one calendar unit. all places a tick at every value. manual places one every tick.step.*\
                step: None          *# \[None, float > 0, text\]; The distance between ticks when algorithm is manual, e.g. 5 or "2 week". On a log axis, it's a factor.*\
                label:\
                    format: auto          *# \[auto, format\]; The tick label format. auto chooses one from the values, and for dates, from the tick unit.*\
    arrangement:          *# How the series are placed relative to each other.*\
        base_axis: x          *# \[x, y\]; The common axis for all series. Bars stand on it, and stacking adds values along the other axis.*\
        stacking: none          *# \[none, sum, percent\]; How series at the same location are combined. none draws each as it is, sum stacks them, and percent stacks them to 100 %.*\
        offset: none          *# \[none, side_by_side\]; side_by_side draws series at the same location beside each other instead of over each other.*\
        total:\
            show: false          *# \[true, false\]; Whether to write each stack's total when stacking is sum.*\
    series:          *# The series drawn, each under its name in the legend. A GraphSpec must list at least one. Each series has these parameters, and it can also set the theme's variable series parameters for itself.*\
        "Cell Voltage (V)":\
            column: name          *# \[name, column\]; The column of values the series draws along the axis that isn't arrangement.base_axis. name uses the column with the series' name.*\
            aggregation:          *# \[aggregation style\]; How rows at the same location are combined into one point. If its function is None, each row is drawn.*\
            split: \[Cell, Run\]          *# \[None, columns\]; Columns whose values split the series into separate lines, e.g. replicates.*\
            order: sorted          *# \[sorted, data\]; The order of the series' groups: sorted, or data for the order in which they first appear.*\
            color: Cell          *# \[series, hex color, column\]; The series' color. series takes the next palette color, and a column gives each of its values its own.*\
            color_scale: auto          *# \[auto, categorical, continuous\]; For a color column: categorical uses the palette, continuous a color scale and color bar, and auto continuous for numbers.*\
            opacity: 1          *# \[0-1\]; The opacity of lines, markers and bars.*\
            line:\
                show: true          *# \[true, false\]; Whether to draw lines.*\
                style: first          *# \[first, series, solid, dashed, dotted, dashdot, column\]; The line style. first is the theme's first line style, series takes the next one, and a column gives each of its values its own.*\
                connect_order: x          *# \[x, data\]; The order in which points are connected along each line: by x, or data for the order of the rows.*\
                interpolate: linear          *# \[linear, step_after, step_before, step_center, smooth\]; How the line joins points: straight, in flat steps that change at the next point, before it or midway, or as a smooth curve.*\
                missing_values: drop          *# \[drop, gap\]; What happens to rows missing x or y. drop joins the line across them, and gap breaks the line. Lint counts both in dropped-rows.*\
            marker:\
                show: true          *# \[true, false\]; Whether to draw markers.*\
                shape: first          *# \[first, series, circle, square, triangle_up, triangle_down, diamond, cross, plus, column\]; The marker shape. first is the theme's first marker shape, series takes the next one, and a column gives each of its values its own.*\
                fill: first          *# \[first, series, filled, open, column\]; The marker fill. first is the theme's first marker fill, series takes the next one, and a column gives each of its values its own.*\
                size: 0.5          *# \[float > 0\]; The marker size, × base size.*\
            bar:\
                show: false          *# \[true, false\]; Whether to draw bars. Bars start at 0, or at 1 on a log axis, and the value axis then always includes that value.*\
                width: 0.8          *# \[0-1\]; The fraction of the distance between neighboring bar positions that the bars at one position fill.*\
                gap: 0.1          *# \[0-1\]; The fraction of each side-by-side bar's space left empty between it and the next bar.*\
            value_label:          *# \[text style, look from series.value_label\]; The value labels.*\
                show: false          *# \[true, false\]; Whether to write each value next to its mark.*\
                position: auto          *# \[auto, inside, outside\]; Where each value is written: inside the end of its bar, or outside, just beyond its mark. auto writes it inside if it fits and outside otherwise. On stacks, values are always inside.*\
                format: auto          *# \[auto, format\]; The value label format. auto uses the format of the value axis's tick labels.*\
    benchmark:\
        data_column: Cell          *# \[None, series, column\]; The column that identifies the benchmark. series means the benchmark is one of the series. If None, there is no benchmark.*\
        value: Benchmark          *# \[None, text, float, date\]; The benchmark's value in data_column: a series' name with series, or a date for a date column. The benchmark is drawn in the series.benchmark style. Set it together with data_column.*\
        side: start          *# \[start, end\]; Where the benchmark is placed when it's a category on a categorical axis: before the other categories or after them.*\
    legend:\
        method: auto          *# \[auto, direct, key, none\]; How this graph names its series: one of the theme's legend.methods.*\
        key:\
            positions: \[top_right, top_left, bottom_right, bottom_left\]          *# \[top_left, top_center, top_right, bottom_left, bottom_center, bottom_right, right_top, right_center, right_bottom\]; The positions to try, in order. The key goes in the first one where it doesn't overlap the data.*\
            inside: true          *# \[true, false\]; Whether the key is inside the plot area. If false, top positions are above the plot area, bottom positions are below the x-axis title, and right positions are to its right.*\
            title:\
                text: column_name          *# \[None, column_name, text\]; The title of every key. column_name uses the name of each key's column. Other text is allowed only when there is one key. If None, there is no title.*\
        color_bar:\
            title:\
                text: column_name          *# \[None, column_name, text\]; The color bar's title. column_name uses the name of the series' color column. If None, there is no title.*\
    output:\
        dpi: 600          *# \[int > 0\]; The resolution of png, jpg and tiff files, in dots per inch.*\
        file_types: \[png\]          *# \[png, jpg, tiff, svg, pdf, html\]; The file types to save.*\
    provenance:\
        level: full          *# \[full, minimal, off\]; What each saved file records about how it was made. full records every value and the data file. minimal records the GraphSpec and the specs. off records nothing.*\
    layers:          *# The layers drawn on the graph, in this order, each under a name the GraphSpec chooses. A layer may set the look its theme marks !var.*\
        target:\
            type: reference          *# \[layer type\]; The layer's type: one of the graph type's layer.types.*\
            axis: y          *# \[x, y\]; The axis the values are on. y draws horizontal lines.*\
            line_1:\
                value: 1.2          *# \[None, float, date, column\]; A number, a date, or a column.*\
                label:\
                    text: Target 1.2 V          *# \[None, aggregation, value, aggregation_value, text\]; aggregation writes e.g. Mean, value e.g. 14.9, and aggregation_value e.g. Mean: 14.9. Other text is written as given.*\
        conditions:\
            type: note          *# \[layer type\]; The layer's type: one of the graph type's layer.types.*\
            text: "60 °C, 1 atm, H₂/air"          *# \[text\]; The note's text, in label markup. A line break starts a new line.*
