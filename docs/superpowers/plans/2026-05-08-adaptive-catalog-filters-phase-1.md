# Adaptive Catalog Filters Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first architecture layer for adaptive catalog filters: a typed attribute registry, numeric range filters, and reliable extractors for electrical/SCS and computer goods.

**Architecture:** Keep the existing `ProductAttribute` table and `attr=key:value` exact filters. Add a small registry that defines which attributes are filterable and how they should render, then add `attrMin=key:value` / `attrMax=key:value` numeric range filters. Product enrichment remains deterministic through tested extractors and `npm run sync:attributes`.

**Tech Stack:** Next.js 16 app router, React 19, Prisma 6, Vitest, TypeScript, existing `web-store` catalog modules.

---

## File Map

- Create `web-store/src/lib/catalog-attribute-registry.ts`: single registry for filterable attributes, order, UI control type, and range keys.
- Create `web-store/src/lib/catalog-attribute-registry.test.ts`: registry tests.
- Modify `web-store/src/lib/catalog-attribute-filters.ts`: use the registry, parse exact and range filters, build Prisma `where`, build range group metadata.
- Modify `web-store/src/lib/catalog-attribute-filters.test.ts`: exact filters, range filters, range groups.
- Modify `web-store/src/lib/catalog-query.ts`: parse `attrMin` and `attrMax`.
- Modify `web-store/src/lib/catalog-query.test.ts`: URL parsing tests.
- Modify `web-store/src/lib/catalog-ui.ts` and `web-store/src/lib/catalog-ui.test.ts`: active filter count includes numeric ranges.
- Modify `web-store/src/lib/catalog.ts`: apply range filters and return range groups.
- Modify `web-store/src/app/catalog/catalog-view.tsx`: render numeric ranges in desktop and mobile filter panels, preserve them in links/forms/chips/sort.
- Modify catalog route pages in `web-store/src/app/catalog/page.tsx`, `web-store/src/app/catalog/[slug]/page.tsx`, `web-store/src/app/search/page.tsx`: pass range filters to catalog data and view.
- Modify `web-store/src/lib/product-attributes.ts`: add electrical/SCS and computer extractors.
- Modify `web-store/src/lib/product-attributes.test.ts`: extractor tests.
- Modify `web-store/src/lib/product-name-specs.ts` and `web-store/src/lib/product-name-specs.test.ts`: card highlights for the most useful new attributes.
- Modify `web-store/HANDOFF.md`: deployment and smoke notes.

## Task 1: Attribute Registry

**Files:**
- Create: `web-store/src/lib/catalog-attribute-registry.ts`
- Create: `web-store/src/lib/catalog-attribute-registry.test.ts`
- Modify: `web-store/src/lib/catalog-attribute-filters.ts`

- [ ] **Step 1: Write the failing registry test**

Add `web-store/src/lib/catalog-attribute-registry.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  catalogAttributeFacetKeys,
  catalogRangeAttributeKeys,
  getCatalogAttributeDefinition,
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
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
npm.cmd test -- src/lib/catalog-attribute-registry.test.ts
```

Expected: fail because `catalog-attribute-registry.ts` does not exist.

- [ ] **Step 3: Implement the registry**

Create `web-store/src/lib/catalog-attribute-registry.ts`:

```ts
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
```

- [ ] **Step 4: Wire the registry into existing filters**

Modify `web-store/src/lib/catalog-attribute-filters.ts`:

```ts
import {
  catalogAttributeFacetKeys,
  getCatalogAttributeDefinition,
} from "@/lib/catalog-attribute-registry";
```

Remove the local `attributeKeyOrder` array. Build `keyRank` from imported `catalogAttributeFacetKeys`:

```ts
const keyRank = new Map(catalogAttributeFacetKeys.map((key, index) => [key, index]));
```

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm.cmd test -- src/lib/catalog-attribute-registry.test.ts src/lib/catalog-attribute-filters.test.ts
```

Expected: pass.

Commit:

```powershell
git add -- web-store/src/lib/catalog-attribute-registry.ts web-store/src/lib/catalog-attribute-registry.test.ts web-store/src/lib/catalog-attribute-filters.ts
git commit -m "Add catalog attribute registry"
```

## Task 2: Numeric Range URL Parsing and Prisma Where

**Files:**
- Modify: `web-store/src/lib/catalog-attribute-filters.ts`
- Modify: `web-store/src/lib/catalog-attribute-filters.test.ts`
- Modify: `web-store/src/lib/catalog-query.ts`
- Modify: `web-store/src/lib/catalog-query.test.ts`
- Modify: `web-store/src/lib/catalog-ui.ts`
- Modify: `web-store/src/lib/catalog-ui.test.ts`

- [ ] **Step 1: Write failing tests for range filters**

Add tests to `web-store/src/lib/catalog-attribute-filters.test.ts`:

```ts
import {
  buildCatalogAttributeRangeFilterWhere,
  normalizeCatalogAttributeRangeFilters,
} from "@/lib/catalog-attribute-filters";

