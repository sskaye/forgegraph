# forgegraph_base_2 trial: runbook

This trial tries the skill with a pack the way a user would, before the public release. The pack is `forgegraph_base_2`, built into ForgeGraph. The trial runs in three folders, one for each way a config can treat the pack:

1. **standard:** the main config lists the pack. Graphs are standard.
2. **folder-only:** only a folder config lists the pack. Graphs work but are non-standard, so they're watermarked.
3. **not-allowed:** the folder config doesn't list the pack. It can't be used.

Each folder gets its own main config through `FORGEGRAPH_CONFIG`, so the machine's own main config (~/.config/forgegraph/config.toml) is never read or changed.

The sample data in data/ is synthetic: monthly revenue by region, conversion by marketing channel, price against units sold, and daily active users with a few days missing.

## Setup

1. Install ForgeGraph from the main branch, and the skill. In your checkout of the repository:

```bash
git fetch && git checkout main && git pull
```

```bash
uv tool install --force .
```

```bash
forgegraph skill install
```

2. Make the trial folders, with the data, and a small pack, house, for step 8's reference note. Run this from the checkout, which sets `REPO` to it:

```bash
REPO=$(pwd) T=~/forgegraph-trial; mkdir -p $T/configs $T/standard $T/folder-only $T/not-allowed $T/house && printf 'name: house\nversion: 1.0.0\ndescription: Notes for the trial.\nissues: https://example.com/issues\nrequires: None\n' > $T/house/pack.yaml && for d in standard folder-only not-allowed; do cp $REPO/review/phase-06/runbook/data/*.csv $T/$d/; done
```

3. Write the two main configs and the two folder configs:

```bash
T=~/forgegraph-trial; printf 'packs = ["forgegraph_base", "forgegraph_base_2", "%s/house"]\n' $T > $T/configs/main-with-pack.toml && printf 'packs = ["forgegraph_base"]\n' > $T/configs/main-base.toml && printf 'packs = ["forgegraph_base", "forgegraph_base_2"]\n' > $T/folder-only/forgegraph.toml && printf 'packs = ["forgegraph_base"]\n' > $T/not-allowed/forgegraph.toml
```

4. Start each part's sessions from a terminal in that part's folder, with its main config, as each part shows. Start a new session for each step, unless the step is a follow-up.

## Part A: standard

Start sessions with:

```bash
cd ~/forgegraph-trial/standard && FORGEGRAPH_CONFIG=~/forgegraph-trial/configs/main-with-pack.toml claude
```

For every graph, check that:
- it looks like your matplotlib style: Source Sans 3 Light, a dark gray box, short outward ticks, the Tableau 10 colors, a transparent background, about 4 in across;
- it isn't watermarked;
- the GraphSpec names `forgegraph_base_2/base_theme` and `forgegraph_base_2/compact_format`.

Steps:

1. Ask: "Using the forgegraph_base_2 pack, plot monthly revenue for each region from sales_by_region.csv as lines."
   - Check the common points above, and that the regions are named, by direct labels or a key.
2. Ask: "Make a bar chart of the conversion rate for each marketing channel in channel_conversion.csv, sorted from highest to lowest, using the forgegraph_base_2 pack."
   - Check that the bars are sorted.
3. In the same session, ask: "Please print each value above its bar and change the title to 'Conversion by channel'."
   - Check that the same GraphSpec was edited, not a new one written.
4. Ask: "Can you plot units sold against price from price_vs_demand.csv as points, colored by product category, in the forgegraph_base_2 style?"
   - Check that the points are colored by category, and whether a log axis would read better.
5. Ask: "Plot daily active users from daily_active_users.csv with the forgegraph_base_2 pack, leaving a gap where readings are missing."
   - Check the gaps in late July and late August, and the date ticks.
6. Ask: "Put the revenue lines and the conversion bars side by side in one figure for a report, using the forgegraph_base_2 pack."
   - Check that the layout draws both, and that its format is a layout format.
7. Copy the reference note into the house pack, from a terminal in your checkout:

```bash
mkdir -p ~/forgegraph-trial/house/references && cp review/phase-06/runbook/house-note.md ~/forgegraph-trial/house/references/house.md
```

   - Then ask, without naming the pack: "Plot monthly revenue for the East region from sales_by_region.csv in our house style."
   - Check that the agent reads the note (`forgegraph pack-notes`) and uses the theme and format it names.
8. Ask: "Make a version of the forgegraph_base_2 theme with a light grid, called grid_theme, and use it to redraw the revenue graph."
   - Check that the agent makes a pack of its own for it (the built-in pack is part of ForgeGraph), with themes/grid_theme.yaml extending `forgegraph_base_2/base_theme` and setting only the grid.
   - Check that it lists the new pack in a folder config, and asks before changing the main config. If it doesn't change the main config, the graph is watermarked as non-standard and it says so.
9. Ask: "I'd like a violin plot of units sold by product category from price_vs_demand.csv in the forgegraph_base_2 style. If ForgeGraph can't make one, draw it anyway."
   - Check that it says ForgeGraph has no violin plot, then draws one on the blank canvas in the forgegraph_base_2 theme.
   - Check that the image is watermarked.

## Part B: folder-only

Start the session with:

```bash
cd ~/forgegraph-trial/folder-only && FORGEGRAPH_CONFIG=~/forgegraph-trial/configs/main-base.toml claude
```

1. Ask the question from step A1.
   - Check that the graph draws in the forgegraph_base_2 theme and is watermarked.
   - Check that the agent tells you it's non-standard because the main config doesn't list the pack.
2. Run `forgegraph catalog` in the folder, with the same `FORGEGRAPH_CONFIG`.
   - Check that it leads with the non-standard line and marks the pack and its specs `[non-standard]`.
3. Run `forgegraph load` on the image.
   - Check that it says it was drawn with a pack the main config didn't list.

## Part C: not-allowed

Start the session with:

```bash
cd ~/forgegraph-trial/not-allowed && FORGEGRAPH_CONFIG=~/forgegraph-trial/configs/main-with-pack.toml claude
```

1. Ask the question from step A1.
   - Check that the agent says the folder's config (forgegraph.toml) doesn't allow the pack, and asks how to go on.
   - Check that it doesn't draw the graph another way.

## Recording what you find

For each step, note "pass", or what went wrong, in the list below. Each step's files stay in its folder, and `forgegraph load <image>` shows what drew an image. Send me the notes and the ~/forgegraph-trial folder. I'll turn each problem into a fix with a regression test, and list what's fixed and what's deferred.

- A1:
- A2:
- A3:
- A4:
- A5:
- A6:
- A7:
- A8:
- A9:
- B1:
- B2:
- B3:
- C1:
