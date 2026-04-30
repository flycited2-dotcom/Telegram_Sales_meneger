import { describe, expect, it } from "vitest";
import { parseImageSyncLimit } from "@/lib/itp/images";

describe("parseImageSyncLimit", () => {
  it("uses null for full image sync and positive numbers for capped syncs", () => {
    expect(parseImageSyncLimit(undefined)).toBeNull();
    expect(parseImageSyncLimit("all")).toBeNull();
    expect(parseImageSyncLimit("0")).toBeNull();
    expect(parseImageSyncLimit("250")).toBe(250);
  });

  it("falls back to full sync for invalid values", () => {
    expect(parseImageSyncLimit("not-a-number")).toBeNull();
    expect(parseImageSyncLimit("-5")).toBeNull();
  });
});
