# Schedule specification: base_schedule

This page mirrors src/forgegraph/packs/forgegraph_base/schedules/base_schedule.yaml, which is the specification. A test fails if they ever differ.

name: base_schedule          *# \[text\]; The name of the schedule. Names the status file and log.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: The base schedule that others can inherit from.          *# \[text\]; The description of the schedule.*\
extends: None          *# \[None, schedule\]; Each parameter not listed is inherited from this schedule. If None, this file must list every parameter.*\
 \
fixed_parameters: None          *# List of fixed parameters for the schedule, None if none.*\
 \
variable_parameters:          *# List of variable parameters for the schedule, None if none.*\
    targets:\
        files: None          *# \[texts\]; GraphSpec and layout files rendered each run: absolute, from ~, or relative to this file. A schedule must set it.*\
        output_folder: None          *# \[None, text\]; Folder the outputs are saved in. None: beside each target file.*\
    cadence:          *# When the job runs, in the machine's local time.*\
        interval: 1          *# \[positive int\]; Units between runs: a divisor of 60 (minute), 24 (hour) or 12 (month); otherwise 1.*\
        interval_unit: day          *# \[minute, hour, day, week, month, year\]; The unit interval counts in.*\
        at: "06:00"          *# \[None, text, texts\]; When in each unit: ":30", "06:00", "mon 06:00", "1 06:00", "Jan 1 06:00", or a list. None: its start.*\
    freshness:\
        stamp: true          *# \[true, false\]; Draw the "data as of" stamp, with the cadence, in every output.*\
        stale_after_hours: auto          *# \[auto, positive float\]; Data age after which the HTML page shows the stale banner. auto: a period plus 25%.*\
    status:\
        file: auto          *# \[auto, text\]; The status file. auto: \<name>.status.json in output_folder, or beside this file.*\
    on_failure:\
        command: None          *# \[None, texts\]; Program and arguments run, without a shell, when a run fails. None: none.*\
        timeout_seconds: 60          *# \[positive int\]; Time allowed for the command before it's stopped.*\
    on_success:\
        command: None          *# \[None, texts\]; Program and arguments run, without a shell, when a run succeeds. None: none.*\
        timeout_seconds: 60          *# \[positive int\]; Time allowed for the command before it's stopped.*
