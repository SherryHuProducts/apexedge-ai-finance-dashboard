from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


TEXT_FIELDS = ["date", "year", "month", "sku", "product", "category", "channel", "department"]
NUMERIC_FIELDS = [
    "units", "list_price", "gross_sales", "discount", "returns", "net_revenue", "product_cost",
    "freight", "tariff", "platform_fee", "marketing_spend", "inventory_units", "inventory_value",
]
REQUIRED_ANALYSIS_FIELDS = [
    "gross_sales", "discount", "returns", "net_revenue", "product_cost", "freight", "tariff",
    "platform_fee", "marketing_spend",
]
KEY_FIELDS = ["date", "sku", "channel"]

ALIASES = {
    "date": ["date", "transaction date", "order date", "posting date", "report date", "reporting date", "reporting month", "period", "fiscal period", "日期", "交易日期", "订单日期", "记账日期", "报告日期", "期间", "会计期间", "月份日期"],
    "year": ["year", "fiscal year", "fy", "年度", "年份", "财年"],
    "month": ["month", "fiscal month", "月", "月份"],
    "sku": ["sku", "sku id", "item", "item id", "item code", "product code", "material", "material id", "货号", "商品编码", "物料", "物料编码", "产品编码"],
    "product": ["product", "product name", "item name", "description", "商品", "产品", "产品名称", "商品名称", "品名"],
    "category": ["category", "product category", "item category", "business unit", "bu", "品类", "产品类别", "商品类别", "业务单元"],
    "channel": ["channel", "sales channel", "platform", "marketplace", "渠道", "销售渠道", "平台"],
    "department": ["department", "dept", "cost center", "function", "owner", "部门", "成本中心", "职能", "归属部门"],
    "units": ["units", "unit", "quantity", "qty", "sales volume", "volume", "销量", "数量", "销售数量", "件数"],
    "list_price": ["list price", "unit price", "price", "asp", "selling price", "标价", "单价", "售价", "平均售价"],
    "gross_sales": ["gross sales", "gross revenue", "sales before returns", "booked sales", "销售总额", "销售收入总额", "总销售额", "含税销售额"],
    "discount": ["discount", "discounts", "promo", "promotion", "sales discount", "折扣", "促销折让", "销售折扣", "优惠"],
    "returns": ["returns", "return amount", "refunds", "sales returns", "退货", "退款", "退货金额", "销售退回"],
    "net_revenue": ["net revenue", "revenue", "sales", "net sales", "amount", "actual revenue", "净收入", "营业收入", "销售额", "净销售额", "收入", "实际收入"],
    "product_cost": ["product cost", "cogs", "cost of goods sold", "material cost", "standard cost", "成本", "产品成本", "销售成本", "主营业务成本", "物料成本", "标准成本"],
    "freight": ["freight", "shipping", "shipping cost", "logistics", "logistics cost", "运费", "物流费", "运输成本", "物流成本"],
    "tariff": ["tariff", "tariffs", "duty", "duties", "customs", "关税", "进口税", "海关税费"],
    "platform_fee": ["platform fee", "platform fees", "marketplace fee", "commission", "selling fee", "平台费", "渠道费", "佣金", "销售佣金"],
    "marketing_spend": ["marketing", "marketing spend", "marketing cost", "ad spend", "advertising", "广告费", "营销费用", "市场费用", "推广费", "广告投入"],
    "inventory_units": ["inventory units", "inventory qty", "stock units", "on hand qty", "库存数量", "库存量", "现有库存", "期末库存数量"],
    "inventory_value": ["inventory value", "inventory balance", "stock value", "ending inventory", "库存金额", "库存价值", "期末库存", "存货余额"],
}


