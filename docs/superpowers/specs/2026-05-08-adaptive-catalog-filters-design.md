# Adaptive Catalog Filters Design

## Purpose

Build a dynamic catalog filtering architecture for the whole storefront, not a fixed set of hand-written filters for a few categories. A buyer should open any catalog section and see filters that match the actual goods in that section: TV diagonal and Smart TV for televisions, cable section and length for electrical goods, processor and RAM for laptops, density and whiteness for paper, No Frost and color for refrigerators, and so on.

## Current Context

Production catalog snapshot on 2026-05-08:

- `Строительство и ремонт`: 118613 products; the largest child section is `Электротехническая продукция, СКС` with 68311 products.
- `Компьютерная техника`: 73680 products.
- `Бытовая техника`: 29336 products.
- `Запчасти`: 26911 products.
- `Электроника`: 14901 products.
- `Товары для дома`: 9444 products.
- `Дача, сад и огород`: 7057 products.

Current structured attributes are useful but narrow: `screen_diagonal`, `smart_tv`, `resolution`, `storage_type`, `storage_capacity`, `ram`, `daily_capacity`, `tank_volume`, `power_source`, `power_hp`, `battery_voltage`, `battery_capacity`.

This means the main problem is not only UI. The catalog needs a repeatable enrichment pipeline and category-aware attribute profiles.

## Principles

- Base filters are always available: price, brand, available to order, photo, sort.
- Category-specific filters appear only when matching products in the current category have real values.
- Empty non-active filters are hidden.
- Active filters remain visible even if the current narrowed result count is zero.
- Every filtering feature must be designed and verified for both desktop and mobile in the same implementation step.
- Filter URLs remain parametric and `noindex, follow` unless a curated SEO landing page is created separately.
- Public delivery copy must remain `Под заказ 7 дней`; no public same-day promise.
- The architecture must tolerate incomplete data: if a category lacks attributes, the system shows base filters and reports the coverage gap instead of inventing unrelated filters.

## Recommended Architecture

### 1. Attribute Registry

Create one typed registry of filterable attributes. Each attribute defines:

- stable key, for example `cable_section`, `processor_family`, `paper_density`;
- label for UI;
- value type: enum, number, boolean, text;
- unit, if numeric;
- preferred UI control: checkbox list, searchable checkbox list, numeric range, boolean toggle;
- normalization rules;
- category/profile hints;
- sorting rules.

The existing `ProductAttribute` table can store the values without a schema migration: `key`, `label`, `value`, `normalizedValue`, `numericValue`, `unit`, `source`.

### 2. Category Filter Profiles

Create profiles that map category names/slugs to relevant attribute keys. Profiles should be heuristic at first, using category name hints, and then can become explicit per category if needed.

Priority profiles:

- Electrical and SCS: product type, cable type, number of cores, section, length, voltage, current, power, IP rating, color, installation type.
- Computer equipment: device type, CPU family/model, RAM, storage type/capacity, GPU, screen diagonal, interface, form factor.
- Home appliances: device type, No Frost, volume/capacity, load, color, energy class, installation type, power.
- Electronics/photo/video: device type, resolution, screen diagonal, matrix/display type, lens/focal hints, power source, memory/storage, connectivity.
- Garden/tools: product type, power source, engine power, battery voltage/capacity, cutting width, tank volume, weight.
- Auto/moto: product type, tire width/profile/diameter, season, oil viscosity, voltage, capacity, compatibility hints.
- Home goods and office supplies: material, color, size, volume, paper format, paper density, whiteness, sheet count.
- Clothing/workwear: size, height, chest range, gender, season, color, material.
- Spare parts: compatible brand/model hints, part type, voltage/capacity for batteries, connector/interface.

Profiles decide what can be shown; the facet engine still shows only attributes that exist in current products.

### 3. Extractor Pipeline

Use a pipeline that can enrich products from multiple sources:

1. Existing structured supplier fields: brand, weight, volume, warranty, part, barcodes.
2. Product names and supplier names.
3. Existing `Product.specifications` JSON when populated.
4. Manual/admin attributes for important SKUs.
5. Future supplier characteristics feed if available.

Each extractor emits normalized `ProductAttribute` rows. It must be deterministic and covered by tests. It should never create broad or noisy values from weak patterns.

### 4. Facet Engine

The catalog page should build facets from the current product set:

