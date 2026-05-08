export type CatalogAttributeValueType = "enum" | "number" | "boolean" | "text";
export type CatalogAttributeControl = "checkbox" | "range" | "boolean";

export type CatalogAttributeDefinition = {
  key: string;
  label: string;
  valueType: CatalogAttributeValueType;
  control: CatalogAttributeControl;
  unit?: string;
};

export const catalogAttributeDefinitions = [
  { key: "storage_type", label: "Тип накопителя", valueType: "enum", control: "checkbox" },
  { key: "storage_capacity", label: "Объем накопителя", valueType: "number", control: "range", unit: "ГБ" },
  { key: "ram", label: "Оперативная память", valueType: "number", control: "range", unit: "ГБ" },
  { key: "screen_diagonal", label: "Диагональ", valueType: "number", control: "range", unit: "дюйм" },
  { key: "resolution", label: "Разрешение", valueType: "enum", control: "checkbox" },
  { key: "smart_tv", label: "Smart TV", valueType: "boolean", control: "checkbox" },
  { key: "daily_capacity", label: "Производительность", valueType: "number", control: "range", unit: "л/сутки" },
  { key: "tank_volume", label: "Объем бака", valueType: "number", control: "range", unit: "л" },
  { key: "power_source", label: "Тип питания", valueType: "enum", control: "checkbox" },
  { key: "power_hp", label: "Мощность двигателя", valueType: "number", control: "range", unit: "л.с." },
  { key: "battery_voltage", label: "Напряжение аккумулятора", valueType: "number", control: "range", unit: "В" },
  { key: "battery_capacity", label: "Емкость аккумулятора", valueType: "number", control: "range", unit: "Ач" },
  { key: "electrical_product_type", label: "Тип электротовара", valueType: "enum", control: "checkbox" },
  { key: "cable_section", label: "Сечение кабеля", valueType: "number", control: "range", unit: "мм²" },
  { key: "cable_cores", label: "Количество жил", valueType: "number", control: "range", unit: "жил" },
  { key: "cable_length", label: "Длина", valueType: "number", control: "range", unit: "м" },
  { key: "voltage", label: "Напряжение", valueType: "number", control: "range", unit: "В" },
  { key: "current_amp", label: "Ток", valueType: "number", control: "range", unit: "А" },
  { key: "power_w", label: "Мощность", valueType: "number", control: "range", unit: "Вт" },
  { key: "ip_rating", label: "Степень защиты", valueType: "enum", control: "checkbox" },
  { key: "color", label: "Цвет", valueType: "enum", control: "checkbox" },
  { key: "processor_family", label: "Процессор", valueType: "enum", control: "checkbox" },
  { key: "processor_model", label: "Модель процессора", valueType: "enum", control: "checkbox" },
  { key: "gpu_family", label: "Видеокарта", valueType: "enum", control: "checkbox" },
  { key: "interface", label: "Интерфейс", valueType: "enum", control: "checkbox" },
] as const satisfies readonly CatalogAttributeDefinition[];

export const catalogAttributeFacetKeys = catalogAttributeDefinitions.map((definition) => definition.key);

export const catalogRangeAttributeKeys = catalogAttributeDefinitions
  .filter((definition) => definition.control === "range")
  .map((definition) => definition.key);

const catalogAttributeDefinitionByKey = new Map(catalogAttributeDefinitions.map((definition) => [definition.key, definition]));

export function getCatalogAttributeDefinition(key: string): CatalogAttributeDefinition | undefined {
  return catalogAttributeDefinitionByKey.get(key);
}