def normalize_label(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower().replace("\n", " ")
    text = re.sub(r"[\s\-_/\\.()（）]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


ALIAS_LOOKUP = {normalize_label(alias): field for field, aliases in ALIASES.items() for alias in aliases}
METRIC_ALIAS_LOOKUP = {key: value for key, value in ALIAS_LOOKUP.items() if value in NUMERIC_FIELDS}


def _unique_headers(values: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    headers = []
    for idx, value in enumerate(values):
        base = normalize_label(value) or f"unnamed_{idx + 1}"
        seen[base] = seen.get(base, 0) + 1
        headers.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return headers


def _header_row(raw: pd.DataFrame) -> int:
    best_row, best_score = 0, float("-inf")
    for idx in range(min(len(raw), 20)):
        values = [normalize_label(v) for v in raw.iloc[idx].tolist()]
        values = [v for v in values if v and v not in ("nan", "none")]
        alias_hits = sum(v in ALIAS_LOOKUP for v in values)
        period_hits = sum(_period_from_token(v) is not None for v in values)
        numeric_like = sum(bool(re.fullmatch(r"[-+()$¥￥€£,\d.%]+", v)) for v in values)
        score = alias_hits * 12 + period_hits * 6 + min(len(values), 20) - numeric_like * 0.4
        if score > best_score:
            best_row, best_score = idx, score
    return best_row


def _period_from_token(value: Any) -> pd.Timestamp | None:
    text = normalize_label(value)
    if not text:
        return None
    compact = re.sub(r"\s+", "", text)
    match = re.search(r"(20\d{2})[年\-_/]?(0?[1-9]|1[0-2])(?:月)?", compact)
    if match:
        return pd.Timestamp(year=int(match.group(1)), month=int(match.group(2)), day=1)
    match = re.search(r"(20\d{2})q([1-4])", compact, flags=re.I)
    if match:
        return pd.Timestamp(year=int(match.group(1)), month=(int(match.group(2)) - 1) * 3 + 1, day=1)
    match = re.search(r"q([1-4])[^0-9]*(20\d{2})", compact, flags=re.I)
    if match:
        return pd.Timestamp(year=int(match.group(2)), month=(int(match.group(1)) - 1) * 3 + 1, day=1)
    # Ordinary finance values such as 50,000 must never be interpreted as dates.
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", compact):
        return None
    try:
        parsed = pd.to_datetime(text, errors="coerce")
        if pd.notna(parsed) and 2000 <= parsed.year <= 2100:
            return pd.Timestamp(parsed.year, parsed.month, 1)
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _infer_period(source_name: str) -> pd.Timestamp | None:
    return _period_from_token(Path(source_name).stem)


def _infer_department(source_name: str) -> str:
    text = normalize_label(source_name)
    rules = [
        (["sales", "commercial", "销售", "业务"], "Sales / 销售"),
        (["marketing", "advertising", "市场", "营销", "广告"], "Marketing / 市场"),
        (["inventory", "warehouse", "stock", "库存", "仓储"], "Inventory / 库存"),
        (["supply", "procurement", "logistics", "供应链", "采购", "物流"], "Supply Chain / 供应链"),
        (["finance", "accounting", "p l", "财务", "会计"], "Finance / 财务"),
        (["retail", "amazon", "tiktok", "dtc", "渠道"], "Channel / 渠道"),
    ]
    for tokens, department in rules:
        if any(token in text for token in tokens):
            return department
    return "Unknown / 未识别"


def _parse_numeric(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    negative = text.str.match(r"^\(.*\)$", na=False)
    text = text.str.replace(r"[,$¥￥€£%\s]", "", regex=True)
    text = text.str.replace(r"^\((.*)\)$", r"\1", regex=True)
    text = text.replace({"": None, "-": None, "—": None, "–": None, "n/a": None, "na": None, "nan": None, "none": None, "null": None})
    values = pd.to_numeric(text, errors="coerce")
    values.loc[negative & values.notna()] *= -1
    return values


def _parse_dates(series: pd.Series) -> pd.Series:
    values = series.copy()
    numeric = pd.to_numeric(values, errors="coerce")
    excel_mask = numeric.between(20000, 80000)
    parsed = pd.to_datetime(values, errors="coerce")
    if excel_mask.any():
        parsed.loc[excel_mask] = pd.to_datetime(numeric.loc[excel_mask], unit="D", origin="1899-12-30", errors="coerce")
    compact = values.astype(str).str.replace(r"\D", "", regex=True)
    yyyymm = compact.str.fullmatch(r"20\d{4}", na=False)
    if yyyymm.any():
        parsed.loc[yyyymm] = pd.to_datetime(compact.loc[yyyymm] + "01", format="%Y%m%d", errors="coerce")
    return parsed.dt.to_period("M").dt.to_timestamp()


def _wide_finance_table(data: pd.DataFrame) -> tuple[pd.DataFrame | None, list[str]]:
    period_columns = {column: _period_from_token(column) for column in data.columns}
    period_columns = {column: period for column, period in period_columns.items() if period is not None}
    if len(period_columns) < 2:
        return None, []
    non_period = [column for column in data.columns if column not in period_columns]
    best_column, best_hits = None, 0
    for column in non_period:
        hits = data[column].map(lambda value: normalize_label(value) in METRIC_ALIAS_LOOKUP).sum()
        if hits > best_hits:
            best_column, best_hits = column, int(hits)
    if best_column is None or best_hits < 2:
        return None, []
    records: list[dict[str, Any]] = []
    for period_column, period in period_columns.items():
        record: dict[str, Any] = {"date": period}
        for _, row in data.iterrows():
            metric = METRIC_ALIAS_LOOKUP.get(normalize_label(row.get(best_column)))
            if metric:
                record[metric] = row.get(period_column)
        records.append(record)
    return pd.DataFrame(records), [str(column) for column in period_columns]


def _read_tables(filename: str, content: bytes) -> list[tuple[str, pd.DataFrame]]:
    suffix = Path(filename).suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
            try:
                text = content.decode(encoding)
                if suffix == ".tsv":
                    delimiter = "\t"
                else:
                    try:
                        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
                    except csv.Error:
                        delimiter = ","
                rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
                width = max((len(row) for row in rows), default=0)
                frame = pd.DataFrame([row + [None] * (width - len(row)) for row in rows], dtype=object)
                return [("CSV", frame)]
            except (UnicodeDecodeError, csv.Error) as exc:
                last_error = exc
        raise ValueError(f"Unable to parse CSV: {last_error}")
    if suffix in (".xlsx", ".xls", ".xlsm"):
        excel = pd.ExcelFile(io.BytesIO(content))
        return [(sheet, pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=None, dtype=object)) for sheet in excel.sheet_names]
    raise ValueError(f"Unsupported file type: {suffix}")


def _issue(severity: str, source: str, sheet: str, issue: str, affected: int, action: str) -> dict[str, Any]:
    return {"Severity / 严重性": severity, "Source / 来源": source, "Sheet / 工作表": sheet, "Issue / 问题": issue, "Rows / 行数": int(affected), "Action / 建议": action}


def _clean_table(filename: str, sheet: str, raw: pd.DataFrame) -> tuple[pd.DataFrame | None, dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    raw_rows = len(raw)
    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    if raw.empty:
        summary = {"File / 文件": filename, "Sheet / 工作表": sheet, "Department / 部门": _infer_department(filename), "Raw Rows / 原始行": raw_rows, "Clean Rows / 清洗后行": 0, "Header Row / 表头行": "n.a.", "Mapped Fields / 已映射字段": "", "Unmapped / 未映射": "", "Period / 期间": "n.a.", "Status / 状态": "Empty / 空表"}
        issues.append(_issue("Warning / 警告", filename, sheet, "Empty table / 空表", raw_rows, "Confirm the correct sheet / 确认正确工作表"))
        return None, summary, issues

    header_row = _header_row(raw)
    data = raw.iloc[header_row + 1:].copy()
    data.columns = _unique_headers(raw.iloc[header_row].tolist())
    data = data.dropna(how="all").dropna(axis=1, how="all")
    wide, period_columns = _wide_finance_table(data)
    if wide is not None:
        data = wide
        issues.append(_issue("Info / 信息", filename, sheet, "Wide monthly report converted to long format / 月度宽表已转换为长表", len(wide), "Review mapped periods / 复核期间映射"))

    mapped_columns: dict[str, list[str]] = {}
    for column in data.columns:
        canonical = column if column in TEXT_FIELDS + NUMERIC_FIELDS else ALIAS_LOOKUP.get(normalize_label(column))
        if canonical:
            mapped_columns.setdefault(canonical, []).append(column)
    unmapped = [str(column) for column in data.columns if not (column in TEXT_FIELDS + NUMERIC_FIELDS or ALIAS_LOOKUP.get(normalize_label(column)))]
    if unmapped:
        issues.append(_issue("Warning / 警告", filename, sheet, f"{len(unmapped)} unmapped columns / {len(unmapped)} 个字段未映射", len(data), "Review the unmapped-field list / 复核未映射字段清单"))

    cleaned = pd.DataFrame(index=data.index)
    for canonical, columns in mapped_columns.items():
        merged = data[columns[0]].copy()
        for alternate in columns[1:]:
            merged = merged.combine_first(data[alternate])
        cleaned[canonical] = merged
        if len(columns) > 1:
            issues.append(_issue("Warning / 警告", filename, sheet, f"Multiple columns mapped to {canonical} / 多列映射至 {canonical}", len(data), "Confirm the preferred source column / 确认首选来源字段"))

    if "date" not in cleaned:
        if "year" in cleaned and "month" in cleaned:
            cleaned["date"] = pd.to_datetime(cleaned["year"].astype(str).str.replace(r"\.0$", "", regex=True) + "-" + cleaned["month"].astype(str).str.replace(r"\.0$", "", regex=True) + "-01", errors="coerce")
        elif "month" in cleaned:
            cleaned["date"] = _parse_dates(cleaned["month"])
        else:
            inferred = _infer_period(f"{filename} {sheet}")
            if inferred is not None:
                cleaned["date"] = inferred
                issues.append(_issue("Info / 信息", filename, sheet, f"Period inferred as {inferred:%Y-%m} / 根据文件名识别期间", len(data), "Confirm the inferred period / 确认识别期间"))
            else:
                issues.append(_issue("Critical / 严重", filename, sheet, "Missing reporting date / 缺少报告日期", len(data), "Add a date column or period to the filename / 添加日期字段或在文件名中注明期间"))
                cleaned["date"] = pd.NaT
    else:
        cleaned["date"] = _parse_dates(cleaned["date"])

    for field in NUMERIC_FIELDS:
        if field in cleaned:
            original_nonblank = cleaned[field].notna().sum()
            cleaned[field] = _parse_numeric(cleaned[field])
            invalid = original_nonblank - cleaned[field].notna().sum()
            if invalid:
                issues.append(_issue("Warning / 警告", filename, sheet, f"Invalid numeric values in {field} / {field} 存在无效数字", invalid, "Review currency, commas and text values / 复核币种、千分位和文本值"))

    text_key_columns = [field for field in ("sku", "product", "category", "channel", "department") if field in cleaned]
    total_mask = pd.Series(False, index=cleaned.index)
    if text_key_columns:
        combined_text = cleaned[text_key_columns].fillna("").astype(str).agg(" ".join, axis=1)
        total_mask = combined_text.str.contains(r"(?:^|\s)(?:grand\s+total|subtotal|total)(?:$|\s)|合计|总计|小计", case=False, regex=True)
    total_rows = int(total_mask.sum())
    if total_rows:
        cleaned = cleaned.loc[~total_mask].copy()
        issues.append(_issue("Info / 信息", filename, sheet, "Total and subtotal rows removed / 已移除合计及小计行", total_rows, "No action required / 无需处理"))

    metric_columns = [field for field in NUMERIC_FIELDS if field in cleaned]
    if not metric_columns:
        issues.append(_issue("Critical / 严重", filename, sheet, "No recognized finance metrics / 未识别到财务指标", len(cleaned), "Map at least one finance metric / 至少映射一个财务指标"))
    else:
        cleaned = cleaned.loc[cleaned[metric_columns].notna().any(axis=1)].copy()
    invalid_dates = int(cleaned["date"].isna().sum()) if "date" in cleaned else len(cleaned)
    if invalid_dates:
        issues.append(_issue("Critical / 严重", filename, sheet, "Rows without a valid period / 记录缺少有效期间", invalid_dates, "Correct date values before analysis / 分析前修正日期"))
        cleaned = cleaned.loc[cleaned["date"].notna()].copy()

    before_duplicates = len(cleaned)
    duplicate_subset = [field for field in TEXT_FIELDS + NUMERIC_FIELDS if field in cleaned]
    cleaned = cleaned.drop_duplicates(subset=duplicate_subset)
    duplicates = before_duplicates - len(cleaned)
    if duplicates:
        issues.append(_issue("Warning / 警告", filename, sheet, "Exact duplicate rows removed / 已移除完全重复记录", duplicates, "Check repeated exports / 检查是否重复导出"))

    department = _infer_department(f"{filename} {sheet}")
    if "department" not in cleaned:
        cleaned["department"] = department
    else:
        cleaned["department"] = cleaned["department"].fillna(department).astype(str).str.strip().replace("", department)
    defaults = {"sku": "UNSPECIFIED", "product": "Unspecified", "category": "Unspecified", "channel": "Unspecified"}
    for field, default in defaults.items():
        if field not in cleaned:
            cleaned[field] = default
        else:
            cleaned[field] = cleaned[field].fillna(default).astype(str).str.strip().replace("", default)
    for field in NUMERIC_FIELDS:
        if field not in cleaned:
            cleaned[field] = pd.NA
    cleaned["source_file"] = filename
    cleaned["source_sheet"] = sheet
    cleaned["source_department"] = cleaned["department"]
    cleaned["date"] = pd.to_datetime(cleaned["date"]).dt.to_period("M").dt.to_timestamp()

    status = "Ready / 可用"
    if any(issue["Severity / 严重性"].startswith("Critical") for issue in issues):
        status = "Blocked / 阻断"
    elif issues:
        status = "Review / 复核"
    period_label = "n.a."
    if not cleaned.empty:
        period_label = f"{cleaned['date'].min():%Y-%m} to {cleaned['date'].max():%Y-%m}"
    summary = {
        "File / 文件": filename,
        "Sheet / 工作表": sheet,
        "Department / 部门": department,
        "Raw Rows / 原始行": raw_rows,
        "Clean Rows / 清洗后行": len(cleaned),
        "Header Row / 表头行": header_row + 1,
        "Mapped Fields / 已映射字段": ", ".join(sorted(mapped_columns)),
        "Unmapped / 未映射": ", ".join(unmapped[:12]),
        "Period / 期间": period_label,
        "Status / 状态": status,
    }
    return cleaned, summary, issues


@st.cache_data(show_spinner=False)
def ingest_finance_files(file_payloads: tuple[tuple[str, bytes], ...]) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    cleaned_tables: list[pd.DataFrame] = []
    file_count = len(file_payloads)
    for filename, content in file_payloads:
        try:
            tables = _read_tables(filename, content)
        except Exception as exc:
            issues.append(_issue("Critical / 严重", filename, "n.a.", f"File could not be read / 文件无法读取: {exc}", 0, "Check file format or password protection / 检查文件格式或密码保护"))
            summaries.append({"File / 文件": filename, "Sheet / 工作表": "n.a.", "Department / 部门": _infer_department(filename), "Raw Rows / 原始行": 0, "Clean Rows / 清洗后行": 0, "Header Row / 表头行": "n.a.", "Mapped Fields / 已映射字段": "", "Unmapped / 未映射": "", "Period / 期间": "n.a.", "Status / 状态": "Blocked / 阻断"})
            continue
        for sheet, raw in tables:
            cleaned, summary, table_issues = _clean_table(filename, sheet, raw)
            summaries.append(summary)
            issues.extend(table_issues)
            if cleaned is not None and not cleaned.empty:
                cleaned_tables.append(cleaned)

    source_summary = pd.DataFrame(summaries)
    issue_log = pd.DataFrame(issues)
    if not cleaned_tables:
        return {"canonical": pd.DataFrame(), "staging": pd.DataFrame(), "sources": source_summary, "issues": issue_log, "coverage": pd.DataFrame(), "stats": {"files": file_count, "tables": len(summaries), "raw_rows": int(source_summary.get("Raw Rows / 原始行", pd.Series(dtype=float)).sum()), "clean_rows": 0, "analysis_rows": 0, "issues": len(issue_log)}}

    staging = pd.concat(cleaned_tables, ignore_index=True, sort=False)
    # Include source identity: identical values from two departments are not
    # proof that one is a duplicate; source-ownership checks must see both.
    duplicate_subset = [field for field in TEXT_FIELDS + NUMERIC_FIELDS + ["source_file", "source_sheet"] if field in staging]
    global_duplicates = staging.duplicated(subset=duplicate_subset, keep="first")
    if global_duplicates.any():
        issues.append(_issue("Warning / 警告", "Multiple files / 多文件", "n.a.", "Duplicate records found across files / 多文件之间存在重复记录", int(global_duplicates.sum()), "Confirm overlapping exports / 确认是否存在重复导出"))
        staging = staging.loc[~global_duplicates].copy()

    def first_known(series: pd.Series) -> str:
        values = [str(value) for value in series.dropna() if str(value) not in ("", "Unspecified", "UNSPECIFIED")]
        return values[0] if values else "Unspecified"

    # Flow metrics can be summed within a source. Balance snapshots cannot:
    # multiple exports of the same ending inventory must not inflate inventory.
    snapshot_fields = {"inventory_units", "inventory_value"}
    aggregation: dict[str, Any] = {
        field: (lambda values: values.max()) if field in snapshot_fields
        else (lambda values: values.sum(min_count=1))
        for field in NUMERIC_FIELDS
    }
    aggregation.update({"product": first_known, "category": first_known, "source_department": lambda s: ", ".join(sorted(set(map(str, s.dropna())))), "source_file": lambda s: ", ".join(sorted(set(map(str, s.dropna())))), "source_sheet": lambda s: ", ".join(sorted(set(map(str, s.dropna()))))})
    canonical = staging.groupby(KEY_FIELDS, dropna=False, as_index=False).agg(aggregation)
    # A shared metric in different files at the same grain might represent
    # overlapping extracts rather than additive transactions. Fail closed
    # until the source ownership / grain has been explicitly resolved.
    overlapping = []
    for field in NUMERIC_FIELDS:
        populated = staging.loc[staging[field].notna(), KEY_FIELDS + ["source_file"]]
        if populated.empty:
            continue
        source_counts = populated.groupby(KEY_FIELDS, dropna=False)["source_file"].nunique()
        conflict_keys = source_counts[source_counts > 1].index
        if len(conflict_keys):
            overlapping.append((field, conflict_keys))
            conflict_index = pd.MultiIndex.from_frame(canonical[KEY_FIELDS]).isin(conflict_keys)
            canonical.loc[conflict_index, field] = float("nan")
            issues.append(_issue(
                "Critical / 严重", "Combined dataset / 合并数据", "n.a.",
                f"Overlapping source ownership for {field} / {field} 多来源重复归属",
                int(conflict_index.sum()),
                "Resolve source ownership and transaction grain before summing / 先确认指标权威来源和明细粒度",
            ))

    # Finance identities validate the inputs; they are not a substitute for
    # independent GL-to-subledger reconciliation.
    has_revenue_inputs = canonical[["gross_sales", "discount", "returns", "net_revenue"]].notna().all(axis=1)
    revenue_difference = (
        canonical["gross_sales"] - canonical["discount"]
        - canonical["returns"] - canonical["net_revenue"]
    ).abs()
    revenue_mismatch = has_revenue_inputs & (revenue_difference > 0.01)
    if revenue_mismatch.any():
        issues.append(_issue(
            "Critical / 严重", "Combined dataset / 合并数据", "n.a.",
            "Net revenue formula mismatch / 净收入勾稽不一致",
            int(revenue_mismatch.sum()),
            "Review discounts, returns, period and gross-to-net mapping / 核对折扣、退货、期间和收入映射",
        ))
    canonical["analysis_ready"] = canonical[REQUIRED_ANALYSIS_FIELDS].notna().all(axis=1) & ~revenue_mismatch
    canonical["gross_profit"] = pd.NA
    canonical["contribution_profit"] = pd.NA
    ready = canonical["analysis_ready"]
    canonical.loc[ready, "gross_profit"] = canonical.loc[ready, "net_revenue"] - canonical.loc[ready, "product_cost"] - canonical.loc[ready, "freight"] - canonical.loc[ready, "tariff"]
    canonical.loc[ready, "contribution_profit"] = canonical.loc[ready, "gross_profit"] - canonical.loc[ready, "platform_fee"] - canonical.loc[ready, "marketing_spend"]
    canonical["gross_profit"] = pd.to_numeric(canonical["gross_profit"], errors="coerce")
    canonical["contribution_profit"] = pd.to_numeric(canonical["contribution_profit"], errors="coerce")

    incomplete = int((~canonical["analysis_ready"]).sum())
    if incomplete:
        issues.append(_issue("Critical / 严重", "Combined dataset / 合并数据", "n.a.", "Rows missing fields required for profit analysis / 记录缺少利润分析必需字段", incomplete, "Review field coverage and join keys; missing values are not treated as zero / 复核字段覆盖及连接键，缺失值不会按零处理"))
    unspecified_keys = int(((canonical["sku"] == "UNSPECIFIED") | (canonical["channel"] == "Unspecified")).sum())
    if unspecified_keys:
        issues.append(_issue("Warning / 警告", "Combined dataset / 合并数据", "n.a.", "Rows have incomplete SKU or channel keys / 记录缺少 SKU 或渠道连接键", unspecified_keys, "Add common business keys before combining departmental reports / 合并部门报表前补充统一业务键"))
    issue_log = pd.DataFrame(issues)

    coverage_rows = []
    table_count = max(len(cleaned_tables), 1)
    for field in TEXT_FIELDS + NUMERIC_FIELDS:
        sources_with_field = sum(field in table and table[field].notna().any() for table in cleaned_tables)
        non_null = int(staging[field].notna().sum()) if field in staging else 0
        coverage_rows.append({"Field / 字段": field, "Sources / 来源数": sources_with_field, "Source Coverage / 来源覆盖率": sources_with_field / table_count, "Non-null Rows / 非空行": non_null, "Row Coverage / 行覆盖率": non_null / len(staging) if len(staging) else 0})
    coverage = pd.DataFrame(coverage_rows)
    stats = {
        "files": file_count,
        "tables": len(summaries),
        "raw_rows": int(source_summary["Raw Rows / 原始行"].sum()) if not source_summary.empty else 0,
        "clean_rows": len(staging),
        "analysis_rows": int(canonical["analysis_ready"].sum()),
        "issues": len(issue_log),
    }
    return {"canonical": canonical, "staging": staging, "sources": source_summary, "issues": issue_log, "coverage": coverage, "stats": stats}


def demo_pipeline_result(data: pd.DataFrame) -> dict[str, Any]:
    canonical = data.copy()
    canonical["source_file"] = "Built-in demo / 内置演示"
    canonical["source_sheet"] = "Generated fact table / 生成事实表"
    canonical["source_department"] = "Commercial Finance / 商业财务"
    canonical["analysis_ready"] = True
    sources = pd.DataFrame([{"File / 文件": "Built-in demo / 内置演示", "Sheet / 工作表": "Generated fact table / 生成事实表", "Department / 部门": "Commercial Finance / 商业财务", "Raw Rows / 原始行": len(data), "Clean Rows / 清洗后行": len(data), "Header Row / 表头行": 1, "Mapped Fields / 已映射字段": ", ".join(TEXT_FIELDS + NUMERIC_FIELDS), "Unmapped / 未映射": "", "Period / 期间": f"{data['date'].min():%Y-%m} to {data['date'].max():%Y-%m}", "Status / 状态": "Ready / 可用"}])
    coverage = pd.DataFrame([{"Field / 字段": field, "Sources / 来源数": 1, "Source Coverage / 来源覆盖率": 1.0, "Non-null Rows / 非空行": int(data[field].notna().sum()) if field in data else 0, "Row Coverage / 行覆盖率": float(data[field].notna().mean()) if field in data else 0.0} for field in TEXT_FIELDS + NUMERIC_FIELDS])
    return {"canonical": canonical, "staging": canonical.copy(), "sources": sources, "issues": pd.DataFrame(columns=["Severity / 严重性", "Source / 来源", "Sheet / 工作表", "Issue / 问题", "Rows / 行数", "Action / 建议"]), "coverage": coverage, "stats": {"files": 1, "tables": 1, "raw_rows": len(data), "clean_rows": len(data), "analysis_rows": len(data), "issues": 0}}

