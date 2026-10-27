# Pack example: acme/workday, a schedule to extend

This page mirrors examples/packs/acme/schedules/workday.yaml, which is the specification. A test fails if they ever differ.

name: workday          *# \[text\]; The name of the schedule.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Acme's working-day cadence and failure alert; a schedule extends it and names its targets.          *# \[text\]; The description of the schedule.*\
extends: forgegraph_base/base_schedule          *# \[None, schedule\]; Each parameter not listed is inherited from this schedule. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a schedule may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    cadence:\
        interval:\
            unit: week          *# \[minute, hour, day, week, month, year\]; The unit interval.count counts in.*\
        at: \[mon 06:00, tue 06:00, wed 06:00, thu 06:00, fri 06:00\]          *# \[None, text, texts\]; When in each unit it runs.*\
    on_failure:\
        command: \[acme-alert, --channel, lab-dashboards\]          *# \[None, texts\]; Program and arguments run, without a shell, when a run fails.*