- start with category/search/price/photo/availability filters;
- apply selected brands and selected attributes where appropriate;
- group `ProductAttribute` values by key/value;
- for each visible group, count options against the current narrowed product set;
- for selected attributes in the same group, count sibling options with other selected groups applied, so users can switch values naturally.

The current dynamic `attr=key:value` URL format remains valid.

Add numeric range support as a new URL form:

- `attrMin=key:value`
- `attrMax=key:value`

The engine uses `numericValue` for range filters and still preserves exact enum filters through `attr=key:value`.

### 5. UI Behavior

Desktop:

- left filter column;
- grouped blocks;
- base filters first;
- category-specific attributes after brand and price;
- searchable checkbox list for long enum lists;
- range inputs for numeric values;
- active filter chips above products.

Mobile:

- sticky `Фильтры` and `Категории` controls;
- bottom sheet or stacked panel;
- active filter count and chips;
- the same relevant category-specific filters as desktop;
- searchable long lists and numeric ranges must be touch-friendly;
- apply/reset controls must stay visible and not require hunting through a long page;
- controls must fit without text overlap.

The UI must not show irrelevant groups. For example, `SSD` must not appear in `Дача, сад и огород` unless the category actually contains SSD products.

### 6. Coverage Reporting

Add an admin report for filter quality:

- category;
- product count;
- products with at least one attribute;
- top attribute keys present;
- missing expected attributes from the category profile;
- sample products without attributes.

This report drives enrichment work and prevents guessing.

## Initial Attribute Expansion Plan

### Phase 1: Registry and Range Facets

Implement the registry and numeric range filtering for existing attributes:

- screen diagonal;
- storage capacity;
- RAM;
- daily capacity;
- tank volume;
- power HP;
- battery voltage;
- battery capacity.

### Phase 2: Electrical and SCS

Add extractors for the largest category:

- cable section, for example `1.5 мм²`, `2.5 мм²`;
- number of cores, for example `3 жилы`, `5 жил`;
- cable length, meters;
- voltage, volts;
- current, amps;
- power, watts/kilowatts;
- IP rating;
- color;
- product type: cable, socket, switch, breaker, lamp, connector, box.

### Phase 3: Computer Equipment

Add extractors for:

- CPU family/model;
- RAM;
- storage type/capacity;
- GPU family/model when clear;
- screen diagonal;
- interface: USB, HDMI, RJ-45, Wi-Fi, Bluetooth;
- printer cartridge color/type for consumables.

### Phase 4: Home Appliances and Electronics

Add extractors for:

- refrigerator No Frost, volume, color, freezer/refrigerator type;
- washer load, depth, inverter, drying, installation type;
- TV diagonal, resolution, Smart TV, display type;
- camera/video resolution, lens/focal hints only when patterns are reliable.

### Phase 5: Long Tail

Add profiles and extractors for home goods, office supplies, auto/moto, workwear, sport, health, beauty, pets, and clearance goods. Each long-tail extractor starts only after category samples show reliable patterns.

## Testing Strategy

- Unit tests for every extractor pattern with real Russian product-name examples.
- Unit tests for registry validation and URL normalization.
- Unit tests for Prisma where builders for exact and numeric range attributes.
- Catalog rendering tests for active count and chips.
- Mobile and desktop smoke checks for every new filter family.
- Production smoke after every deploy:
  - one category URL for the changed profile;
  - one exact attribute URL;
  - one numeric range URL;
  - one mobile-width render/check of the changed category;
  - `/sitemap.xml`;
  - PM2 status and fresh error-log tail.

## Rollout Rules

- Ship one category family at a time.
- Run `npm test`, `npm run lint`, `npm run build` before commit/deploy.
- Run `npm run sync:attributes` after extractor changes.
- Commit code and handoff notes separately when helpful.
- Do not stage unrelated existing root changes.

## Risks

- Product names can be noisy. Extractors must prefer precision over volume.
- Some categories may need manual/admin enrichment because names do not contain enough data.
- Too many exact numeric values can clutter UI; numeric values should prefer ranges when the option count is high.
- Facet counting can stress the production DB. Keep reads sequential or bounded, and cache where appropriate.

## Success Criteria

- Each major root category shows only relevant filter groups.
- The largest sections gain useful, buyer-facing attributes over time.
- No category shows unrelated starter filters.
- Active filters are shareable through URLs.
- Mobile filter controls expose the same logic as desktop and remain usable without overlap or hidden critical actions.
- Admin coverage report shows measurable improvement after each enrichment phase.
