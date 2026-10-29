# Layout example: lab_throughput, an ops dashboard

This page mirrors examples/layouts/dashboard/lab_throughput.layout.yaml, which is the specification. A test fails if they ever differ.

name: lab_throughput\
version: 0\
description: Daily operations view of lab throughput.\
extends: forgegraph_default/layout\
 \
parameters:          *# !var/!fix sets whether a layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        format: ops/dashboard\
    separators:\
        line:\
            <!-- fmc:1 -->width: 0.05<!-- /fmc:1 -->\
        border:\
            show: true\
    tabs:\
        Overview:\
            grid:\
                areas: \[\[weekly,  weekly,   lost\],\
                        \[samples, run_time, .   \]\]\
                row_heights: \[1.2, 1\]\
            tiles:\
                weekly: throughput_weekly.yaml\
                lost: lost_runs.yaml\
                samples: samples_weekly.yaml\
                run_time: run_time.yaml\
        By instrument:\
            grid:\
                areas: \[\[hplc_01,  hplc_02   \],\
                        \[gc_ms_01, icp_oes_01\]\]\
            tiles:\
                hplc_01: runs_hplc_01.yaml\
                hplc_02: runs_hplc_02.yaml\
                gc_ms_01: runs_gc_ms_01.yaml\
                icp_oes_01: runs_icp_oes_01.yaml

<!-- forgemark-comments
- id: 1
  anchor_text: "width: 0.05"
  context_before: "icitly overridden.*\\ specifications:\\ format: ops/dashboard\\ separators:\\ line:\\"
  context_after: "\\ border:\\ show: true\\ tabs:\\ Overview:\\ grid:\\ areas: \\[\\[weekly, weekly, lost\\"
  author: Claude
  timestamp: 2026-10-29T15:03:02Z
  resolved: false
  body: |
    Problem: this dashboard sets the separator line's width and border.show, but inherits separators.line.style: None from forgegraph_default/layout, and a line is drawn only when its style draws one (layouts/separators.py). So it draws no lines between the tiles and no border, and doesn't show the 0.5 line under the tab bar meeting the border.
    Proposed change: add style: solid above this line (in lab_throughput.layout.yaml), then check the drawn dashboard. If no lines were intended, delete width and border instead.
-->
