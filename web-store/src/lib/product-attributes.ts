export type ProductAttributeSource = "name" | "manual" | "supplier" | "backfill";

export type ExtractedProductAttribute = {
  key: string;
  label: string;
  value: string;
  normalizedValue: string;
  numericValue: number | null;
  unit: string | null;
  source: ProductAttributeSource;
};

function compactNumber(value: string): string {
  return value.replace(",", ".").replace(/\.0+$/, "");
}

function numberValue(value: string): number | null {
  const parsed = Number(compactNumber(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeStorageUnit(unit: string): string {
  const lower = unit.toLocaleLowerCase("ru-RU");
  return lower === "тб" || lower === "tb" ? "ТБ" : "ГБ";
}

function extractPowerSource(text: string): { value: string; normalizedValue: string } | null {
  if (/аккумуляторн|акб|battery|cordless/i.test(text)) {
    return { value: "Аккумуляторный", normalizedValue: "battery" };
  }
  if (/бензинов/i.test(text)) {
    return { value: "Бензиновый", normalizedValue: "petrol" };
  }
  if (/дизельн/i.test(text)) {
    return { value: "Дизельный", normalizedValue: "diesel" };
  }
  if (/электрическ|сетев/i.test(text)) {
    return { value: "Электрический", normalizedValue: "electric" };
  }

  return null;
}

function addAttribute(
  attributes: ExtractedProductAttribute[],
  attribute: Omit<ExtractedProductAttribute, "source"> & { source?: ProductAttributeSource },
) {
  if (attributes.some((item) => item.key === attribute.key && item.normalizedValue === attribute.normalizedValue)) return;
  attributes.push({ ...attribute, source: attribute.source ?? "name" });
}

export function extractProductNameAttributes(name: string | null | undefined): ExtractedProductAttribute[] {
  const text = name?.trim();
  if (!text) return [];

  const attributes: ExtractedProductAttribute[] = [];

  const dailyCapacity = text.match(/(\d+(?:[.,]\d+)?)\s*л\s*\/\s*сут/i);
  if (dailyCapacity) {
    const normalized = compactNumber(dailyCapacity[1]);
    addAttribute(attributes, {
      key: "daily_capacity",
      label: "Производительность",
      value: `${normalized} л/сутки`,
      normalizedValue: normalized,
      numericValue: numberValue(normalized),
      unit: "л/сутки",
    });
  }

  const looksLikeTankProduct = /осушител|увлажнител|мойк[аи]\s+воздуха|бак|резервуар/i.test(text);
  if (looksLikeTankProduct) {
    const literMatches = Array.from(text.matchAll(/(\d+(?:[.,]\d+)?)\s*л(?!\s*\/)/gi));
    const tankMatch = literMatches.find((match) => {
      const value = numberValue(match[1]);
      return value !== null && value > 0 && value <= 30;
    });
    if (tankMatch) {
      const normalized = compactNumber(tankMatch[1]);
      addAttribute(attributes, {
        key: "tank_volume",
        label: "Объем бака",
        value: `${normalized} л`,
        normalizedValue: normalized,
        numericValue: numberValue(normalized),
        unit: "л",
      });
    }
  }

  const diagonal = text.match(/(?:^|[^\d])(\d{2,3})\s*(?:"|”|дюйм(?:ов|а)?)/i);
  if (diagonal) {
    addAttribute(attributes, {
      key: "screen_diagonal",
      label: "Диагональ",
      value: `${diagonal[1]}"`,
      normalizedValue: diagonal[1],
      numericValue: numberValue(diagonal[1]),
      unit: "дюйм",
    });
  }

  if (/\b4\s*k\b/i.test(text)) {
    addAttribute(attributes, {
      key: "resolution",
      label: "Разрешение",
      value: /uhd/i.test(text) ? "4K UHD" : "4K",
      normalizedValue: /uhd/i.test(text) ? "4k_uhd" : "4k",
      numericValue: null,
      unit: null,
    });
  } else if (/full\s*hd/i.test(text)) {
    addAttribute(attributes, {
      key: "resolution",
      label: "Разрешение",
      value: "Full HD",
      normalizedValue: "full_hd",
      numericValue: null,
      unit: null,
    });
  }

  if (/smart|смарт/i.test(text)) {
    addAttribute(attributes, {
      key: "smart_tv",
      label: "Smart TV",
      value: "Да",
      normalizedValue: "yes",
      numericValue: null,
      unit: null,
    });
  }

  const powerSource = extractPowerSource(text);
  if (powerSource) {
    addAttribute(attributes, {
      key: "power_source",
      label: "Тип питания",
      value: powerSource.value,
      normalizedValue: powerSource.normalizedValue,
      numericValue: null,
      unit: null,
    });
  }

  const powerHp = text.match(/(\d+(?:[.,]\d+)?)\s*(?:л\.?\s*с\.?|л[,;]\s*с\.?|hp|h\.?\s*p\.?)/i);
  if (powerHp) {
    const normalized = compactNumber(powerHp[1]);
    addAttribute(attributes, {
      key: "power_hp",
      label: "Мощность двигателя",
      value: `${normalized} л.с.`,
      normalizedValue: normalized,
      numericValue: numberValue(normalized),
      unit: "л.с.",
    });
  }

  const looksLikeBatteryProduct = /аккумулятор|акб|battery|cordless|батаре/i.test(text) || /(\d+(?:[.,]\d+)?)\s*(?:а\s*ч|а·ч|ah)/i.test(text);
  if (looksLikeBatteryProduct) {
    const voltage = text.match(/(\d+(?:[.,]\d+)?)\s*(?:в|v)(?=$|[\s,;])/i);
    if (voltage) {
      const normalized = compactNumber(voltage[1]);
      addAttribute(attributes, {
        key: "battery_voltage",
        label: "Напряжение аккумулятора",
        value: `${normalized} В`,
        normalizedValue: normalized,
        numericValue: numberValue(normalized),
        unit: "В",
      });
    }

    const capacity = text.match(/(\d+(?:[.,]\d+)?)\s*(?:а\s*ч|а·ч|ah)/i);
    if (capacity) {
      const normalized = compactNumber(capacity[1]);
      addAttribute(attributes, {
        key: "battery_capacity",
        label: "Емкость аккумулятора",
        value: `${normalized} Ач`,
        normalizedValue: normalized,
        numericValue: numberValue(normalized),
        unit: "Ач",
      });
    }
  }

  const ram = text.match(/(\d+)\s*(?:гб|gb)\s*(?:ram|оператив)/i) ?? text.match(/(?:ram|оператив\D{0,20})(\d+)\s*(?:гб|gb)/i);
  if (ram) {
    addAttribute(attributes, {
      key: "ram",
      label: "Оперативная память",
      value: `${ram[1]} ГБ`,
      normalizedValue: ram[1],
      numericValue: numberValue(ram[1]),
      unit: "ГБ",
    });
  }

  const storageForward = text.match(/(ssd|hdd)\s*(\d+(?:[.,]\d+)?)\s*(гб|gb|тб|tb)/i);
  const storageReverse = storageForward ? null : text.match(/(\d+(?:[.,]\d+)?)\s*(гб|gb|тб|tb)\s*(ssd|hdd)/i);
  const storage = storageForward
    ? { type: storageForward[1], capacity: storageForward[2], unit: storageForward[3] }
    : storageReverse
      ? { type: storageReverse[3], capacity: storageReverse[1], unit: storageReverse[2] }
      : null;

  if (storage) {
    const normalizedCapacity = compactNumber(storage.capacity);
    const normalizedUnit = normalizeStorageUnit(storage.unit);
    addAttribute(attributes, {
      key: "storage_type",
      label: "Тип накопителя",
      value: storage.type.toLocaleUpperCase("ru-RU"),
      normalizedValue: storage.type.toLocaleLowerCase("ru-RU"),
      numericValue: null,
      unit: null,
    });
    addAttribute(attributes, {
      key: "storage_capacity",
      label: "Объем накопителя",
      value: `${normalizedCapacity} ${normalizedUnit}`,
      normalizedValue: normalizedCapacity,
      numericValue: numberValue(normalizedCapacity),
      unit: normalizedUnit,
    });
  }

  return attributes;
}
