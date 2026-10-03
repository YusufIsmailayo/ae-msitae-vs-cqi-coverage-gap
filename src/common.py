"""Shared paths and parsers for the MSitAE vs CQI coverage-gap pipeline.

I keep the parsing here so the notebooks stay readable and every notebook
reads the same Bronze files in the same way.
"""
from pathlib import Path
import glob
import hashlib

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BRONZE = ROOT / "data" / "bronze"
SILVER = ROOT / "data" / "silver"
GOLD = ROOT / "data" / "gold"
for _p in (SILVER, GOLD, GOLD / "charts"):
    _p.mkdir(parents=True, exist_ok=True)

MSITAE_TABLES = BRONZE / "ae" / "AE2526_ECDS_MSitAE_Tables.xlsx"
CQI_CSV = BRONZE / "ae" / "AE2526_CQI_Open_Data_AR.csv"
OP_REPORT = BRONZE / "op" / "hosp-epis-stat-outp-rep-tabs-2025-26-tab.xlsx"
OP_AGE_GENDER = BRONZE / "op" / "hosp-epis-stat-outp-all-firs-atte-2025-26-data.csv"

# Monthly sitrep column positions are fixed across the 12 files (checked in notebook 02).
ATT_COLS = ["att_t1", "att_t2", "att_other"]
BOOKED_COLS = ["bkd_t1", "bkd_t2", "bkd_other"]
OVER4_COLS = ["over4_t1", "over4_t2", "over4_other"]
OVER4_BOOKED_COLS = ["over4_bkd_t1", "over4_bkd_t2", "over4_bkd_other"]
_RENAME = dict(zip(
    ["A&E attendances Type 1", "A&E attendances Type 2", "A&E attendances Other A&E Department",
     "A&E attendances Booked Appointments Type 1", "A&E attendances Booked Appointments Type 2",
     "A&E attendances Booked Appointments Other Department",
     "Attendances over 4hrs Type 1", "Attendances over 4hrs Type 2", "Attendances over 4hrs Other Department",
     "Attendances over 4hrs Booked Appointments Type 1", "Attendances over 4hrs Booked Appointments Type 2",
     "Attendances over 4hrs Booked Appointments Other Department"],
    ATT_COLS + BOOKED_COLS + OVER4_COLS + OVER4_BOOKED_COLS))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_msitae_monthly(folder: str = "msitae_monthly") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (provider-month rows, each file's own TOTAL row) for the CSVs in a Bronze folder."""
    frames = []
    for f in sorted(glob.glob(str(BRONZE / folder / "*.csv"))):
        d = pd.read_csv(f)
        period = d.loc[d["Org Code"].astype(str).str.strip() != "TOTAL", "Period"].iloc[0]
        d["month"] = pd.to_datetime(period.replace("MSitAE-", "").title(), format="%B-%Y").strftime("%Y-%m")
        d["source_file"] = Path(f).name
        frames.append(d)
    d = pd.concat(frames, ignore_index=True).rename(columns=_RENAME)
    d = d.rename(columns={"Org Code": "org_code", "Parent Org": "parent_org", "Org name": "org_name"})
    for c in list(_RENAME.values()):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["org_code"] = d["org_code"].astype(str).str.strip()
    keep = ["month", "org_code", "parent_org", "org_name", "source_file"] + ATT_COLS + BOOKED_COLS + OVER4_COLS + OVER4_BOOKED_COLS
    # The TOTAL row is identified by Org Code, not by Period: the February file labels it with a normal period.
    return d.loc[d.org_code != "TOTAL", keep].reset_index(drop=True), d.loc[d.org_code == "TOTAL", keep].reset_index(drop=True)


def read_cqi() -> pd.DataFrame:
    d = pd.read_csv(CQI_CSV)
    d.columns = [c.lower() for c in d.columns]
    d = d.rename(columns={"attendance_month": "month"})
    d["suppressed"] = d["suppression"].eq("Y")
    return d.drop(columns="suppression")


def _table(sheet: str, header_label: str, ncols: int | None = None) -> pd.DataFrame:
    raw = pd.read_excel(MSITAE_TABLES, sheet_name=sheet, header=None)
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq(header_label)][0]
    t = raw.iloc[hdr + 1:].copy()
    t.columns = raw.iloc[hdr].tolist()
    return t.dropna(how="all")


