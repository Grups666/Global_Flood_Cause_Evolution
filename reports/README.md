# Reports

`global_flood_cause_evolution.md` is the canonical reader-facing report.

`global_flood_cause_evolution.html` is the browser-first derivative. It embeds
all figures and styles in one file so it remains readable across an SSH client
boundary without copying an asset directory.

The `assets/` directory contains report-local PNG copies so Markdown viewers
that block parent-directory image access can render the figures. The canonical
publication PNG/SVG outputs remain under `outputs/figures/` and are regenerated
by the analysis pipeline.
