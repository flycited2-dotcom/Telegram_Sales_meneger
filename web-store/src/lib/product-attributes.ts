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

function normalizeToken(value: string): string {
  return value
    .toLocaleLowerCase("ru-RU")
    .replace(/ё/g, "е")
    .replace(/[^a-zа-я0-9]+/gi, "_")
    .replace(/^_+|_+$/g, "");
}

function cableCoreUnit(value: number): string {
  const lastDigit = value % 10;
  const lastTwoDigits = value % 100;
  if (lastDigit === 1 && lastTwoDigits !== 11) return "жила";
  if (lastDigit >= 2 && lastDigit <= 4 && (lastTwoDigits < 12 || lastTwoDigits > 14)) return "жилы";
  return "жил";
}

function looksLikeLaundryProduct(text: string): boolean {
  return /сушильн|стиральн|washer|washing machine|dryer/i.test(text);
}

function looksLikeEngineProduct(text: string): boolean {
  return /двигател|снегоубор|мотоблок|газонокос|генератор|культиватор|триммер|бензопил|мотопомп/i.test(text);
}

function extractElectricalProductType(text: string): { value: string; normalizedValue: string } | null {
  if (/кабел|провод|шнур|\bcable\b|\bwire\b|\bcord\b/i.test(text)) {
    return { value: "Кабель", normalizedValue: "cable" };
  }
  if (/розетк|\bsocket\b|\boutlet\b/i.test(text)) {
    return { value: "Розетка", normalizedValue: "socket" };
  }
  if (/выключател|\bswitch\b/i.test(text)) {
    return { value: "Выключатель", normalizedValue: "switch" };
  }
  if (/дифавтомат|автоматическ\D{0,12}выключател|узо|\bbreaker\b/i.test(text)) {
    return { value: "Автомат", normalizedValue: "breaker" };
  }
  if (/светильник|ламп|\blamp\b/i.test(text)) {
    return { value: "Светильник", normalizedValue: "lamp" };
  }
  if (/разъ[её]м|коннектор|клемм|\bconnector\b/i.test(text)) {
    return { value: "Коннектор", normalizedValue: "connector" };
  }
  if (/коробк|бокс|\bbox\b|(^|[^а-яё])щит(ок)?(?=$|[^а-яё])/i.test(text)) {
    return { value: "Коробка/щит", normalizedValue: "box" };
  }

  return null;
}

