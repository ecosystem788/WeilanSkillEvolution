# Milestone 3: integration and CLI

Implement `build_plan(manifest_text, routes)` and the CLI. The plan has `assignments` sorted by parcel ID and `total_cost` formatted with two decimals using decimal half-up rounding. Each assignment contains parcel ID, route ID, and two-decimal cost using the same rounding. CLI reads manifest and routes JSON paths, writes canonical JSON to the requested output, creates parent directories, and returns nonzero without a partial output on invalid input. Preserve milestones 1 and 2.
