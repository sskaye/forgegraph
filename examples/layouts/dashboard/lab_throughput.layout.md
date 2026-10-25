# Layout example: lab_throughput, an ops dashboard

This page mirrors examples/layouts/dashboard/lab_throughput.layout.yaml, which is the specification. A test fails if they ever differ.

name: lab_throughput\
version: 0\
description: Daily operations view of lab throughput.\
extends: forgegraph_base/base_layout\
fixed_parameters: None\
variable_parameters:\
    specifications:\
        format: ops/dashboard\
    separators:\
        line:\
            show: true\
            border: true\
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
