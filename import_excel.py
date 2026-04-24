"""
Импорт товаров из Excel/CSV в data/products.json

Запуск:
    python import_excel.py прайс.xlsx
    python import_excel.py прайс.xlsx --sheet 0       # номер листа (с нуля)
    python import_excel.py прайс.xlsx --stock 10      # остаток по умолчанию
    python import_excel.py прайс.xlsx --discount 5+=5,20+=10

Структура прайса (автоопределение):
    Артикул | Бренд | Наименование | Цена (руб.) | Залог (руб.)
    + строки-заголовки категорий (без цены) — определяются автоматически
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Устанавливаю pandas + openpyxl...")
    os.system(f"{sys.executable} -m pip install pandas openpyxl")
    import pandas as pd


# ─── Синонимы названий столбцов ──────────────────────────────────────────────

_ALIASES = {
    "sku":         ["артикул", "арт", "art", "sku", "article", "код", "код товара", "part"],
    "brand":       ["бренд", "brand", "марка", "производитель", "make"],
    "name":        ["наименование", "название", "товар", "name", "product", "номенклатура", "позиция"],
    "price":       ["цена", "price", "стоимость", "цена руб", "цена, руб", "цена (руб)", "цена (руб.)",
                    "розничная цена", "прайс", "розн", "розничная"],
    "stock":       ["остаток", "кол-во", "количество", "qty", "stock", "наличие", "в наличии"],
    "description": ["описание", "description", "характеристики", "примечание"],
    "category":    ["категория", "раздел", "group", "группа"],
}


def _norm(s: str) -> str:
    return re.sub(r"[\s_.,()/]+", " ", str(s).lower()).strip()


def _find_col(columns: list[str], field: str) -> str | None:
    for col in columns:
        cn = _norm(col)
        for alias in _ALIASES[field]:
            if alias in cn or cn in alias:
                return col
    return None


def _clean_price(val) -> float | None:
    if pd.isna(val):
        return None
    s = re.sub(r"[^\d.,]", "", str(val)).replace(",", ".")
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


def _clean_int(val, default=0) -> int:
    if pd.isna(val):
        return default
    s = re.sub(r"[^\d]", "", str(val))
    return int(s) if s else default


def _make_id(sku: str, name: str, idx: int) -> str:
    if sku:
        clean = re.sub(r"[^A-Z0-9\-]", "", sku.upper())[:20]
        if clean:
            return clean
    words = re.sub(r"[^а-яёa-z0-9\s]", "", name.lower()).split()[:2]
    slug = "-".join(w[:5].upper() for w in words) or "ITEM"
    return f"{slug}-{idx:03d}"


def _is_category_row(row: dict, price_col: str | None, sku_col: str | None) -> str | None:
    """
    Возвращает текст категории если строка — заголовок раздела, иначе None.
    Признаки: нет цены, нет артикула, есть какой-то текст в строке.
    """
    if price_col and not pd.isna(row.get(price_col)):
        return None  # есть цена → товарная строка
    if sku_col and not pd.isna(row.get(sku_col)):
        return None  # есть артикул → товарная строка

    # Ищем любую непустую ячейку с текстом
    for v in row.values():
        if not pd.isna(v):
            text = str(v).strip()
            if text and text.lower() not in ("nan", "none") and len(text) > 2:
                return text
    return None


def parse_discounts(raw: str) -> dict:
    result = {}
    for part in raw.split(","):
        m = re.match(r"(\d+)\+?=(\d+)", part.strip())
        if m:
            result[f"{m.group(1)}+"] = int(m.group(2))
    return result


PRICES_DIR = Path(__file__).parent / "prices"


def _pick_file_from_prices_dir() -> Path:
    """Если файл не указан — показываем что лежит в папке prices/."""
    files = sorted(
        f for f in PRICES_DIR.iterdir()
        if f.suffix.lower() in (".xlsx", ".xls", ".csv")
    )
    if not files:
        print(f"❌ Папка prices/ пуста. Положите туда Excel или CSV файл и повторите.")
        sys.exit(1)
    if len(files) == 1:
        print(f"📂 Найден файл: {files[0].name}")
        return files[0]
    print("Файлы в папке prices/:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    raw = input("Выберите номер файла [1]: ").strip() or "1"
    return files[int(raw) - 1]


def main():
    parser = argparse.ArgumentParser(description="Импорт прайса в products.json")
    parser.add_argument("file", nargs="?", default=None, help="Путь к Excel или CSV файлу (если не указан — ищет в папке prices/)")
    parser.add_argument("--sheet", default=None, help="Номер или имя листа (по умолчанию — первый)")
    parser.add_argument("--stock", type=int, default=0, help="Остаток по умолчанию (если нет в файле)")
    parser.add_argument("--discount", default="", help="Скидки: 5+=5,20+=10")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ Файл не найден: {path}")
            sys.exit(1)
    else:
        path = _pick_file_from_prices_dir()

    default_discounts = parse_discounts(args.discount) if args.discount else {}

    # ── Читаем файл ───────────────────────────────────────────────────────────
    print(f"\n📂 Открываю: {path}")

    if path.suffix.lower() in (".xlsx", ".xls"):
        xl = pd.ExcelFile(path)
        sheets = xl.sheet_names

        if args.sheet is not None:
            sheet = sheets[int(args.sheet)] if str(args.sheet).isdigit() else args.sheet
        elif len(sheets) > 1:
            print("Листы в файле:")
            for i, s in enumerate(sheets):
                print(f"  {i + 1}. {s}")
            raw = input("Выбери номер листа [1]: ").strip() or "1"
            sheet = sheets[int(raw) - 1]
        else:
            sheet = sheets[0]

        print(f"   Лист: {sheet}")
        df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
    else:
        for sep in (";", ",", "\t"):
            try:
                df = pd.read_csv(path, sep=sep, header=None, dtype=str, encoding="utf-8-sig")
                if df.shape[1] > 1:
                    break
            except Exception:
                pass

    print(f"   Строк: {len(df)}, столбцов: {df.shape[1]}")

    # ── Ищем строку заголовков ────────────────────────────────────────────────
    header_row_idx = 0
    for i, row in df.iterrows():
        row_vals = [_norm(str(v)) for v in row if not pd.isna(v)]
        # Если в строке есть "артикул" или "наименование" или "цена" — это заголовок
        if any(
            any(alias in rv for alias in _ALIASES[field])
            for field in ("sku", "name", "price")
            for rv in row_vals
        ):
            header_row_idx = i
            break

    print(f"   Строка заголовков: {header_row_idx + 1}")
    df.columns = [str(v).strip() if not pd.isna(v) else f"col_{j}"
                  for j, v in enumerate(df.iloc[header_row_idx])]
    df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
    df.dropna(how="all", inplace=True)
    cols = list(df.columns)
    print(f"   Столбцы: {cols}")

    # ── Определяем маппинг столбцов ───────────────────────────────────────────
    print("\n--- Определяю столбцы ---")
    col_sku   = _find_col(cols, "sku")
    col_brand = _find_col(cols, "brand")
    col_name  = _find_col(cols, "name")
    col_price = _find_col(cols, "price")
    col_stock = _find_col(cols, "stock")
    col_desc  = _find_col(cols, "description")
    col_cat   = _find_col(cols, "category")

    def _report(label, col):
        status = f"✅ «{col}»" if col else "⚠️  не найден (пропускается)"
        print(f"  {label:25s} → {status}")

    _report("Артикул (sku)",       col_sku)
    _report("Бренд",               col_brand)
    _report("Наименование",        col_name)
    _report("Цена",                col_price)
    _report("Остаток",             col_stock)
    _report("Описание",            col_desc)
    _report("Категория (столбец)", col_cat)

    if not col_name or not col_price:
        print("\n❌ Обязательные столбцы (название и цена) не найдены.")
        print("   Укажи вручную (введи имя столбца из списка выше):")
        if not col_name:
            col_name = input("  Столбец с названием товара: ").strip() or None
        if not col_price:
            col_price = input("  Столбец с ценой: ").strip() or None
        if not col_name or not col_price:
            sys.exit(1)

    # Если нет отдельного столбца категорий — будем определять по строкам-заголовкам
    auto_category = col_cat is None
    if auto_category:
        print("  Категории             → определяю по строкам-заголовкам (без цены и артикула)")

    # ── Парсим строки ─────────────────────────────────────────────────────────
    products = []
    skipped = 0
    current_category = ""
    idx = 1

    for _, row in df.iterrows():
        row_dict = dict(row)

        # Проверяем: строка-заголовок категории?
        if auto_category:
            cat_text = _is_category_row(row_dict, col_price, col_sku)
            if cat_text:
                current_category = cat_text
                print(f"  [категория] {current_category}")
                continue

        # Название
        name_raw = row_dict.get(col_name, "")
        name = str(name_raw).strip() if not pd.isna(name_raw) else ""
        if not name or name.lower() in ("nan", "none"):
            skipped += 1
            continue

        # Если есть бренд — добавляем к названию
        brand = ""
        if col_brand:
            b = row_dict.get(col_brand, "")
            brand = str(b).strip() if not pd.isna(b) else ""
            if brand.lower() in ("nan", "none"):
                brand = ""
        full_name = f"{brand} {name}".strip() if brand else name

        # Цена
        price = _clean_price(row_dict.get(col_price))
        if price is None:
            skipped += 1
            continue

        # Артикул
        sku = ""
        if col_sku:
            s = row_dict.get(col_sku, "")
            sku = str(s).strip() if not pd.isna(s) else ""
            if sku.lower() in ("nan", "none"):
                sku = ""

        # Остаток
        stock = args.stock
        if col_stock:
            stock = _clean_int(row_dict.get(col_stock), default=args.stock)

        # Категория
        category = current_category
        if col_cat:
            c = row_dict.get(col_cat, "")
            category = str(c).strip() if not pd.isna(c) else current_category

        # Описание
        description = ""
        if col_desc:
            d = row_dict.get(col_desc, "")
            description = str(d).strip() if not pd.isna(d) else ""
            if description.lower() in ("nan", "none"):
                description = ""

        products.append({
            "id": _make_id(sku, full_name, idx),
            "name": full_name,
            "description": description,
            "price": round(price, 2),
            "stock": stock,
            "unit": "шт",
            "category": category,
            "supplier_sku": sku,
            "discounts": default_discounts.copy(),
        })
        idx += 1

    # ── Превью ────────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"Готово к импорту: {len(products)} товаров, пропущено: {skipped}")
    print(f"{'─'*60}")
    print("Первые 5 позиций:")
    for p in products[:5]:
        print(f"  [{p['category']}] {p['name'][:50]:50s} {p['price']:>10,.0f} ₽  арт:{p['supplier_sku']}")
    print(f"{'─'*60}")

    if not products:
        print("❌ Ни одного товара не распознано. Проверь файл.")
        sys.exit(1)

    # ── Сохраняем ─────────────────────────────────────────────────────────────
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "products.json"

    if out_path.exists():
        ans = input(f"\nФайл {out_path} уже существует. Перезаписать? [y/n]: ").strip().lower()
        if ans != "y":
            print("Отменено.")
            sys.exit(0)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Сохранено: {out_path}")
    print(f"   Товаров: {len(products)}")
    print(f"\nЗапускай бота: py main.py")


if __name__ == "__main__":
    main()
