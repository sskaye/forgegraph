# Built-in pack: forgegraph_default/schedule, a schedule

This page mirrors src/forgegraph/packs/forgegraph_default/schedules/schedule.yaml, which is the specification. A test fails if they ever differ.

name: schedule          *# \[text\]; The name of the schedule, which also names its status file and log.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A default schedule to extend.          *# \[text\]; The description of the schedule.*\
extends: None          *# \[None, schedule\]; Each parameter not listed is inherited from this schedule. If None, this file must list every parameter.*\
 \
parameters: !var          *# !var/!fix sets whether a schedule may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    targets:\
        files: None          *# \[texts\]; The GraphSpec and layout files rendered on each run: absolute paths, paths starting with ~, or paths relative to this file. A schedule must set it.*\
        output_folder: None          *# \[None, text\]; The folder the outputs are saved in: an absolute path, a path starting with ~, or a path relative to the file that sets it. If None, each output is saved beside its target file.*\
    cadence:          *# When the job runs, in the machine's local time.*\
        interval:\
            count: 1          *# \[int > 0\]; The number of units between runs. For minutes, hours and months, it must divide 60, 24 or 12; for other units, it must be 1.*\
            unit: day          *# \[minute, hour, day, week, month, year\]; The unit that interval.count counts.*\
        at: "06:00"          *# \[None, text, texts\]; When in each unit the job runs: ":30", "06:00", "mon 06:00", "1 06:00", "Jan 1 06:00", or a list of these. If None, it runs at the start of the unit.*\
    freshness:\
        stamp:\
            show: true          *# \[true, false\]; Whether to draw the "data as of" stamp, with the cadence, in every output.*\
        stale_after_hours: auto          *# \[auto, float > 0\]; How old the data may get before the HTML page shows the stale banner. auto is one period plus 25%.*\
    status:\
        file: auto          *# \[auto, text\]; The status file: an absolute path, a path starting with ~, or a path relative to the file that sets it. auto uses \<name>.status.json in output_folder, or beside this file.*\
    on_failure:\
        command: None          *# \[None, texts\]; The program and arguments run, without a shell, when a run fails. If None, nothing is run.*\
        timeout_seconds: 60          *# \[int > 0\]; The time the command may take before it's stopped.*\
    on_success:\
        command: None          *# \[None, texts\]; The program and arguments run, without a shell, when a run succeeds. If None, nothing is run.*\
        timeout_seconds: 60          *# \[int > 0\]; The time the command may take before it's stopped.*
