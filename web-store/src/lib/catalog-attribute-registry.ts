export type CatalogAttributeValueType = "enum" | "number" | "boolean" | "text";
export type CatalogAttributeControl = "checkbox" | "range" | "boolean";
export type CatalogAttributeFamily =
  | "universal"
  | "computer"
  | "tv"
  | "climate"
  | "garden"
  | "electrical"
  | "laundry"
  | "refrigeration"
  | "camera"
  | "paper";

export type CatalogAttributeDefinition = {
  key: string;
  label: string;
  valueType: CatalogAttributeValueType;
  control: CatalogAttributeControl;
  unit?: string;
  families?: CatalogAttributeFamily[];
};

export const catalogAttributeDefinitions = [
  { key: "storage_type", label: "Тип накопителя", valueType: "enum", control: "checkbox", families: ["computer"] },
  { key: "storage_capacity", label: "Объем накопителя", valueType: "number", control: "range", unit: "ГБ", families: ["computer"] },
  { key: "ram", label: "Оперативная память", valueType: "number", control: "range", unit: "ГБ", families: ["computer"] },
  { key: "screen_diagonal", label: "Диагональ", valueType: "number", control: "range", unit: "дюйм", families: ["tv", "computer"] },
  { key: "resolution", label: "Разрешение", valueType: "enum", control: "checkbox", families: ["tv", "computer", "camera"] },
  { key: "smart_tv", label: "Smart TV", valueType: "boolean", control: "checkbox", families: ["tv"] },
  { key: "daily_capacity", label: "Производительность", valueType: "number", control: "range", unit: "л/сутки", families: ["climate"] },
  { key: "tank_volume", label: "Объем бака", valueType: "number", control: "range", unit: "л", families: ["climate"] },
  { key: "load_capacity", label: "Загрузка", valueType: "number", control: "range", unit: "кг", families: ["laundry"] },
  { key: "drying_type", label: "Тип сушки", valueType: "enum", control: "checkbox", families: ["laundry"] },
  { key: "installation_type", label: "Установка", valueType: "enum", control: "checkbox", families: ["laundry", "refrigeration"] },
  { key: "inverter_motor", label: "Инверторный двигатель", valueType: "boolean", control: "checkbox", families: ["laundry", "refrigeration"] },
  { key: "program_count", label: "Количество программ", valueType: "number", control: "range", unit: "программ", families: ["laundry"] },
  { key: "spin_speed", label: "Скорость отжима", valueType: "number", control: "range", unit: "об/мин", families: ["laundry"] },
  { key: "width_cm", label: "Ширина", valueType: "number", control: "range", unit: "см", families: ["laundry", "refrigeration"] },
  { key: "height_cm", label: "Высота", valueType: "number", control: "range", unit: "см", families: ["laundry", "refrigeration"] },
  { key: "depth_cm", label: "Глубина", valueType: "number", control: "range", unit: "см", families: ["laundry", "refrigeration"] },
  { key: "energy_class", label: "Класс энергопотребления", valueType: "enum", control: "checkbox", families: ["laundry", "refrigeration"] },
  { key: "power_source", label: "Тип питания", valueType: "enum", control: "checkbox", families: ["garden"] },
  { key: "power_hp", label: "Мощность двигателя", valueType: "number", control: "range", unit: "л.с.", families: ["garden"] },
  { key: "battery_voltage", label: "Напряжение аккумулятора", valueType: "number", control: "range", unit: "В", families: ["garden"] },
  { key: "battery_capacity", label: "Емкость аккумулятора", valueType: "number", control: "range", unit: "Ач", families: ["garden"] },
  { key: "electrical_product_type", label: "Тип электротовара", valueType: "enum", control: "checkbox", families: ["electrical"] },
  { key: "cable_section", label: "Сечение кабеля", valueType: "number", control: "range", unit: "мм²", families: ["electrical"] },
  { key: "cable_cores", label: "Количество жил", valueType: "number", control: "range", unit: "жил", families: ["electrical"] },
  { key: "cable_length", label: "Длина", valueType: "number", control: "range", unit: "м", families: ["electrical"] },
  { key: "voltage", label: "Напряжение", valueType: "number", control: "range", unit: "В", families: ["electrical", "garden", "climate"] },
  { key: "current_amp", label: "Ток", valueType: "number", control: "range", unit: "А", families: ["electrical"] },
  { key: "power_w", label: "Мощность", valueType: "number", control: "range", unit: "Вт", families: ["electrical", "garden", "climate"] },
  { key: "ip_rating", label: "Степень защиты", valueType: "enum", control: "checkbox", families: ["electrical", "garden", "camera"] },
  { key: "color", label: "Цвет", valueType: "enum", control: "checkbox", families: ["universal"] },
  { key: "processor_family", label: "Процессор", valueType: "enum", control: "checkbox", families: ["computer"] },
  { key: "processor_model", label: "Модель процессора", valueType: "enum", control: "checkbox", families: ["computer"] },
  { key: "gpu_family", label: "Видеокарта", valueType: "enum", control: "checkbox", families: ["computer"] },
  { key: "interface", label: "Интерфейс", valueType: "enum", control: "checkbox", families: ["computer", "camera"] },
] as const satisfies readonly CatalogAttributeDefinition[];

