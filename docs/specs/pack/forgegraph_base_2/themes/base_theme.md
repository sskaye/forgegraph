# Theme: forgegraph_base_2/base_theme

This page mirrors src/forgegraph/packs/forgegraph_base_2/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[text\]; The name of the theme.*\
version: 2          *# \[int ≥ 0\]; The version number of the specification.*\
description: Source Sans 3 at report sizes, the Tableau 10 palette, a dark full box, short outward ticks, a key before direct labels.          *# \[text\]; The description of the theme.*\
extends: forgegraph_base/base_theme          *# \[None, theme\]; Each parameter not listed is inherited from this theme. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    text:\
        font: Source Sans 3          *# \[text\]; The typeface.*\
        weight: light          *# \[light, regular, medium, semibold, bold\]; The weight.*\
    background:\
        color: None          *# \[None, hex color\]; The background color of the figure and the plot area. If None, the background is transparent.*\
    title:          *# \[text style\]; The graph's title.*\
        size: 1.45          *# \[float > 0\]; The size, × base size.*\
        weight: medium          *# \[light, regular, medium, semibold, bold\]; The weight.*\
        gap: 1.1          *# \[float ≥ 0\]; The gap between the text and whatever is around it, × base size.*\
    axis:\
        title:          *# \[text style\]; The axis titles.*\
            size: 1.27          *# \[float > 0\]; The size, × base size.*\
            weight: medium          *# \[light, regular, medium, semibold, bold\]; The weight.*\
            gap: 1.0          *# \[float ≥ 0\]; The gap between the text and whatever is around it, × base size.*\
        tick:          *# \[line style\]; The tick marks.*\
            length: 0.18          *# \[float ≥ 0\]; The tick length, × base size. If 0, the labels are drawn without tick marks.*\
            width: 0.073          *# \[float ≥ 0\]; The width, × base size. If 0, no line is drawn.*\
            algorithm: matplotlib          *# \[extended_wilkinson, wilkinson, heckbert, nelder, r_pretty, matplotlib\]; The published algorithm that places the major ticks on linear axes.*\
            log_algorithm: matplotlib          *# \[breaks_log, matplotlib\]; The algorithm that places the major ticks on log axes. breaks_log is R's algorithm and places about as many ticks as on a linear axis. matplotlib places them at powers of ten.*\
            label:          *# \[text style\]; The tick labels.*\
                size: 1.27          *# \[float > 0\]; The size, × base size.*\
                gap: 0.55          *# \[float ≥ 0\]; The gap between the text and whatever is around it, × base size.*\
    plot_area:\
        border:          *# \[line style\]; The plot area's border.*\
            width: 0.091          *# \[float ≥ 0\]; The width, × base size. If 0, no line is drawn.*\
            color: "#262626"          *# \[hex color\]; The color.*\
        aspect_ratio: 1.11          *# \[float > 0\]; The plot area's width ÷ its height.*\
    grid:          *# \[line style\]; The grid lines.*\
        width: 0.064          *# \[float ≥ 0\]; The width, × base size. If 0, no line is drawn.*\
        color: "#F2F2F2"          *# \[hex color\]; The color.*\
    series:\
        colors: tableau_10          *# \[okabe_ito, tol_bright, tol_muted, tableau_10, color_blind, hex colors\]; The colors given to the series, or to the values of a series' color column: a named palette or a list of colors.*\
        line:          *# \[line style\]; The series lines.*\
            width: !var 0.18          *# \[float ≥ 0\]; The width, × base size. If 0, no line is drawn.*\
            cap: round          *# \[butt, round, projecting\]; The shape of a line's ends.*\
        marker:\
            size: 0.64          *# \[float > 0\]; The marker size, × base size.*\
            edge:          *# \[line style\]; The outline of filled markers.*\
                width: !var 0.082          *# \[float ≥ 0\]; The width, × base size. If 0, no line is drawn.*\
        bar:\
            edge:          *# \[line style\]; The bar outlines.*\
                style: None          *# \[None, solid, dashed, dotted, dashdot\]; The line style. If None, no line is drawn.*\
        benchmark:          *# \[series style\]; How the benchmark looks. It looks like every other series, using the first item of each list, except for what is set here.*\
            marker:\
                edge:\
                    style: None          *# \[None, solid, dashed, dotted, dashdot\]; The line style. If None, no line is drawn.*\
            bar:\
                edge:\
                    style: None          *# \[None, solid, dashed, dotted, dashdot\]; The line style. If None, no line is drawn.*\
    legend:\
        methods: \[auto, key, direct\]          *# \[auto, direct, key, none\]; The methods graphs may use to name their series, tried in order when legend.method is auto. direct writes each name beside its line, and key lists the names in a key.*\
        label:          *# \[text style\]; The direct labels. Each label has its series' color.*\
            size: 0.91          *# \[float > 0\]; The size, × base size.*\
        key:\
            border:          *# \[line style\]; The line around the key.*\
                style: None          *# \[None, solid, dashed, dotted, dashdot\]; The line style. If None, no line is drawn.*\
            background: "#FFFFFFCC"          *# \[None, hex color\]; The fill color behind the key. If None, there is no fill.*\
            gap:\
                inner: 0.36          *# \[float ≥ 0\]; The gap inside the key between its edge and its entries, × base size.*\
                outer: 0.45          *# \[float ≥ 0\]; The gap between the plot area and the key, × base size.*\
                row: 1.0          *# \[float > 0\]; The gap between rows of entries, × base size.*\
            sample:\
                length: 2.27          *# \[float > 0\]; The length of the sample's line, × base size.*\
                gap: 0.9          *# \[float > 0\]; The gap between the sample and its name, × base size.*
