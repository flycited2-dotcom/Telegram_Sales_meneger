"""
Импорт товаров из Excel/CSV в data/products.json

Запуск:
    python import_excel.py прайс.xlsx
    python import_excel.py прайс.csv

Скрипт автоматически определяет столбцы по названию.
Если не может — спросит тебя вручную.

Поддерживаемые форматы:
    .xlsx, .xls, .csv
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Устанавливаю pandas...")
    os.system(f"{sys.executable} -m pip install pandas openpyxl")
    import pandas as pd


# ─── Синонимы названий столбцов ──────────────────────────────────────────────

COLUMN_ALIASES = {
    "name": [
        "наименование", "название", "товар", "продукт", "наим", "name",
        "product", "item", "описание товара", "номенклатура", "позиция",
    ],
    "price": [
        "цена", "стоимость", "price", "cost", "цена руб", "цена, руб",
        "цена руб.", "розничная цена", "прайс", "сумма",
    ],
    "stock": [
        "остаток", "количество", "наличие", "кол-во", "qty", "stock",
        "quantity", "в наличии", "остатки", "доступно", "кол", "остаток шт",
    ],
    "category": [
        "категория", "раздел", "группа", "тип", "category", "group",
        "вид товара", "подраздел",
    ],
    "description": [
        "описание", "характеристики", "description", "примечание",
        "доп.информация", "детали",
    ],
    "sku": [
        "артикул", "код", "арт", "sku", "article", "код товара",
        "партномер", "арт.", "art", "id",
    ],
    "unit": [
        "ед.изм", "единица", "ед", "unit", "шт", "упак", "ед. изм.",
        "единица измерения",
    ],
}


def normalize(s: str) -> str:
    return re.sub(r"[\s_.,-]+", " ", str(s).lower().strip())


def find_column(df_cols: list[str], field: str) -> str | None:
    """Ищет столбец по списку синонимов."""
    aliases = COLUMN_ALIASES[field]
    for col in df_cols:
        col_n = normalize(col)
        for alias in aliases:
            if alias in col_n or col_n in alias:
                return col
    return None


def ask_column(df_cols: list[str], field: str, label: str, required: bool = True) -> str | None:
    """Спрашивает пользователя какой столбец соответствует полю."""
    print(f"\nСтолбец для «{label}» не найден автоматически.")
    print("Доступные столбцы:")
    for i, c in enumerate(df_cols, 1):
        print(f"  {i}. {c}")
    if not required:
        print("  0. Пропустить (необязательное поле)")
    while True:
        raw = input(f"Введи номер столбца для «{label}»: ").strip()
        if raw == "0" and not required:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(df_cols):
            return df_cols[int(raw) - 1]
        print("Введи число от 1 до", len(df_cols))


def generate_id(name: str, idx: int) -> str:
    """Генерирует уникальный ID товара из названия."""
    # Взять первые значимые слова латиницей / транслит-хак через ascii
    clean = re.sub(r"[^а-яёa-z0-9\s]", "", name.lower())
    words = clean.split()[:2]
    slug = "-".join(w[:6].upper() for w in words if w) or "ITEM"
    return f"{slug}-{idx:03d}"


def main():
    if len(sys.argv) < 2:
        print("Использование: python import_excel.py <файл.xlsx или файл.csv>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Файл не найден: {path}")
        sys.exit(1)

    # ── Чтение файла ─────────────────────────────────────────────────────────
    print(f"\nЧитаю файл: {path}")
    if path.suffix.lower() in (".xlsx", ".xls"):
        # Если несколько листов — показать список
        xl = pd.ExcelFile(path)
        if len(xl.sheet_names) > 1:
            print("Листы в файле:")
            for i, sh in enumerate(xl.sheet_names, 1):
                print(f"  {i}. {sh}")
            raw = input("Выбери номер листа [1]: ").strip() or "1"
            sheet = xl.sheet_names[int(raw) - 1]
        else:
            sheet = xl.sheet_names[0]
        df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    else:
        # CSV — пробуем разные разделители
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8-sig")
                if df.shape[1] > 1:
                    break
            except Exception:
                pass

    # Удалить полностью пустые строки/столбцы
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    print(f"Найдено строк: {len(df)}, столбцов: {len(cols)}")
    print("Столбцы:", cols)

    # ── Определение маппинга ─────────────────────────────────────────────────
    print("\n--- Определяю столбцы ---")
    mapping = {}

    for field, label, required in [
        ("name",        "Название товара",      True),
        ("price",       "Цена (₽)",             True),
        ("stock",       "Остаток (кол-во)",      False),
        ("category",    "Категория",            False),
        ("description", "Описание",             False),
        ("sku",         "Артикул поставщика",   False),
        ("unit",        "Единица измерения",    False),
    ]:
        col = find_column(cols, field)
        if col:
            print(f"  ✅ {label} → «{col}»")
            mapping[field] = col
        else:
            col = ask_column(cols, field, label, required=required)
            if col:
                mapping[field] = col

    if "name" not in mapping or "price" not in mapping:
        print("\n❌ Не удалось определить обязательные поля (название и цена). Выход.")
        sys.exit(1)

    # ── Скидки (опционально) ──────────────────────────────────────────────────
    print("\nВведи оптовые скидки (или нажми Enter чтобы пропустить).")
    print("Формат: 5+=3,20+=7  (означает: от 5 шт — скидка 3%, от 20 шт — 7%)")
    raw_disc = input("Скидки [Enter — без скидок]: ").strip()
    default_discounts: dict = {}
    if raw_disc:
        for part in raw_disc.split(","):
            m = re.match(r"(\d+)\+?=(\d+)", part.strip())
            if m:
                default_discounts[f"{m.group(1)}+"] = int(m.group(2))
    if default_discounts:
        print(f"  Скидки применятся ко всем товарам: {default_discounts}")

    # ── Преобразование строк ─────────────────────────────────────────────────
    products = []
    skipped = 0

    for idx, row in enumerate(df.itertuples(index=False), start=1):
        row_dict = dict(zip(cols, row))

        name_raw = row_dict.get(mapping["name"], "")
        price_raw = row_dict.get(mapping["price"], "")

        name = str(name_raw).strip() if pd.notna(name_raw) else ""
        if not name or name.lower() in ("nan", "none", "наименование", "название"):
            skipped += 1
            continue

        # Цена: убрать пробелы, запятые→точки
        price_str = re.sub(r"[^\d.,]", "", str(price_raw))
        price_str = price_str.replace(",", ".")
        try:
            price = float(price_str)
        except ValueError:
            skipped += 1
            continue
        if price <= 0:
            skipped += 1
            continue

        # Остаток
        stock = 0
        if "stock" in mapping:
            stock_raw = row_dict.get(mapping["stock"], "0")
            stock_str = re.sub(r"[^\d]", "", str(stock_raw))
            stock = int(stock_str) if stock_str else 0

        # Категория
        category = ""
        if "category" in mapping:
            cat_raw = row_dict.get(mapping["category"], "")
            category = str(cat_raw).strip() if pd.notna(cat_raw) else ""

        # Описание
        description = ""
        if "description" in mapping:
            desc_raw = row_dict.get(mapping["description"], "")
            description = str(desc_raw).strip() if pd.notna(desc_raw) else ""

        # Артикул
        supplier_sku = ""
        if "sku" in mapping:
            sku_raw = row_dict.get(mapping["sku"], "")
            supplier_sku = str(sku_raw).strip() if pd.notna(sku_raw) else ""

        # Единица измерения
        unit = "шт"
        if "unit" in mapping:
            unit_raw = row_dict.get(mapping["unit"], "шт")
            u = str(unit_raw).strip() if pd.notna(unit_raw) else "шт"
            unit = u if u and u.lower() != "nan" else "шт"

        # ID товара
        product_id = (
            re.sub(r"[^A-Z0-9-]", "", supplier_sku.upper())[:20]
            if supplier_sku
            else generate_id(name, idx)
        )

        products.append({
            "id": product_id,
            "name": name,
            "description": description,
            "price": round(price, 2),
            "stock": stock,
            "unit": unit,
            "category": category,
            "supplier_sku": supplier_sku,
            "discounts": default_discounts.copy(),
        })

    # ── Сохранение ────────────────────────────────────────────────────────────
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "products.json"

    # Предупреждение если файл уже есть
    if out_path.exists():
        ans = input(f"\nФайл {out_path} уже существует. Перезаписать? [y/n]: ").strip().lower()
        if ans != "y":
            print("Отменено.")
            sys.exit(0)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Готово!")
    print(f"   Товаров импортировано: {len(products)}")
    print(f"   Пропущено (нет цены или названия): {skipped}")
    print(f"   Файл сохранён: {out_path}")
    print("\nТеперь запускай: python main.py")


if __name__ == "__main__":
    main()
