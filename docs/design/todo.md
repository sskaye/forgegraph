# To do

<!-- fmc:1 -->What's still planned, in order.<!-- /fmc:1 -->

1. **A trial on real data.** A private pack for one organization, kept outside this repository (reference notes, and a house theme if it wants one); the skill run on the organization's data; one real request filed through the skill, to judge whether filing is easy enough. Fixes come with regression tests.
2. **A week of a scheduled dashboard.** A real dashboard, built from real data, updating daily for a week, then a report on its runs and anything that went wrong.
3. **Toward 1.0.** The `distribution` graph type (box plus strip, categorical x), the `iso_curve` layer (x·y = c and similar) and the `fit` layer, each with its definition reviewed as a proposal first; then a go/no-go on releasing 1.0.
4. **Studio.** A desktop app for making graphs without an AI (architecture D14): a UI plan and mockups first, then the app, judged by a hands-on trial.

Not planned: interactive output, and the deferred items in architecture §11. They're added on request.

<!-- forgemark-comments
- id: 1
  anchor_text: "What's still planned, in order."
  context_before: "# To do"
  context_after: "A trial on real data."
  author: Claude
  timestamp: 2026-10-29T15:03:02Z
  resolved: false
  body: |
    Problem: this list isn't kept up to date (item 3 still has the fit layer you deferred), and the README no longer links to it.
    Proposed change: delete docs/design/todo.md, with the two links to it in architecture.md (commented there).
-->
