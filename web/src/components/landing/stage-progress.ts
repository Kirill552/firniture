import type { StageId } from "./landing-copy";

export function resolveStageProgress(rawProgress: number): {
  stage: StageId;
  localProgress: number;
} {
  const finite = Number.isFinite(rawProgress) ? rawProgress : 0;
  const progress = Math.min(1, Math.max(0, finite));
  const index = Math.min(4, Math.floor(progress * 5));
  const stage = (index + 1) as StageId;
  const start = index * 0.2;
  const localProgress = progress === 1 ? 1 : (progress - start) / 0.2;
  return { stage, localProgress: Math.min(1, Math.max(0, localProgress)) };
}