it("normalizes numeric min/max URL filters", () => {
  expect(
    normalizeCatalogAttributeRangeFilters({
      minValues: ["ram:16", "bad", "storage_capacity:512"],
      maxValues: ["ram:64", "screen_diagonal:65", "unknown:1"],
    }),
  ).toEqual([
    { key: "ram", min: 16, max: 64 },
    { key: "storage_capacity", min: 512 },
    { key: "screen_diagonal", max: 65 },
  ]);
});

it("builds Prisma numeric attribute range filters", () => {
  expect(buildCatalogAttributeRangeFilterWhere([{ key: "ram", min: 16, max: 64 }])).toEqual({
    AND: [
      {
        attributes: {
          some: {
            key: "ram",
            numericValue: {
              gte: 16,
              lte: 64,
            },
          },
        },
      },
    ],
  });
});
```

Add to `web-store/src/lib/catalog-query.test.ts` expected parsed ranges:

```ts
attrMin: ["ram:16", "storage_capacity:512"],
attrMax: ["ram:64"],
```

Expected `attributeRangeFilters`:

```ts
[
  { key: "ram", min: 16, max: 64 },
  { key: "storage_capacity", min: 512 },
]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
npm.cmd test -- src/lib/catalog-attribute-filters.test.ts src/lib/catalog-query.test.ts src/lib/catalog-ui.test.ts
```

Expected: fail because range types/functions are missing.

- [ ] **Step 3: Implement range types and parsing**

In `web-store/src/lib/catalog-attribute-filters.ts`, add:

```ts
import { catalogRangeAttributeKeys } from "@/lib/catalog-attribute-registry";

export type CatalogAttributeRangeFilter = {
  key: string;
  min?: number;
  max?: number;
};

function parseRangeParam(value: string | null | undefined): { key: string; value: number } | null {
  const raw = value?.trim();
  if (!raw || !raw.includes(":")) return null;

  const [key, ...rest] = raw.split(":");
  const normalizedKey = key.trim();
  const numberValue = Number(rest.join(":").trim().replace(",", "."));
  if (!catalogRangeAttributeKeys.includes(normalizedKey) || !Number.isFinite(numberValue) || numberValue < 0) {
    return null;
  }

  return { key: normalizedKey, value: numberValue };
}

export function normalizeCatalogAttributeRangeFilters({
  minValues,
  maxValues,
}: {
  minValues: Array<string | null | undefined>;
  maxValues: Array<string | null | undefined>;
}): CatalogAttributeRangeFilter[] {
  const byKey = new Map<string, CatalogAttributeRangeFilter>();

  for (const value of minValues) {
    const parsed = parseRangeParam(value);
    if (parsed) byKey.set(parsed.key, { ...byKey.get(parsed.key), key: parsed.key, min: parsed.value });
  }

  for (const value of maxValues) {
    const parsed = parseRangeParam(value);
    if (parsed) byKey.set(parsed.key, { ...byKey.get(parsed.key), key: parsed.key, max: parsed.value });
  }

  return Array.from(byKey.values())
    .filter((filter) => filter.min !== undefined || filter.max !== undefined)
    .slice(0, 16);
}

