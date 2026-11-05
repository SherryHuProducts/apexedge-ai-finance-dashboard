"""Read optional presentation summaries without mixing YTD slices into monthly P&L facts."""
from __future__ import annotations
import io
from pathlib import Path
import pandas as pd


def extract_segment_summaries(filename: str, content: bytes) -> dict[str,pd.DataFrame]:
    if Path(filename).suffix.lower() not in {".xlsx",".xlsm",".xls"}:
        return {}
    excel=pd.ExcelFile(io.BytesIO(content))
    result={}
    channel_name=next((s for s in excel.sheet_names if "channel p&l" in s.lower() or "渠道利润" in s),None)
    if channel_name:
        raw=pd.read_excel(io.BytesIO(content),sheet_name=channel_name,header=None)
        heading=next((i for i in range(len(raw)) if "Line" in str(raw.iat[i,1]) and "项目" in str(raw.iat[i,1])),None)
        if heading is not None:
            names={col:str(raw.iat[heading,col]).split("\n")[0].strip()
                   for col in range(2,raw.shape[1])
                   if pd.notna(raw.iat[heading,col]) and "Total" not in str(raw.iat[heading,col])}
            labels={"Net Sales":"revenue","Contribution Margin":"contribution_profit",
                    "Returns":"returns","Orders":"orders"}
            values={k:{} for k in labels.values()}
            for row in range(heading+1,min(heading+22,len(raw))):
                label=str(raw.iat[row,1])
                for token,key in labels.items():
                    if token in label and key not in values.get("__seen",{}):
                        for col,name in names.items():
                            number=pd.to_numeric(raw.iat[row,col],errors="coerce")
                            if pd.notna(number):values[key][name]=float(number)
                        values.setdefault("__seen",{})[key]=True
            rows=[]
            for name in names.values():
                item={"channel":name}
                item.update({key:dataset.get(name) for key,dataset in values.items() if key!="__seen"})
                if item.get("revenue") is not None:rows.append(item)
            if rows:result["channel"]=pd.DataFrame(rows)
    category_name=next((s for s in excel.sheet_names if "margin-cogs" in s.lower() or "毛利与成本" in s),None)
    if category_name:
        raw=pd.read_excel(io.BytesIO(content),sheet_name=category_name,header=None)
        heading=next((i for i in range(len(raw)) if "Category" in str(raw.iat[i,1]) and "品类" in str(raw.iat[i,1])),None)
        if heading is not None:
            rows=[]
            for i in range(heading+1,min(heading+20,len(raw))):
                label=str(raw.iat[i,1])
                if "分摊" in label or "Allocated" in label:break
                revenue=pd.to_numeric(raw.iat[i,2],errors="coerce")
                gm=pd.to_numeric(raw.iat[i,5],errors="coerce")
                if pd.notna(revenue) and pd.notna(gm):
                    rows.append({"category":label,"revenue":float(revenue),
                                 "product_gross_margin_pct":float(gm)*100})
            if rows:result["category"]=pd.DataFrame(rows)
    return result
