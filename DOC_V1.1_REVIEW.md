# Documentation V1.1 Maintenance Draft Review

**Date:** 2026-07-22
**Base:** Documentation V1.0 / Snapshot-017
**Status:** Approved

## Files Revised

- `docs/developer-guide.md`
- `docs/lidarr.md`
- `CHANGELOG.md`
- `DOCUMENT_INDEX.md`

## Maintenance Corrections

1. Removed obsolete `refresh_on_start` behavior from cache evaluation.
2. Updated Lidarr failure isolation to current per-entry behavior.
3. Added the stabilized exit-code contract:
   - 0 success / clean dry run
   - 1 Ctrl-C interruption
   - 2 dry run with warnings
   - 4 Plex unavailable; playlist operation skipped
   - 5 Plex live-resolution safety skip
   - noted standard argparse usage errors also return 2
4. Clarified normalization preservation of legitimate title words.
5. Clarified prebuilt normalized album-artist SearchIndex lookup.
6. Recorded that M3U8 implementation now conforms to the already approved format documentation.
7. Recorded the validated 145-test full regression baseline.

## Scope Discipline

This is a documentation-only maintenance release. It introduces no new application feature and does not
change the Documentation Standards V2.0 baseline.

After approval, the release should be finalized as the next documentation snapshot and the index status
changed from Draft to Approved.

## Approval

Documentation V1.1 maintenance changes approved on 2026-07-22.
