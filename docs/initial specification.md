# **Data Visualizer \- Specification**

Author: Steven Kaye  
Version: 0.1

## 

# Problem

During the course of their work, scientists and engineers routinely create graphs and other data visualizations to explore data, test hypotheses, and communicate results to others.

There are numerous programs to assist with this, but none of them satisfy all of the following:

1. Easy and fast to create the graph  
2. Flexible enough to create all common graph types  
3. Enable consistent, clear styling using best practices and/or the standard styles for the relevant organization (company, journal, etc.)  
4. Enable arrangement in dashboards  
5. Useable with modern AI agents (increasingly  a routine part of the research process)

Some examples:

Tableau

* Yes, it’s main selling point  
* Mixed. Basic graphs yes, but it doesn’t natively support error bars and other common features needed in science & engineering  
* Fails miserably. It can create a nice looking graph, but there’s no way to save the format so it replicates by default.  
* Yes, but the interface is clunky.  
* No.

Excel

1. Not easy or fast.  
2. Yes, very flexible.  
3. Not sure, but it’s definitely hard to get it right.  
4. No.  
5. Yes.

SigmaPlot, Origin, other “Scientific” graphing software

1. No. They’re very cumbersome  
2. Mostly yes.  
3. Yes, their main selling point.  
4. Not last I checked, but may have changed.  
5. Not last I checked, but may have changed.

# 

# Solution

An agent skill and associated library that enable low-labor, fast, and consistent construction of high-quality graphs from a variety of data sources.

# 

# Users

* Human scientists/engineers via the following interfaces  
  * Python scripts or jupyter notebooks  
  * A dedicated desktop application  
  * Working with an AI via desktop app (Claude, ChatGPT, etc.), terminal (claude code, codex)  
* AI agents via their standard interfaces

# 

# Data Sources

* Pandas dataframes  
* Flat files where the first row are the field names and subsequent rows are the values   
  * Types: xlsx, xls, csv, tab, tsv  
  * Imported by: basic pandas import   
* SQL database tables (at least PostgreSQL to start)

## 

# Features

## Skill

*  A skill that knows how to work with the graphing library and data sources, enabling a person to request a graph or set of graphs and get them quickly and easily.  
* In addition to producing graphs on demand, it should be capable of creating code or a recurring task that recreates a graph or dashboard on a schedule (e.g. updating a library analysis 1/day so it always has the latest data).  
* If someone asks for a graph that’s not represented in the graphing library, the skill will do its best to extrapolate from the existing set of graphs.  
  * It should then warn the user that this isn’t a supported graph type and that they should authorize a feature request if they want to use that type of graph.  
  * If authorized, it should create a proposed specification for the graphing library and then submit to github in a way so that it’s easy for a human to read/comment on the specification.  
* Example uses:  
  * Scientists analyzing a dataset will ask for a set of graphs, look at them, ask for another, rinse-repeat.  
  * An operations team will work with the skill to create a dashboard for lab throughput from their excel records, then set up a recurring task to update that dashboard daily.  
  * A controls engineer will ask for a graph of their model output (csv files on their laptop).

## 

## Library

* Code that produces graphs from a pandas dataframe.  
* Each graph type should have a human readable/commentable specification with a machine readable specification. The machine-readable version is the source, with the human-readable version deterministically derived from it. The human-readable specification should include example graphs that show what the baseline case and each parameter variation looks like.  
  * The idea is for humans to be able to look at the graphs and adjust the specifications (either directly or via request to AI) to get the code producing graphs of the desired appearance.  
  * An HTML file with tabs for each graph type would be an easy way to implement this. My forgemark software enables commenting on an html file and is human-useable and AI readable.  
* In addition to single graphs, there should also be code to produce dashboards of multiple graphs.  
* The code will be used by the skill, but also any other time someone wants to make a graph. Examples:  
  * When controls engineers are developing models, they often include graph outputs as part of validation checks.  
  * Scientists have jupyter notebooks they use for data analysis.  
  * Operations teams have standard dashboards we update for tracking lab throughput, experimental queue, etc.

## Initial Graph Types

* I have provided some examples in pdfs to give you a sense of the breadth we need to eventually get to.  
* We can start simple with just scatter and bar plots.

## Architecture Proposal

* I’ve provided a previous architecture proposal I put together with another agent.  
* Caveat 1: This was an older model, you are more advanced and may have ideas or see opportunities or issues the previous agent missed.  
* Caveat 2: The original proposal was for a suite of tools that would be just for my company. I’ve decided to make this more general and eventually release it publicly. Some of the architecture likely needs to change to accommodate this.

# Questions & Concerns

* None

# UI/UX

* See above.