export function buildCatalogAttributeRangeFilterWhere(filters: CatalogAttributeRangeFilter[]): Prisma.ProductWhereInput {
  if (!filters.length) return {};

  return {
    AND: filters.map((filter) => ({
      attributes: {
        some: {
          key: filter.key,
          numericValue: {
            ...(filter.min !== undefined ? { gte: filter.min } : {}),
            ...(filter.max !== undefined ? { lte: filter.max } : {}),
          },
        },
      },
    })),
  };
}
```

- [ ] **Step 4: Parse range params in catalog query**

Modify `web-store/src/lib/catalog-query.ts`:

```ts
import {
  normalizeCatalogAttributeFilters,
  normalizeCatalogAttributeRangeFilters,
  type CatalogAttributeFilter,
  type CatalogAttributeRangeFilter,
} from "@/lib/catalog-attribute-filters";
```

Add to `ParsedCatalogSearchParams`:

```ts
attributeRangeFilters: CatalogAttributeRangeFilter[];
```

Add in `parseCatalogSearchParams`:

```ts
attributeRangeFilters: normalizeCatalogAttributeRangeFilters({
  minValues: allParams(params.attrMin),
  maxValues: allParams(params.attrMax),
}),
```

- [ ] **Step 5: Count active range filters**

Modify `web-store/src/lib/catalog-ui.ts` input type to include:

```ts
attributeRangeFilters?: unknown[];
```

Add to the count:

```ts
(input.attributeRangeFilters?.length ?? 0)
```

- [ ] **Step 6: Verify and commit**

Run:

```powershell
npm.cmd test -- src/lib/catalog-attribute-filters.test.ts src/lib/catalog-query.test.ts src/lib/catalog-ui.test.ts
```

Expected: pass.

Commit:

```powershell
git add -- web-store/src/lib/catalog-attribute-filters.ts web-store/src/lib/catalog-attribute-filters.test.ts web-store/src/lib/catalog-query.ts web-store/src/lib/catalog-query.test.ts web-store/src/lib/catalog-ui.ts web-store/src/lib/catalog-ui.test.ts
git commit -m "Add numeric attribute range filters"
```

## Task 3: Catalog Data Flow and Desktop/Mobile Range UI

**Files:**
- Modify: `web-store/src/lib/catalog.ts`
- Modify: `web-store/src/app/catalog/catalog-view.tsx`
- Modify: `web-store/src/app/catalog/page.tsx`
- Modify: `web-store/src/app/catalog/[slug]/page.tsx`
- Modify: `web-store/src/app/search/page.tsx`

- [ ] **Step 1: Add range group metadata to `catalog-attribute-filters.ts` tests**

Add a test that builds range groups from aggregate rows:

```ts
expect(
  buildCatalogAttributeRangeGroups([
    { key: "ram", label: "Оперативная память", min: 8, max: 64, unit: "ГБ", count: 25 },
    { key: "power_hp", label: "Мощность двигателя", min: 5, max: 18, unit: "л.с.", count: 10 },
  ]),
).toEqual([
  { key: "ram", label: "Оперативная память", min: 8, max: 64, unit: "ГБ", count: 25 },
  { key: "power_hp", label: "Мощность двигателя", min: 5, max: 18, unit: "л.с.", count: 10 },
]);
```

- [ ] **Step 2: Implement range group helper**

Add:

```ts
export type CatalogAttributeRangeGroup = {
  key: string;
  label: string;
  min: number;
  max: number;
  unit: string | null;
  count: number;
};
```

and:

```ts
export function buildCatalogAttributeRangeGroups(rows: CatalogAttributeRangeGroup[]): CatalogAttributeRangeGroup[] {
  return rows
    .filter((row) => row.count > 0 && Number.isFinite(row.min) && Number.isFinite(row.max) && row.min < row.max)
    .sort((left, right) => (keyRank.get(left.key) ?? 999) - (keyRank.get(right.key) ?? 999));
}
```

- [ ] **Step 3: Apply range filters in catalog data**

In `web-store/src/lib/catalog.ts`:

- add `attributeRangeFilters?: CatalogAttributeRangeFilter[]` to `CatalogQuery`;
- import `buildCatalogAttributeRangeFilterWhere`, `buildCatalogAttributeRangeGroups`, `catalogRangeAttributeKeys`;
- append `attributeRangeAnd` to final `filteredWhere`;
- append `attributeRangeAnd` to `specCountBaseWhere`, `brandWhere`, and the final `filteredWhere`;
- add `getCatalogAttributeRangeGroups(baseWhere)` using sequential Prisma `aggregate` per range key:

```ts
const aggregate = await prisma.productAttribute.aggregate({
  where: {
    key,
    numericValue: { not: null },
    product: { is: baseWhere },
  },
  _min: { numericValue: true },
  _max: { numericValue: true },
  _count: { _all: true },
});
```

Return `attributeRangeGroups` from `getCatalogPage`.

- [ ] **Step 4: Render range controls in desktop and mobile**

In `web-store/src/app/catalog/catalog-view.tsx`:

- extend `CatalogUrlState` with `attributeRangeFilters`;
- preserve `attrMin` and `attrMax` in `catalogHref`;
- preserve range filters in sort form hidden inputs;
- pass `attributeRangeGroups` and `currentAttributeRangeFilters` to `FiltersPanel`;
- render each group as two inputs:

```tsx
<input name="attrMin" value={`${group.key}:${current?.min ?? ""}`} ... />
<input name="attrMax" value={`${group.key}:${current?.max ?? ""}`} ... />
```

Implementation detail: because empty `key:` values are discarded by parser, inputs can submit `ram:` safely, but prefer only setting `name` when value is present by using separate visible inputs plus hidden composition only if needed. If that is too much for this task, use direct inputs and rely on parser discarding invalid values.

- [ ] **Step 5: Add range chips**

In `ActiveFilterChips`, add chips like:

```ts
label: `${group.label}: от ${filter.min} ${group.unit ?? ""}`
label: `${group.label}: до ${filter.max} ${group.unit ?? ""}`
```

Each chip removes only the corresponding bound.

- [ ] **Step 6: Wire route pages**

In `catalog/page.tsx`, `catalog/[slug]/page.tsx`, and `search/page.tsx`, pass:

```tsx
attributeRangeFilters={parsed.attributeRangeFilters}
currentAttributeRangeFilters={parsed.attributeRangeFilters}
attributeRangeGroups={catalog.attributeRangeGroups}
```

- [ ] **Step 7: Verify desktop/mobile HTML**

Run:

```powershell
npm.cmd test -- src/lib/catalog-attribute-filters.test.ts src/lib/catalog-query.test.ts src/lib/catalog-ui.test.ts
npm.cmd run build
```

Expected: pass.

Manual local or prod smoke after deploy must verify:

- desktop catalog HTML contains `attrMin`, `attrMax`, and range labels;
- mobile filter details contains the same range labels and controls.

Commit:

```powershell
git add -- web-store/src/lib/catalog.ts web-store/src/app/catalog/catalog-view.tsx web-store/src/app/catalog/page.tsx web-store/src/app/catalog/[slug]/page.tsx web-store/src/app/search/page.tsx web-store/src/lib/catalog-attribute-filters.ts web-store/src/lib/catalog-attribute-filters.test.ts
git commit -m "Render numeric attribute range filters"
```

## Task 4: Electrical and Computer Extractors

**Files:**
- Modify: `web-store/src/lib/product-attributes.ts`
- Modify: `web-store/src/lib/product-attributes.test.ts`
- Modify: `web-store/src/lib/product-name-specs.ts`
- Modify: `web-store/src/lib/product-name-specs.test.ts`

- [ ] **Step 1: Write failing extractor tests**

Add to `product-attributes.test.ts`:

```ts
expect(extractProductNameAttributes("Кабель ВВГнг-LS 3х2,5 ГОСТ, бухта 100 м, белый")).toEqual([
  { key: "electrical_product_type", label: "Тип электротовара", value: "Кабель", normalizedValue: "cable", numericValue: null, unit: null, source: "name" },
  { key: "cable_cores", label: "Количество жил", value: "3 жилы", normalizedValue: "3", numericValue: 3, unit: "жил", source: "name" },
  { key: "cable_section", label: "Сечение кабеля", value: "2.5 мм²", normalizedValue: "2.5", numericValue: 2.5, unit: "мм²", source: "name" },
  { key: "cable_length", label: "Длина", value: "100 м", normalizedValue: "100", numericValue: 100, unit: "м", source: "name" },
  { key: "color", label: "Цвет", value: "Белый", normalizedValue: "white", numericValue: null, unit: null, source: "name" },
]);
```

Add:

```ts
expect(extractProductNameAttributes("Ноутбук ASUS VivoBook 15 Intel Core i5-1235U, 16 ГБ RAM, SSD 512 ГБ, HDMI, Wi-Fi")).toEqual([
  { key: "ram", label: "Оперативная память", value: "16 ГБ", normalizedValue: "16", numericValue: 16, unit: "ГБ", source: "name" },
  { key: "storage_type", label: "Тип накопителя", value: "SSD", normalizedValue: "ssd", numericValue: null, unit: null, source: "name" },
  { key: "storage_capacity", label: "Объем накопителя", value: "512 ГБ", normalizedValue: "512", numericValue: 512, unit: "ГБ", source: "name" },
  { key: "processor_family", label: "Процессор", value: "Intel Core i5", normalizedValue: "intel_core_i5", numericValue: null, unit: null, source: "name" },
  { key: "processor_model", label: "Модель процессора", value: "Intel Core i5-1235U", normalizedValue: "intel_core_i5_1235u", numericValue: null, unit: null, source: "name" },
  { key: "interface", label: "Интерфейс", value: "HDMI", normalizedValue: "hdmi", numericValue: null, unit: null, source: "name" },
  { key: "interface", label: "Интерфейс", value: "Wi-Fi", normalizedValue: "wi_fi", numericValue: null, unit: null, source: "name" },
]);
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
npm.cmd test -- src/lib/product-attributes.test.ts
```

Expected: fail because new attributes are not extracted.

- [ ] **Step 3: Implement precise extraction**

In `product-attributes.ts`:

- add color normalization for common colors: white, black, gray, red, blue, green, beige;
- add cable pattern `/(\d+)\s*[xх]\s*(\d+(?:[.,]\d+)?)/i`;
- add cable length pattern `/(\d+(?:[.,]\d+)?)\s*м\b/i` only when product looks like cable/wire;
- add electrical product type from safe keywords: cable, wire, socket, switch, breaker, lamp, connector, box;
- add voltage/current/power patterns;
- add processor model patterns for `Intel Core i3/i5/i7/i9`, `AMD Ryzen 3/5/7/9`;
- add interface values when exact keywords exist: HDMI, USB, RJ-45, Wi-Fi, Bluetooth.

Keep all helpers local to `product-attributes.ts`. Do not introduce a broad parser file in this task.

- [ ] **Step 4: Add card specs for new highlights**

In `product-name-specs.ts`, include these keys in `cardAttributeKeys`:

```ts
"electrical_product_type",
"cable_cores",
"cable_section",
"cable_length",
"processor_family",
"processor_model",
"interface",
```

Add tests to show catalog cards can display cable section and processor.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm.cmd test -- src/lib/product-attributes.test.ts src/lib/product-name-specs.test.ts src/lib/product-display.test.ts
```

