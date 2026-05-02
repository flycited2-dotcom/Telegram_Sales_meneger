import { publicFulfillmentText } from "@/lib/fulfillment";

export type ProductFact = {
  label: string;
  value: string;
};

export type ProductFactInput = {
  sku: number;
  categoryName?: string | null;
  vendor?: string | null;
  part?: string | null;
  barcodes?: string | null;
  warranty?: string | null;
  weight?: number | null;
  volume?: number | null;
  deliveryDays?: number | null;
  multiplicity?: number | null;
};

export type ProductDescriptionInput = {
  supplierName: string;
  name?: string | null;
  categoryName?: string | null;
  vendor?: string | null;
  warranty?: string | null;
  deliveryDays?: number | null;
  multiplicity?: number | null;
};

export type ProductCardHighlightInput = Pick<ProductFactInput, "part" | "warranty" | "weight" | "volume" | "multiplicity">;

export function warrantyLabel(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) return null;

  const numeric = Number(trimmed.replace(",", "."));
  if (Number.isFinite(numeric)) {
    return numeric > 0 ? `${trimmed} мес.` : null;
  }

  return trimmed;
}

function trimNumber(value: number, fractionDigits: number): string {
  return value.toFixed(fractionDigits).replace(/\.?0+$/, "");
}

function publicDeliveryShortLabel(): string {
  return publicFulfillmentText({ isAvailable: true }).deliveryShortLabel.toLowerCase();
}

function volumeLabel(value: number | null | undefined): string | null {
  if (!value || value <= 0) return null;
  return `${trimNumber(value, value < 0.001 ? 6 : 3)} м³`;
}

function barcodesLabel(value: string | null | undefined): string | null {
  const barcodes = value
    ?.split(/[,\s;]+/)
    .map((barcode) => barcode.trim())
    .filter(Boolean);

  return barcodes?.length ? barcodes.join(", ") : null;
}

function pushFact(facts: ProductFact[], label: string, value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return;
  facts.push({ label, value: String(value) });
}

export function buildProductFacts(product: ProductFactInput): ProductFact[] {
  const facts: ProductFact[] = [];

  pushFact(facts, "SKU", product.sku);
  pushFact(facts, "Категория", product.categoryName);
  pushFact(facts, "Бренд", product.vendor);
  pushFact(facts, "Партномер", product.part);
  pushFact(facts, "Штрихкоды", barcodesLabel(product.barcodes));
  pushFact(facts, "Гарантия", warrantyLabel(product.warranty));
  pushFact(facts, "Вес", product.weight ? `${trimNumber(product.weight, 3)} кг` : null);
  pushFact(facts, "Объем упаковки", volumeLabel(product.volume));
  pushFact(facts, "Кратность заказа", product.multiplicity && product.multiplicity > 1 ? `${product.multiplicity} шт.` : null);
  pushFact(facts, "Срок поставки", publicFulfillmentText({ isAvailable: true }).deliveryShortLabel);

  return facts;
}

export function buildProductCardHighlights(product: ProductCardHighlightInput): string[] {
  const highlights = [
    warrantyLabel(product.warranty) ? `Гарантия ${warrantyLabel(product.warranty)}` : null,
    product.weight ? `${trimNumber(product.weight, 3)} кг` : null,
    product.multiplicity && product.multiplicity > 1 ? `Кратно ${product.multiplicity} шт.` : null,
    volumeLabel(product.volume),
    product.part ? `Арт. ${product.part}` : null,
  ].filter(Boolean) as string[];

  return highlights.slice(0, 3);
}

export function productDescriptionText(description: string | null | undefined, product?: ProductDescriptionInput): string {
  const trimmed = description?.trim();
  if (trimmed) return trimmed;

  if (!product) {
    return "Подробное описание пока не заполнено. Менеджер проверит характеристики, наличие и срок доставки перед подтверждением заказа.";
  }

  const name = product.name?.trim() || product.supplierName;
  const details = [
    product.vendor ? `Бренд: ${product.vendor}` : null,
    product.categoryName ? `Категория: ${product.categoryName}` : null,
    warrantyLabel(product.warranty) ? `Гарантия: ${warrantyLabel(product.warranty)}` : null,
  ].filter(Boolean);
  const orderNotes = [
    product.multiplicity && product.multiplicity > 1 ? `Заказ кратно ${product.multiplicity} шт.` : null,
    `Ориентировочный срок поставки: ${publicDeliveryShortLabel()}.`,
  ].filter(Boolean);

  return [
    `${name} доступен для заказа в интернет-магазине БытТехОпт.`,
    details.length ? `${details.join(". ")}.` : null,
    orderNotes.join(" "),
    "Менеджер подтвердит актуальную цену, наличие и срок доставки перед оформлением заказа.",
  ]
    .filter(Boolean)
    .join(" ");
}
