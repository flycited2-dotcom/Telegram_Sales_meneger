import { describe, expect, it } from "vitest";
import { extractProductNameAttributes } from "@/lib/product-attributes";

describe("extractProductNameAttributes", () => {
  it("extracts normalized climate attributes from dehumidifier names", () => {
    expect(
      extractProductNameAttributes("Осушитель воздуха Ballu Vector BD-30L VT белый, 30 л/сутки, 4 л, очистка воздуха"),
    ).toEqual([
      {
        key: "daily_capacity",
        label: "Производительность",
        value: "30 л/сутки",
        normalizedValue: "30",
        numericValue: 30,
        unit: "л/сутки",
        source: "name",
      },
      {
        key: "tank_volume",
        label: "Объем бака",
        value: "4 л",
        normalizedValue: "4",
        numericValue: 4,
        unit: "л",
        source: "name",
      },
    ]);
  });

  it("extracts TV attributes including diagonal, resolution and smart tv", () => {
    expect(extractProductNameAttributes('Телевизор Samsung UE55CU7100U 55" 4K UHD Smart TV')).toEqual([
      {
        key: "screen_diagonal",
        label: "Диагональ",
        value: '55"',
        normalizedValue: "55",
        numericValue: 55,
        unit: "дюйм",
        source: "name",
      },
      {
        key: "resolution",
        label: "Разрешение",
        value: "4K UHD",
        normalizedValue: "4k_uhd",
        numericValue: null,
        unit: null,
        source: "name",
      },
      {
        key: "smart_tv",
        label: "Smart TV",
        value: "Да",
        normalizedValue: "yes",
        numericValue: null,
        unit: null,
        source: "name",
      },
    ]);
  });

  it("extracts computer memory and storage attributes", () => {
    expect(extractProductNameAttributes("Ноутбук Lenovo IdeaPad 15, 16 ГБ RAM, SSD 512 ГБ")).toEqual([
      {
        key: "ram",
        label: "Оперативная память",
        value: "16 ГБ",
        normalizedValue: "16",
        numericValue: 16,
        unit: "ГБ",
        source: "name",
      },
      {
        key: "storage_type",
        label: "Тип накопителя",
        value: "SSD",
        normalizedValue: "ssd",
        numericValue: null,
        unit: null,
        source: "name",
      },
      {
        key: "storage_capacity",
        label: "Объем накопителя",
        value: "512 ГБ",
        normalizedValue: "512",
        numericValue: 512,
        unit: "ГБ",
        source: "name",
      },
    ]);
  });
});
