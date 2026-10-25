# Layout example: cell_performance, a paper figure

This page mirrors examples/layouts/paper/cell_performance.layout.yaml, which is the specification. A test fails if they ever differ.

name: cell_performance\
version: 0\
description: Voltage and resistance over a durability test, and the polarization curves after it, for cells A–C.\
extends: forgegraph_base/base_layout\
fixed_parameters: None\
variable_parameters:\
    specifications:\
        format: journal/journal-double\
    tabs:\
        Figure:\
            grid:\
                areas: \[\[voltage, polarization\],\
                        \[hfr,     polarization\]\]\
                column_widths: \[1, 1.3\]\
            tiles:\
                voltage: voltage_time.yaml\
                hfr: hfr_time.yaml\
                polarization: polarization.yaml
