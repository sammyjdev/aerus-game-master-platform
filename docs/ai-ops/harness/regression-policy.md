# Regression Policy

## Classification

- new regression: failing assertion not failing in previous baseline
- persistent regression: still failing from previous baseline
- fixed regression: failed before, passes now

## Actions

1. New regression blocks merge by default.
2. Persistent regression requires explicit owner and ETA.
3. Waiver is allowed only with time-box and linked follow-up issue.

## Evidence required

- run profile used
- scenario ids affected
- top failed assertions
- comparison summary vs previous run