def read_msitae_table1() -> pd.DataFrame:
    """Annual MSitAE attendances (Table 1). Row label is blank in the source, so I take the numeric row."""
    raw = pd.read_excel(MSITAE_TABLES, sheet_name="Table 1", header=None)
    hdr = raw.index[raw.iloc[:, 1].astype(str).str.match(r"^\d{4}-\d{2}$")][0]
    years = raw.iloc[hdr, 1:].dropna().tolist()
    vals = raw.iloc[hdr + 1, 1:1 + len(years)].tolist()
    return pd.DataFrame({"year": years, "attendances": pd.to_numeric(vals)})


def read_msitae_table3() -> pd.DataFrame:
    raw = pd.read_excel(MSITAE_TABLES, sheet_name="Table 3", header=None)
    hdr = raw.index[raw.iloc[:, 1].astype(str).str.match(r"^\d{4}-\d{2}$")][0]
    t = raw.iloc[hdr:].dropna(how="all").set_index(0).T.reset_index(drop=True)
    t.columns = ["year", "le4", "gt4", "total", "pct_le4", "standard"]
    t = t.assign(**{c: pd.to_numeric(t[c], errors="coerce") for c in t.columns[1:]})
    return t


def read_msitae_table6() -> pd.DataFrame:
    """Provider-level Type 1 only (121 providers). I check that against Table 11 in the gate."""
    t = _table("Table 6", "Provider code").iloc[:, :6]
    t.columns = ["org_code", "org_name", "attendances", "le4", "gt4", "pct_le4"]
    t = t[t.org_code.astype(str).str.fullmatch(r"[A-Z0-9]{3,5}")].copy()
    for c in ["attendances", "le4", "gt4", "pct_le4"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")
    return t.reset_index(drop=True)


def read_msitae_table11() -> pd.DataFrame:
    raw = pd.read_excel(MSITAE_TABLES, sheet_name="Table 11", header=None)
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip().eq("A&E Department Type")][0]
    yr_row = raw.iloc[hdr - 1]
    last = yr_row.last_valid_index()           # final year block = 2025-26
    t = raw.iloc[hdr + 1:hdr + 5, [0, last, last + 1, last + 2]].copy()
    t.columns = ["dept_type", "ecds", "msitae", "ecds_pct_of_msitae"]
    t.insert(0, "year", yr_row[last])
    for c in t.columns[2:]:
        t[c] = pd.to_numeric(t[c])
    return t.reset_index(drop=True)


def read_op_summary1() -> pd.DataFrame:
    x = pd.read_excel(OP_REPORT, sheet_name="Summary Report 1", header=7).iloc[:11, :7]
    x.columns = ["year", "attendances", "dnas", "patient_cancellations", "hospital_cancellations", "unknown", "total"]
    for c in x.columns[1:]:
        x[c] = pd.to_numeric(x[c])
    return x


ECDS_NATIONAL = BRONZE / "ae" / "AE2526_ECDS_National_Data_Tables.xlsx"


def read_ecds_imd() -> pd.DataFrame:
    """IMD decile rows from the ECDS National Report Tables, 'Demographics' sheet (annual rows only)."""
    d = pd.read_excel(ECDS_NATIONAL, sheet_name="Demographics", header=None).iloc[10:].copy()
    d.columns = ["period", "demographic_type", "group", "attendances", "population", "rate_per_100k"]
    d = d[(d.demographic_type == "Imd_Decile") & d.period.astype(str).str.contains("/")].copy()
    for col in ["attendances", "population", "rate_per_100k"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    return d.drop(columns="demographic_type").reset_index(drop=True)
