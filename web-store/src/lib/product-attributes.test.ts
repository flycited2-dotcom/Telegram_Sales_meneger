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

  it("extracts garden equipment power attributes from product names", () => {
    expect(extractProductNameAttributes("Снегоуборщик бензиновый Elitech ST 0762LE 7л.с.")).toEqual([
      {
        key: "power_source",
        label: "Тип питания",
        value: "Бензиновый",
        normalizedValue: "petrol",
        numericValue: null,
        unit: null,
        source: "name",
      },
      {
        key: "power_hp",
        label: "Мощность двигателя",
        value: "7 л.с.",
        normalizedValue: "7",
        numericValue: 7,
        unit: "л.с.",
        source: "name",
      },
    ]);
  });

  it("extracts battery voltage and capacity from cordless equipment names", () => {
    expect(extractProductNameAttributes("Газонокосилка аккумуляторная Makita DLM538CT2, 36 В, 5 Ач")).toEqual([
      {
        key: "power_source",
        label: "Тип питания",
        value: "Аккумуляторный",
        normalizedValue: "battery",
        numericValue: null,
        unit: null,
        source: "name",
      },
      {
        key: "battery_voltage",
        label: "Напряжение аккумулятора",
        value: "36 В",
        normalizedValue: "36",
        numericValue: 36,
        unit: "В",
        source: "name",
      },
      {
        key: "battery_capacity",
        label: "Емкость аккумулятора",
        value: "5 Ач",
        normalizedValue: "5",
        numericValue: 5,
        unit: "Ач",
        source: "name",
      },
    ]);
  });

  it("extracts compact battery units without spaces", () => {
    expect(extractProductNameAttributes("Триммер аккумуляторный 18В 4Ач").map((attribute) => attribute.key)).toEqual([
      "power_source",
      "battery_voltage",
      "battery_capacity",
    ]);
  });
});