export const catalogAttributeFacetKeys: string[] = catalogAttributeDefinitions.map((definition) => definition.key);

export const catalogRangeAttributeKeys: string[] = catalogAttributeDefinitions
  .filter((definition) => definition.control === "range")
  .map((definition) => definition.key);

const catalogAttributeDefinitionByKey = new Map<string, CatalogAttributeDefinition>(catalogAttributeDefinitions.map((definition) => [definition.key, definition]));

export function getCatalogAttributeDefinition(key: string): CatalogAttributeDefinition | undefined {
  return catalogAttributeDefinitionByKey.get(key);
}

function normalizeCategoryScope(value: string | null | undefined): string {
  return (value ?? "").toLocaleLowerCase("ru-RU").replace(/ё/g, "е");
}

export function getCatalogAttributeFamilyForCategory({
  categoryName,
  categorySlug,
}: {
  categoryName?: string | null;
  categorySlug?: string | null;
}): CatalogAttributeFamily | null {
  const text = `${normalizeCategoryScope(categoryName)} ${normalizeCategoryScope(categorySlug)}`;
  if (!text.trim()) return null;

  if (/сушильн|стиральн|washer|washing|dryer|laundry/.test(text)) return "laundry";
  if (/холодильн|морозильн|refrigerator|fridge|freezer/.test(text)) return "refrigeration";
  if (/телевиз|tv|televiz/.test(text)) return "tv";
  if (/компьютер|ноутбук|планшет|монитор|процессор|laptop|computer|notebook|monitor/.test(text)) return "computer";
  if (/кабел|провод|электр|розетк|выключател|светильник|ламп|щит|cable|wire|electric/.test(text)) return "electrical";
  if (/сад|огород|снегоубор|газон|мотоблок|триммер|культиватор|dacha|sad|ogorod|garden/.test(text)) return "garden";
  if (/кондиционер|сплит|осушител|увлажнител|очистител|климат|climat|conditioner|humidifier|dehumidifier/.test(text)) return "climate";
  if (/камер|фотоаппарат|объектив|camera|video/.test(text)) return "camera";
  if (/бумаг|картон|канцеляр|paper|cardboard/.test(text)) return "paper";

  return null;
}

export function getCatalogAttributeKeysForCategory({
  categoryName,
  categorySlug,
}: {
  categoryName?: string | null;
  categorySlug?: string | null;
}): string[] {
  const family = getCatalogAttributeFamilyForCategory({ categoryName, categorySlug });
  if (!family) return catalogAttributeFacetKeys;

  return catalogAttributeDefinitions
    .filter((definition) => {
      const families: readonly CatalogAttributeFamily[] = definition.families ?? ["universal"];
      return families.includes("universal") || families.includes(family);
    })
    .map((definition) => definition.key);
}
