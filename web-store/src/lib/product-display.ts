export type ProductFact = {
  label: string;
  value: string;
};

export type ProductFactInput = {
  sku: number;
  vendor?: string | null;
  part?: string | null;
  warranty?: string | null;
  weight?: number | null;
  volume?: number | null;
  deliveryDays?: number | null;
};

export function warrantyLabel(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) return null;

  const numeric = Number(trimmed.replace(",", "."));
  if (Number.isFinite(numeric)) {
    return numeric > 0 ? `${trimmed} мес.` : null;
  }

  return trimmed;
}

function deliveryLabel(days: number | null | undefined): string | null {
  if (days === null || days === undefined) return null;
  if (days <= 0) return "день в день";

  const lastDigit = days % 10;
  const lastTwoDigits = days % 100;
  const suffix = lastDigit === 1 && lastTwoDigits !== 11 ? "день" : lastDigit >= 2 && lastDigit <= 4 && (lastTwoDigits < 12 || lastTwoDigits > 14) ? "дня" : "дней";

  return `${days} ${suffix}`;
}

function pushFact(facts: ProductFact[], label: string, value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return;
  facts.push({ label, value: String(value) });
}

export function buildProductFacts(product: ProductFactInput): ProductFact[] {
  const facts: ProductFact[] = [];

  pushFact(facts, "SKU", product.sku);
  pushFact(facts, "Бренд", product.vendor);
  pushFact(facts, "Партномер", product.part);
  pushFact(facts, "Гарантия", warrantyLabel(product.warranty));
  pushFact(facts, "Вес", product.weight ? `${product.weight} кг` : null);
  pushFact(facts, "Объем", product.volume ? `${product.volume} м³` : null);
  pushFact(facts, "Срок поставки", deliveryLabel(product.deliveryDays));

  return facts;
}

export function productDescriptionText(description: string | null | undefined): string {
  const trimmed = description?.trim();
  return trimmed || "Подробное описание пока не заполнено. Менеджер проверит характеристики, наличие и срок доставки перед подтверждением заказа.";
}