Expected: pass.

Commit:

```powershell
git add -- web-store/src/lib/product-attributes.ts web-store/src/lib/product-attributes.test.ts web-store/src/lib/product-name-specs.ts web-store/src/lib/product-name-specs.test.ts
git commit -m "Extract electrical and computer attributes"
```

## Task 5: Full Verification, Deploy, and Attribute Sync

**Files:**
- Modify: `web-store/HANDOFF.md`

- [ ] **Step 1: Run full local verification**

Run:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

Expected:

- all Vitest tests pass;
- ESLint exits 0;
- Next build exits 0.

- [ ] **Step 2: Deploy to VPS**

Run:

```powershell
$env:WEB_STORE_SSH_KEY_PATH = Join-Path $env:USERPROFILE '.ssh\climat_simf_deploy'
npm.cmd run deploy:vps -- --remote-timeout 1800
```

Expected: `Deploy completed`.

- [ ] **Step 3: Rebuild product attributes on production**

Run:

```powershell
$key = Join-Path $env:USERPROFILE '.ssh\climat_simf_deploy'
ssh -i $key -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@212.116.115.150 'cd /var/www/climat-simf.ru && npm run sync:attributes'
```

Expected: `product attributes backfill complete`.

If SSH disconnects, check the process and `SyncLog` before rerunning.

