import { describe, expect, it } from "vitest";
import {
  catalogAttributeFacetKeys,
  catalogRangeAttributeKeys,
  getCatalogAttributeDefinition,
  getCatalogAttributeKeysForCategory,
} from "@/lib/catalog-attribute-registry";

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

  it("limits laundry categories to laundry-relevant attributes", () => {
    const keys = getCatalogAttributeKeysForCategory({ categoryName: "Сушильные машины", categorySlug: "sushilnye-mashiny-18029" });

    expect(keys).toEqual(expect.arrayContaining(["load_capacity", "drying_type", "inverter_motor", "depth_cm", "program_count", "color"]));
    expect(keys).not.toContain("power_hp");
    expect(keys).not.toContain("electrical_product_type");
    expect(keys).not.toContain("cable_section");
  });

  it("keeps electrical filters available only in electrical categories", () => {
    const keys = getCatalogAttributeKeysForCategory({ categoryName: "Кабель и провод", categorySlug: "kabel-i-provod" });

    expect(keys).toEqual(expect.arrayContaining(["electrical_product_type", "cable_section", "cable_cores", "voltage", "ip_rating"]));
    expect(keys).not.toContain("load_capacity");
    expect(keys).not.toContain("drying_type");
  });
});
