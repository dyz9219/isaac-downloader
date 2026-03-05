# Any4 Raw Adapter Design

Date: 2026-02-21

## Background

The converter must keep LeRobot `v3.0/v2.1/v2.0` on the GitHub any4 conversion chain, but current user inputs are raw packages (`aligned_joints.h5 + state.json + mp4`) rather than native any4 dataset layout (`task_info/*.json`, `observations/*`, `proprio_stats/*`).

Without adaptation, precheck blocks non-HDF5 routes.

## Decision

Use **Adapter A (sidecar adapter)**:

- Keep any4 scripts untouched.
- Build a minimal any4-compatible temporary dataset from each raw source.
- Feed the adapted dataset into `agibot2lerobot.agibot_h5`.
- Continue version migrations with compatibility fallback:
  - Prefer upstream scripts (`v30_to_v21`, `v21_to_v20`).
  - If upstream conversion cannot run on incomplete v3 metadata (for example missing `meta/episodes`),
    apply local metadata-only fallback to reach target contract.

## Scope

- In scope:
  - Raw input auto adaptation for LeRobot non-HDF5 conversion.
  - Precheck warning and pass for adaptable raw inputs.
  - Manifest observability fields for adapter usage.
- Out of scope:
  - Modifying any4 upstream scripts.
  - Packaging changes.

## Data Flow

1. Discover source.
2. Precheck:
   - `any4` source: pass.
   - `raw` source: pass with warning.
   - `unknown`: fail.
3. Runtime:
   - Non-HDF5 + `raw` -> adapter writes temporary any4 dataset.
   - Run `agibot_h5` on adapted root.
   - Run version downgrade scripts if target is `v2.1` or `v2.0`.
   - If downgrade scripts fail due missing v3 episode parquet metadata, run local fallback conversion.
4. Validate output format by target version.
5. Cleanup adapter working directory on success; preserve on failure.

## Adapter Contracts

### Input kinds

- `any4`: contains `task_info/*.json` and `observations/`.
- `raw`: contains `aligned_joints.h5` and `state.json` (directly or inside one nested folder / zip root).
- `unknown`: neither of the above.

### Temporary structure (per source)

Under `<output_parent>/.adapter_work/<source>_adapted/any4_dataset`:

- `task_info/<task_id>.json`
- `observations/<task_id>/<episode_id>/videos/*.mp4`
- `proprio_stats/<task_id>/<episode_id>/proprio_stats.h5`

### task_info minimal template

Each file is a list with one episode:

- `episode_id`
- `task_name`
- `init_scene_text`
- `label_info.action_config` (empty list by default)

## Raw Mapping Rules

### Proprio

Read from `aligned_joints.h5` and generate `proprio_stats.h5` with expected keys:

- state/*
- action/*

If key is missing or shape mismatched:

- fill zeros with target shape.
- append warning message.

### Version fallback rules

- `v3.0 -> v2.1` fallback:
  - rewrite `meta/info.json` to `codebase_version=v2.1` and legacy path templates.
  - ensure `meta/episodes.jsonl` and `meta/episodes_stats.jsonl` exist (empty allowed).
- `v2.1 -> v2.0` fallback:
  - rewrite `meta/info.json` to `codebase_version=v2.0`.
  - ensure `meta/stats.json` exists (empty JSON allowed).

### Videos

Required any4 video keys are populated in `videos/<key>_color.mp4`.

If raw key missing:

- fallback to an existing video (prefer `head.mp4`).
- append warning message.

## Observability

Manifest includes:

- `input_kind`
- `adapter_used`
- `adapter_workdir`

Failure message includes adapter working directory when available.

## Testing

1. Unit tests:
   - Input kind detection (`any4` / `raw` / `unknown`).
   - Precheck pass with warning for `raw`.
   - Non-HDF5 route invokes any4 module.
   - Version migration call chain remains correct.
2. Contract tests:
   - LeRobot version format assertions (`v3.0`, `v2.1`, `v2.0`).
   - HDF5 signature/readability assertions.
3. Smoke on target input:
   - Non-HDF5 routes pass precheck through adaptation.
   - HDF5 route unchanged.

## Acceptance Criteria

- Raw input no longer blocks non-HDF5 precheck.
- Non-HDF5 conversions still run via any4 GitHub chain.
- Output version checks pass.
- Adapter metadata appears in manifests.
