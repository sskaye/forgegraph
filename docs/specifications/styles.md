# Styles specification: styles

This page mirrors src/forgegraph/specifications/styles.yaml, which is the specification. A test fails if they ever differ.

name: styles          *# \[text\]; The name of the specification.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Styles that graph types and layers share. A category marked with a style has its parameters, with these defaults, and lists only those it changes.          *# \[text\]; The description of the specification.*\
 \
aggregation_style:          *# How a column's rows are combined into one number. Marked \[aggregation style\].*\
    function: None          *# \[None, mean, median, sum, min, max, percentile, stddev, stderr, ci\]; The aggregate. ci is half the 95 % confidence interval of the mean. If None, each row's value is used.*\
    multiplier: 1          *# \[float\]; The number the aggregate is multiplied by, e.g. 2 for twice the standard deviation.*\
    percentile: 50          *# \[0-100\]; The percentile when function is percentile.*