function extractColor(text: string): { value: string; normalizedValue: string } | null {
  const colors: Array<{ pattern: RegExp; value: string; normalizedValue: string }> = [
    { pattern: /бел(ый|ая|ое|ые)|\bwhite\b/i, value: "Белый", normalizedValue: "white" },
    { pattern: /ч[её]рн(ый|ая|ое|ые)|\bblack\b/i, value: "Черный", normalizedValue: "black" },
    { pattern: /сер(ый|ая|ое|ые)|\bgr[ae]y\b/i, value: "Серый", normalizedValue: "gray" },
    { pattern: /красн(ый|ая|ое|ые)|\bred\b/i, value: "Красный", normalizedValue: "red" },
    { pattern: /син(ий|яя|ее|ие)|\bblue\b/i, value: "Синий", normalizedValue: "blue" },
    { pattern: /зел[её]н(ый|ая|ое|ые)|\bgreen\b/i, value: "Зеленый", normalizedValue: "green" },
    { pattern: /бежев(ый|ая|ое|ые)|\bbeige\b/i, value: "Бежевый", normalizedValue: "beige" },
  ];

  return colors.find((color) => color.pattern.test(text)) ?? null;
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

function addNumberAttribute(
  attributes: ExtractedProductAttribute[],
  key: string,
  label: string,
  rawValue: string,
  unit: string,
) {
  const normalized = compactNumber(rawValue);
  addAttribute(attributes, {
    key,
    label,
    value: `${normalized} ${unit}`,
    normalizedValue: normalized,
    numericValue: numberValue(normalized),
    unit,
  });
}

function extractLaundryAttributes(text: string, attributes: ExtractedProductAttribute[]) {
  if (!looksLikeLaundryProduct(text)) return;

  const load = text.match(/(?:макс\.?\s*загр\.?\s*:?\s*)?(\d+(?:[.,]\d+)?)\s*кг/i);
  if (load) {
    addNumberAttribute(attributes, "load_capacity", "Загрузка", load[1], "кг");
  }

  if (/теплов(ой|ым)\s+насос|heat\s*pump/i.test(text)) {
    addAttribute(attributes, {
      key: "drying_type",
      label: "Тип сушки",
      value: "Тепловой насос",
      normalizedValue: "heat_pump",
      numericValue: null,
      unit: null,
    });
  } else if (/конденсацион/i.test(text)) {
    addAttribute(attributes, {
      key: "drying_type",
      label: "Тип сушки",
      value: "Конденсационная",
      normalizedValue: "condensation",
      numericValue: null,
      unit: null,
    });
  } else if (/вентиляцион/i.test(text)) {
    addAttribute(attributes, {
      key: "drying_type",
      label: "Тип сушки",
      value: "Вентиляционная",
      normalizedValue: "vented",
      numericValue: null,
      unit: null,
    });
  }

  if (/отдельностоящ/i.test(text)) {
    addAttribute(attributes, {
      key: "installation_type",
      label: "Установка",
      value: "Отдельностоящая",
      normalizedValue: "freestanding",
      numericValue: null,
      unit: null,
    });
  } else if (/встраиваем/i.test(text)) {
    addAttribute(attributes, {
      key: "installation_type",
      label: "Установка",
      value: "Встраиваемая",
      normalizedValue: "built_in",
      numericValue: null,
      unit: null,
    });
  }

  if (/inverter|инвертор/i.test(text)) {
    addAttribute(attributes, {
      key: "inverter_motor",
      label: "Инверторный двигатель",
      value: "Да",
      normalizedValue: "yes",
      numericValue: null,
      unit: null,
    });
  }

  const programs = text.match(/программ\D{0,8}(\d{1,2})/i) ?? text.match(/(\d{1,2})\s*программ/i);
  if (programs) {
    addNumberAttribute(attributes, "program_count", "Количество программ", programs[1], "программ");
  }

  const spinSpeed = text.match(/(\d{3,4})\s*(?:об\s*\/\s*мин|об\.?\s*мин)/i);
  if (spinSpeed) {
    addNumberAttribute(attributes, "spin_speed", "Скорость отжима", spinSpeed[1], "об/мин");
  }

  const dimensions = text.match(/(\d+(?:[.,]\d+)?)\s*[xх]\s*(\d+(?:[.,]\d+)?)\s*[xх]\s*(\d+(?:[.,]\d+)?)\s*см/i);
  if (dimensions) {
    addNumberAttribute(attributes, "width_cm", "Ширина", dimensions[1], "см");
    addNumberAttribute(attributes, "height_cm", "Высота", dimensions[2], "см");
    addNumberAttribute(attributes, "depth_cm", "Глубина", dimensions[3], "см");
  } else {
    const depth = text.match(/глубин[аы]?\s*(\d+(?:[.,]\d+)?)\s*см/i);
    if (depth) {
      addNumberAttribute(attributes, "depth_cm", "Глубина", depth[1], "см");
    }
  }

  const energy = text.match(/(?:кл\.?\s*энер\.?|энергоэффективность|класс энергопотребления)\s*:?\s*([aа][+]{0,3}|[bcdefgвсдефг])/i);
  if (energy) {
    const value = energy[1].toLocaleUpperCase("ru-RU").replace(/^А/, "A");
    addAttribute(attributes, {
      key: "energy_class",
      label: "Класс энергопотребления",
      value,
      normalizedValue: normalizeToken(value),
      numericValue: null,
      unit: null,
    });
  }
}

export function extractProductNameAttributes(name: string | null | undefined): ExtractedProductAttribute[] {
  const text = name?.trim();
  if (!text) return [];

  const attributes: ExtractedProductAttribute[] = [];

  const dailyCapacity = text.match(/(\d+(?:[.,]\d+)?)\s*л\s*\/\s*сут/i);
  if (dailyCapacity) {
    addNumberAttribute(attributes, "daily_capacity", "Производительность", dailyCapacity[1], "л/сутки");
  }

  const looksLikeTankProduct = /осушител|увлажнител|мойк[аи]\s+воздуха|бак|резервуар/i.test(text);
  if (looksLikeTankProduct) {
    const literMatches = Array.from(text.matchAll(/(\d+(?:[.,]\d+)?)\s*л(?!\s*\/)/gi));
    const tankMatch = literMatches.find((match) => {
      const value = numberValue(match[1]);
      return value !== null && value > 0 && value <= 30;
    });
    if (tankMatch) {
      addNumberAttribute(attributes, "tank_volume", "Объем бака", tankMatch[1], "л");
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

  extractLaundryAttributes(text, attributes);

  const electricalProductType = extractElectricalProductType(text);
  if (electricalProductType) {
    addAttribute(attributes, {
      key: "electrical_product_type",
      label: "Тип электротовара",
      value: electricalProductType.value,
      normalizedValue: electricalProductType.normalizedValue,
      numericValue: null,
      unit: null,
    });

    if (electricalProductType.normalizedValue === "cable") {
      const cableSize = text.match(/(\d+)\s*[xх]\s*(\d+(?:[.,]\d+)?)/i);
      if (cableSize) {
        const cores = Number(cableSize[1]);
        const section = compactNumber(cableSize[2]);
        if (Number.isFinite(cores) && cores > 0) {
          addAttribute(attributes, {
            key: "cable_cores",
            label: "Количество жил",
            value: `${cores} ${cableCoreUnit(cores)}`,
            normalizedValue: String(cores),
            numericValue: cores,
            unit: "жил",
          });
        }
        addNumberAttribute(attributes, "cable_section", "Сечение кабеля", section, "мм²");
      }

      const cableLength = text.match(/(\d+(?:[.,]\d+)?)\s*м(?=$|[\s,;.])/i);
      if (cableLength) {
        addNumberAttribute(attributes, "cable_length", "Длина", cableLength[1], "м");
      }
    }

    const voltage = text.match(/(\d+(?:[.,]\d+)?)\s*(?:в|v)(?=$|[\s,;])/i);
    if (voltage) {
      addNumberAttribute(attributes, "voltage", "Напряжение", voltage[1], "В");
    }

    const current = text.match(/(\d+(?:[.,]\d+)?)\s*(?:а(?!\s*ч)|a(?!h))(?=$|[\s,;])/i);
    if (current) {
      addNumberAttribute(attributes, "current_amp", "Сила тока", current[1], "А");
    }

    const power = text.match(/(\d+(?:[.,]\d+)?)\s*(квт|kw|вт|w)\b/i);
    if (power) {
      const sourceValue = numberValue(power[1]);
      const unit = power[2].toLocaleLowerCase("ru-RU");
      const numericWatts = sourceValue === null ? null : unit === "квт" || unit === "kw" ? sourceValue * 1000 : sourceValue;
      const displayUnit = unit === "квт" || unit === "kw" ? "кВт" : "Вт";
      const displayValue = compactNumber(power[1]);
      addAttribute(attributes, {
        key: "power_w",
        label: "Мощность",
        value: `${displayValue} ${displayUnit}`,
        normalizedValue: numericWatts === null ? displayValue : compactNumber(String(numericWatts)),
        numericValue: numericWatts,
        unit: "Вт",
      });
    }

    const ipRating = text.match(/\bIP\s?(\d{2})\b/i);
    if (ipRating) {
      addAttribute(attributes, {
        key: "ip_rating",
        label: "Степень защиты",
        value: `IP${ipRating[1]}`,
        normalizedValue: `ip${ipRating[1]}`,
        numericValue: null,
        unit: null,
      });
    }
  }

  const color = extractColor(text);
  if (color) {
    addAttribute(attributes, {
      key: "color",
      label: "Цвет",
      value: color.value,
      normalizedValue: color.normalizedValue,
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

  const powerHp =
    text.match(/(\d+(?:[.,]\d+)?)\s*(?:л\.?\s*с\.?|л[,;]\s*с\.?)/i) ??
    (looksLikeEngineProduct(text) ? text.match(/(\d+(?:[.,]\d+)?)\s*(?:hp\b|h\.?\s*p\.?\b)/i) : null);
  if (powerHp) {
    addNumberAttribute(attributes, "power_hp", "Мощность двигателя", powerHp[1], "л.с.");
  }

  const looksLikeBatteryProduct = /аккумулятор|акб|battery|cordless|батаре/i.test(text) || /(\d+(?:[.,]\d+)?)\s*(?:а\s*ч|а·ч|ah)/i.test(text);
  if (looksLikeBatteryProduct) {
    const voltage = text.match(/(\d+(?:[.,]\d+)?)\s*(?:в|v)(?=$|[\s,;])/i);
    if (voltage) {
      addNumberAttribute(attributes, "battery_voltage", "Напряжение аккумулятора", voltage[1], "В");
    }

    const capacity = text.match(/(\d+(?:[.,]\d+)?)\s*(?:а\s*ч|а·ч|ah)/i);
    if (capacity) {
      addNumberAttribute(attributes, "battery_capacity", "Емкость аккумулятора", capacity[1], "Ач");
    }
  }

  const ram = text.match(/(\d+)\s*(?:гб|gb)\s*(?:ram|оператив)/i) ?? text.match(/(?:ram|оператив\D{0,20})(\d+)\s*(?:гб|gb)/i);
  if (ram) {
    addNumberAttribute(attributes, "ram", "Оперативная память", ram[1], "ГБ");
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

  const intelProcessor = text.match(/\bintel\s+core\s+(i[3579])(?:[-\s]+([a-z0-9][a-z0-9-]*))?/i);
  if (intelProcessor) {
    const family = `Intel Core ${intelProcessor[1].toLocaleLowerCase("ru-RU")}`;
    addAttribute(attributes, {
      key: "processor_family",
      label: "Процессор",
      value: family,
      normalizedValue: normalizeToken(family),
      numericValue: null,
      unit: null,
    });
    if (intelProcessor[2]) {
      const model = `${family}-${intelProcessor[2].toLocaleUpperCase("ru-RU")}`;
      addAttribute(attributes, {
        key: "processor_model",
        label: "Модель процессора",
        value: model,
        normalizedValue: normalizeToken(model),
        numericValue: null,
        unit: null,
      });
    }
  }

  const amdProcessor = text.match(/\bamd\s+ryzen\s+([3579])(?:[-\s]+([a-z0-9][a-z0-9-]*))?/i);
  if (amdProcessor) {
    const family = `AMD Ryzen ${amdProcessor[1]}`;
    addAttribute(attributes, {
      key: "processor_family",
      label: "Процессор",
      value: family,
      normalizedValue: normalizeToken(family),
      numericValue: null,
      unit: null,
    });
    if (amdProcessor[2]) {
      const model = `${family}-${amdProcessor[2].toLocaleUpperCase("ru-RU")}`;
      addAttribute(attributes, {
        key: "processor_model",
        label: "Модель процессора",
        value: model,
        normalizedValue: normalizeToken(model),
        numericValue: null,
        unit: null,
      });
    }
  }

  const interfaces: Array<{ pattern: RegExp; value: string; normalizedValue: string }> = [
    { pattern: /\bhdmi\b/i, value: "HDMI", normalizedValue: "hdmi" },
    { pattern: /\busb\b/i, value: "USB", normalizedValue: "usb" },
    { pattern: /\brj\s*[- ]?\s*45\b/i, value: "RJ-45", normalizedValue: "rj_45" },
    { pattern: /\bwi[\s-]?fi\b|вай\s?фай/i, value: "Wi-Fi", normalizedValue: "wi_fi" },
    { pattern: /\bbluetooth\b|блютуз/i, value: "Bluetooth", normalizedValue: "bluetooth" },
  ];
  for (const item of interfaces) {
    if (!item.pattern.test(text)) continue;
    addAttribute(attributes, {
      key: "interface",
      label: "Интерфейс",
      value: item.value,
      normalizedValue: item.normalizedValue,
      numericValue: null,
      unit: null,
    });
  }

  return attributes;
}