- [ ] **Step 4: Production smoke checks**

Run HTTP checks for:

- `/catalog/stroitelstvo-i-remont-10118?attrMin=cable_section:2.5`;
- `/catalog/kompyuternaya-tehnika-9975?attrMin=ram:16`;
- `/catalog/kompyuternaya-tehnika-9975?attr=processor_family:intel_core_i5`;
- `/search?q=HDMI&attr=interface:hdmi`;
- `/sitemap.xml`.

Each page must return 200 and contain relevant labels plus `Под заказ 7 дней` for catalog/product listings where products render.

- [ ] **Step 5: Mobile smoke check**

Use a mobile-width browser or HTML check to confirm the changed category contains:

- `Фильтры`;
- active filter count when a range is active;
- `attrMin` / `attrMax`;
- the changed range label, for example `Сечение кабеля` or `Оперативная память`.

- [ ] **Step 6: Record handoff and commit**

Append to `web-store/HANDOFF.md`:

```md
- Adaptive filter Phase 1 deployed: registry, numeric `attrMin`/`attrMax` ranges, electrical/SCS and computer extractors. Smoke: electrical range, computer RAM range, processor exact filter, interface exact filter, sitemap, PM2 online, fresh error-log empty. Backup source: `<backup path>`.
```

Commit:

```powershell
git add -- web-store/HANDOFF.md
git commit -m "Record adaptive filter phase 1 deployment"
git push origin codex/Site_master
```

## Self-Review

- Spec coverage: Phase 1 covers the registry, numeric ranges, priority electrical/SCS extractors, priority computer extractors, desktop/mobile checks, production deploy, and handoff.
- Scope kept bounded: admin coverage report and long-tail category families are intentionally not part of Phase 1 code; they remain in the design spec for later phases.
- No placeholders: every task names concrete files, commands, and expected outcomes.
- Type consistency: range filter type is `CatalogAttributeRangeFilter`; range URL params are `attrMin` and `attrMax`; exact filters remain `CatalogAttributeFilter` and `attr`.
