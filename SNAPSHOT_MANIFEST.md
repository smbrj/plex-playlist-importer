# Documentation Snapshot Manifest

**Snapshot:** 018  
**Documentation Release:** V1.1  
**Date:** 2026-07-22  
**Type:** Full Documentation Maintenance Release  
**Status:** Approved

## Base

Documentation V1.0 / Snapshot-017.

## V1.1 Maintenance Changes

- Removed obsolete `refresh_on_start` behavior from cache documentation.
- Updated Lidarr documentation to reflect current per-entry request-failure isolation.
- Documented the stabilized application exit-code contract, including the standard `argparse` exit-code-2 overlap.
- Clarified normalization behavior so legitimate title words are preserved when they are not metadata.
- Clarified the prebuilt normalized album-artist SearchIndex lookup.
- Confirmed `.m3u8` parser implementation now conforms to the approved supported-format documentation.
- Recorded the post-cleanup regression baseline of 145 passing tests.

## Recovery Point

Snapshot-018 supersedes Snapshot-017 as the preferred documentation recovery point.
Snapshot-017 remains the immutable Documentation V1.0 baseline.
