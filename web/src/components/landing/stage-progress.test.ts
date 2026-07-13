import { describe, expect, it } from "vitest";

import { resolveStageProgress } from "./stage-progress";

describe("resolveStageProgress", () => {
  it.each([
    [-1, 1, 0],
    [0, 1, 0],
    [0.1999, 1, 0.9995],
    [0.2, 2, 0],
    [0.4, 3, 0],
    [0.6, 4, 0],
    [0.8, 5, 0],
    [1, 5, 1],
    [2, 5, 1],
  ])("maps %s to stage %s", (raw, stage, local) => {
    const result = resolveStageProgress(raw);
    expect(result.stage).toBe(stage);
    expect(result.localProgress).toBeCloseTo(local, 3);
  });

  it("maps NaN to the first stage", () => {
    expect(resolveStageProgress(Number.NaN)).toEqual({ stage: 1, localProgress: 0 });
  });
});
