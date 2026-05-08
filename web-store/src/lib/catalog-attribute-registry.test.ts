import { describe, expect, it } from "vitest";
import { catalogAttributeFacetKeys, catalogRangeAttributeKeys, getCatalogAttributeDefinition } from "@/lib/catalog-attribute-registry";

describe("catalog attribute registry", () => {
  it("keeps filterable keys ordered and exposes numeric range keys", () => {
    expect(catalogAttributeFacetKeys.slice(0, 4)).toEqual(["storage_type", "storage_capacity", "ram", "screen_diagonal"]);
    expect(catalogRangeAttributeKeys).toContain("storage_capacity");
    expect(catalogRangeAttributeKeys).toContain("power_hp");
    expect(catalogRangeAttributeKeys).toContain("cable_section");
  });

  it("returns UI metadata for new electrical and computer attributes", () => {
    expect(getCatalogAttributeDefinition("cable_section")).toMatchObject({
      label: "Сечение кабеля",
      valueType: "number",
      unit: "мм²",
      control: "range",
    });
    expect(getCatalogAttributeDefinition("processor_family")).toMatchObject({
      label: "Процессор",
      valueType: "enum",
      control: "checkbox",
    });
  });
});
