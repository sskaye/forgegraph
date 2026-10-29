# Open issues

Last updated: 10/29/26

## [#81](https://github.com/sskaye/forgegraph/issues/81): ask the user to file a feature request after making something non-standard

- **Filed by:** sskaye.
- **Summary:** users ask their agents for features ForgeGraph doesn't have, and the agents make them anyway, so the request never reaches ForgeGraph unless someone reminds the user to file one. Whenever an agent makes a non-standard graph or layout, or any visual not drawn by ForgeGraph, it should ask the user whether they'd like to file a feature request.
- **Verification:** confirmed. The skill offers a request only before drawing, when a fixed parameter or a missing graph type blocks the request (SKILL.md, workflow step 2). Nothing asks after something non-standard has been drawn: a graph from a pack only a folder config lists, a drawing on `forgegraph.blank`, or a chart made some other way.
- **Proposal:**
  1. A step in the skill's workflow, after step 5: "If anything you drew is non-standard or wasn't drawn by ForgeGraph, say what ForgeGraph couldn't do and ask the user whether to file a feature request (references/requests.md)."
  2. As 1, and ForgeGraph's own message about a non-standard file (from `render` and the API) also says that what's missing can be requested at the pack's `issues` address, so agents that haven't loaded the skill see it too.

  Recommendation: 1, the smallest change that meets the need. 2 reaches agents without the skill, but adds a line to every non-standard message, including when someone is just trying out their own pack.
- **Decision:** open.
