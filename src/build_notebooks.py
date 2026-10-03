"""Generates the five notebooks. Run once; the notebooks themselves are the deliverable."""
import nbformat as nbf
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "notebooks"
HEAD = "import sys\nsys.path.insert(0, '../src')\nimport pandas as pd\nimport numpy as np\nimport common as c\npd.options.display.float_format = '{:,.4f}'.format\npd.options.display.width = 200\n"


def build(name, cells):
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.cells = [nbf.v4.new_markdown_cell(t) if k == "md" else nbf.v4.new_code_cell(t) for k, t in cells]
    nbf.write(nb, NB / name)


# ---------------------------------------------------------------- 01
build("01_bronze_manifest.ipynb", [
    ("md", "# 01 Bronze manifest\nI keep every downloaded file untouched and record a SHA-256 for each, so that anyone can later prove which bytes this analysis used. Nothing is transformed here."),
    ("code", HEAD + "from datetime import datetime, timezone"),
    ("code", """# The URLs I downloaded from. The monthly sitrep URLs are in urls.txt, written when I downloaded them.
urls = {
    'AE2526_CQI_Open_Data_AR.csv': 'https://files.digital.nhs.uk/96/785BF6/AE2526_CQI_Open_Data_AR.csv',
    'AE2526_ECDS_MSitAE_Tables.xlsx': 'https://files.digital.nhs.uk/08/D5507A/AE2526_ECDS_MSitAE_Tables.xlsx',
    'AE_2526_Metadata.xlsx': 'https://files.digital.nhs.uk/D2/087EB2/AE_2526_Metadata.xlsx',
    'hosp-epis-stat-outp-rep-tabs-2025-26-tab.xlsx': 'https://files.digital.nhs.uk/3A/DC44DE/hosp-epis-stat-outp-rep-tabs-2025-26-tab.xlsx',
    'hosp-epis-stat-outp-all-firs-atte-2025-26-data.csv': 'https://files.digital.nhs.uk/BC/881240/hosp-epis-stat-outp-all-firs-atte-2025-26-data.csv',
    'hosp-epis-stat-outp-eth-imd-dec-2025-26-data.csv': 'https://files.digital.nhs.uk/41/3F7E90/hosp-epis-stat-outp-eth-imd-dec-2025-26-data.csv',
    'AE2526_ECDS_Summary_Report_Tables.xlsx': 'https://files.digital.nhs.uk/36/B35E68/AE2526_ECDS_Summary_Report_Tables.xlsx',
    'AE2526_ECDS_National_Data_Tables.xlsx': 'https://files.digital.nhs.uk/70/666D19/AE2526_ECDS_National_Data_Tables.xlsx',
    'hosp-epis-stat-outp-meta-2025-26-tab.xlsx': 'https://files.digital.nhs.uk/15/578BB6/hosp-epis-stat-outp-meta-2025-26-tab.xlsx',
}
for line in (c.BRONZE / 'msitae_monthly' / 'urls.txt').read_text().split():
    urls[line.rsplit('/', 1)[-1]] = line
# Provisional files came from the Internet Archive; I record the capture timestamp in the URL itself.
for line in (c.BRONZE / 'msitae_provisional' / 'archive_sources.tsv').read_text().splitlines():
    name, stamp, url = line.split('\t'); urls[name] = url

rows = []
for p in sorted(c.BRONZE.rglob('*')):
    if p.is_file() and p.suffix in {'.csv', '.xls', '.xlsx'}:
        rows.append({'file': str(p.relative_to(c.BRONZE)), 'bytes': p.stat().st_size, 'sha256': c.sha256(p),
                     'source_url': urls.get(p.name),
                     'file_mtime_utc': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec='seconds')})
manifest = pd.DataFrame(rows)
manifest"""),
    ("code", """# I want to know about any file I cannot trace back to a URL, so I check rather than assume.
untraced = manifest[manifest.source_url.isna()]
print(f'{len(manifest)} files; {len(untraced)} without a recorded source URL')
manifest.to_parquet(c.BRONZE / 'manifest.parquet', index=False)"""),
])

# ---------------------------------------------------------------- 02
build("02_silver_tables.ipynb", [
    ("md", "# 02 Silver tables\nI parse each Bronze file into a typed table and check it against itself before anything is compared across files."),
    ("code", HEAD),
    ("code", """monthly, monthly_totals = c.read_msitae_monthly()
print(monthly.shape, monthly.month.nunique(), 'months;', monthly.groupby('month').org_code.nunique().min(), 'to', monthly.groupby('month').org_code.nunique().max(), 'providers per month')
# Internal check: provider rows must sum to the TOTAL row that each file carries. I expect zero everywhere.
cols = c.ATT_COLS + c.BOOKED_COLS + c.OVER4_COLS + c.OVER4_BOOKED_COLS
chk = monthly.groupby('month')[cols].sum() - monthly_totals.set_index('month')[cols]
print('max absolute difference between provider rows and file TOTAL row:', int(chk.abs().max().max()))
assert chk.abs().max().max() == 0"""),
    ("code", """cqi = c.read_cqi()
print(cqi.shape, cqi.month.nunique(), 'months', cqi.org_code.nunique(), 'orgs', cqi.suppressed.sum(), 'suppressed rows')
# Internal check: CQI provider rows should sum to its own ENG row. I look at the MSitAE and ECDS counts only.
for m in ['AEQI011', 'AEQI012']:
    s = cqi[cqi.measure_id == m]
    print(m, 'ENG', s[s.org_code == 'ENG'].measure_value.sum(), 'providers', s[s.org_code != 'ENG'].measure_value.sum())"""),
    ("code", """t1, t3, t6, t11, op1 = c.read_msitae_table1(), c.read_msitae_table3(), c.read_msitae_table6(), c.read_msitae_table11(), c.read_op_summary1()
print(len(t1), 'years in Table 1;', len(t3), 'in Table 3;', len(t6), 'providers in Table 6;', len(op1), 'years in outpatient Summary Report 1')
t11"""),
    ("code", """out = {'msitae_monthly_provider': monthly, 'msitae_monthly_totals': monthly_totals, 'cqi_long': cqi,
       'msitae_table1_attendances': t1, 'msitae_table3_four_hour': t3, 'msitae_table6_type1_provider': t6,
       'msitae_table11_dept_type': t11, 'op_summary1_appointments': op1}
for name, df in out.items():
    df.to_parquet(c.SILVER / f'{name}.parquet', index=False)
    print(f'{name:34s}{len(df):>8,d} rows')"""),
])

# ---------------------------------------------------------------- 03
build("03_reconciliation_gate.ipynb", [
    ("md", """# 03 Reconciliation gate
Before I derive anything new I rebuild the published annual figures from my own monthly tables, and I publish the residual rather than tidy it away.

I report **two definitions** because the first one I tried did not reconcile. The report-table text says planned attendances are excluded, but the published numbers only reconcile once booked-appointment attendances are included. I keep both rows in the output so the difference stays visible."""),
    ("code", HEAD),
    ("code", """m = pd.read_parquet(c.SILVER / 'msitae_monthly_provider.parquet')
t1 = pd.read_parquet(c.SILVER / 'msitae_table1_attendances.parquet').set_index('year')
t3 = pd.read_parquet(c.SILVER / 'msitae_table3_four_hour.parquet').set_index('year')
t6 = pd.read_parquet(c.SILVER / 'msitae_table6_type1_provider.parquet')
t11 = pd.read_parquet(c.SILVER / 'msitae_table11_dept_type.parquet').set_index('dept_type')

def rebuild(include_booked):
    att = m[c.ATT_COLS].sum()
    over = m[c.OVER4_COLS].sum()
    if include_booked:
        att = att + m[c.BOOKED_COLS].sum().set_axis(c.ATT_COLS)
        over = over + m[c.OVER4_BOOKED_COLS].sum().set_axis(c.OVER4_COLS)
    return att, over

rows = []
for label, inc in [('non-booked only', False), ('non-booked + booked', True)]:
    att, over = rebuild(inc)
    pub_type = {'att_t1': t11.msitae.iloc[0], 'att_t2': t11.msitae.iloc[1], 'att_other': t11.msitae.iloc[2]}
    rows += [('attendances, all types', label, att.sum(), t1.loc['2025-26', 'attendances']),
             ('four-hour %', label, 100 * (1 - over.sum() / att.sum()), 100 * t3.loc['2025-26', 'pct_le4'])]
    rows += [(f'attendances, {k}', label, att[k], v) for k, v in pub_type.items()]
gate = pd.DataFrame(rows, columns=['metric', 'definition', 'rebuilt', 'published'])
gate['residual'] = gate.rebuilt - gate.published
gate['residual_pct'] = 100 * gate.residual / gate.published
gate"""),
    ("code", """# Provider-level check: Table 6 is Type 1 only, so I compare it with my Type 1 column, with and without booked.
t1_by_org = m.groupby('org_code')[['att_t1', 'bkd_t1']].sum()
j = t6.set_index('org_code').join(t1_by_org, how='left')
j['resid_non_booked'] = j.attendances - j.att_t1
j['resid_with_booked'] = j.attendances - (j.att_t1 + j.bkd_t1)
prov = pd.DataFrame({'definition': ['non-booked only', 'non-booked + booked'],
                     'providers': len(j),
                     'exact_matches': [(j.resid_non_booked == 0).sum(), (j.resid_with_booked == 0).sum()],
                     'sum_abs_residual': [j.resid_non_booked.abs().sum(), j.resid_with_booked.abs().sum()]})
prov"""),
    ("code", """# I write the residuals out whether or not the gate passes, then decide.
DECLARED = 'non-booked + booked'
gate.to_parquet(c.GOLD / 'gate_residuals.parquet', index=False)
prov.to_parquet(c.GOLD / 'gate_provider_residuals.parquet', index=False)
declared = gate[gate.definition == DECLARED]
print('residuals under the declared definition:'); print(declared[['metric', 'residual']].to_string(index=False))
assert (declared.residual.abs() < 1e-6).all(), 'The gate failed: I should not derive anything new until this is explained.'
assert prov.loc[prov.definition == DECLARED, 'exact_matches'].iloc[0] == len(j)
print('Gate passed under', DECLARED)"""),
])

# ---------------------------------------------------------------- 04
build("04_coverage_gap.ipynb", [
    ("md", """# 04 The coverage gap between the MSitAE report tables and the CQI open data
The footnote says the MSitAE report tables account for revisions and may differ slightly from CQI. I test what actually differs. CQI publishes no four-hour measure, so the comparison is on attendances (AEQI012) and on the scope of providers; the four-hour effect is **my calculation**, not a published figure."""),
    ("code", HEAD + "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt"),
    ("code", """m = pd.read_parquet(c.SILVER / 'msitae_monthly_provider.parquet')
cqi = pd.read_parquet(c.SILVER / 'cqi_long.parquet')
t11 = pd.read_parquet(c.SILVER / 'msitae_table11_dept_type.parquet').set_index('dept_type')
t3 = pd.read_parquet(c.SILVER / 'msitae_table3_four_hour.parquet').set_index('year')
m['att'] = m[c.ATT_COLS].sum(axis=1) + m[c.BOOKED_COLS].sum(axis=1)
m['over4'] = m[c.OVER4_COLS].sum(axis=1) + m[c.OVER4_BOOKED_COLS].sum(axis=1)   # booked included, as the gate showed
cq = cqi[(cqi.measure_id == 'AEQI012') & (cqi.org_code != 'ENG')].rename(columns={'measure_value': 'cqi_att'})[['month', 'org_code', 'cqi_att']]
cq = cq[cq.cqi_att > 0]"""),
    ("md", "## 1. Monthly totals: sitrep against CQI"),
    ("code", """sitrep_m = m.groupby('month').att.sum()
cqi_m = cqi[(cqi.measure_id == 'AEQI012') & (cqi.org_code == 'ENG')].set_index('month').measure_value
monthly = pd.DataFrame({'sitrep_all_providers': sitrep_m, 'cqi_msitae': cqi_m})
monthly['omitted_by_cqi'] = monthly.sitrep_all_providers - monthly.cqi_msitae
monthly['omitted_pct'] = 100 * monthly.omitted_by_cqi / monthly.sitrep_all_providers
print(monthly.round(3).to_string()); print('annual omitted:', int(monthly.omitted_by_cqi.sum()), f'({100*monthly.omitted_by_cqi.sum()/monthly.sitrep_all_providers.sum():.2f}%)')"""),
    ("md", "## 2. Where CQI overlaps with the sitrep, how different is it?\nI test every provider-month, not just the totals."),
    ("code", """j = m[['month', 'org_code', 'org_name', 'att', 'over4']].merge(cq, on=['month', 'org_code'], how='left')
shared = j[j.cqi_att.notna()]
print('provider-months in sitrep with activity:', int((j.att > 0).sum()), '| present in CQI:', len(shared))
print('exact matches among shared provider-months:', int((shared.att == shared.cqi_att).sum()), 'of', len(shared))
print('largest absolute difference among shared:', int((shared.att - shared.cqi_att).abs().max()))"""),
    ("md", "## 3. The providers CQI leaves out"),
    ("code", """annual = j.groupby(['org_code']).agg(org_name=('org_name', 'first'), att=('att', 'sum'), over4=('over4', 'sum'), in_cqi=('cqi_att', lambda s: s.notna().any()))
omitted = annual[(~annual.in_cqi) & (annual.att > 0)].copy()
omitted['four_hour_pct'] = 100 * (1 - omitted.over4 / omitted.att)
omitted = omitted.sort_values('att', ascending=False).reset_index()
print(len(omitted), 'providers with activity omitted; attendances', int(omitted.att.sum()))
omitted.head(12)"""),
    ("md", """## 4. Is it a code mismatch?
CQI also lists organisations with ECDS attendances but no MSitAE count. I test whether the omitted sitrep codes are children of those codes by prefix. I expect a partial match at best, and I report what I find."""),
    ("code", """w = cqi[cqi.org_code != 'ENG'].pivot_table(index='org_code', columns='measure_id', values='measure_value', aggfunc='sum')[['AEQI011', 'AEQI012']].fillna(0)
orphans = w[(w.AEQI012 == 0) & (w.AEQI011 > 0)]
print('CQI orgs:', len(w), '| all with ECDS > 0:', bool((w.AEQI011 > 0).all()), '| ECDS-only orgs:', len(orphans), 'with ECDS attendances', int(orphans.AEQI011.sum()))
def parent(code):
    for n in (5, 4, 3):
        if code[:n] != code and code[:n] in orphans.index:
            return code[:n]
omitted['cqi_parent'] = omitted.org_code.map(parent)
hit = omitted[omitted.cqi_parent.notna()]
print(f'{len(hit)} of {len(omitted)} omitted providers share a code prefix with a CQI ECDS-only organisation, covering {int(hit.att.sum()):,} of {int(omitted.att.sum()):,} attendances')
cmp_ = hit.groupby('cqi_parent').att.sum().rename('sitrep_att').to_frame().join(orphans.AEQI011.rename('cqi_ecds'))
cmp_['ecds_over_sitrep'] = cmp_.cqi_ecds / cmp_.sitrep_att
cmp_"""),
    ("md", "## 5. What the omission does to the numbers people quote"),
    ("code", """inc_orgs = set(cq.org_code)
m['in_cqi'] = m.org_code.isin(inc_orgs)
def perf(df): return 100 * (1 - df.over4.sum() / df.att.sum())
scope = pd.DataFrame({'all_providers': m.groupby('month').apply(perf, include_groups=False),
                      'cqi_providers_only': m[m.in_cqi].groupby('month').apply(perf, include_groups=False)})
scope['difference_pp'] = scope.cqi_providers_only - scope.all_providers
annual_all, annual_cqi = perf(m), perf(m[m.in_cqi])
print(f'annual four-hour %: all providers {annual_all:.4f} (published {100*t3.loc["2025-26","pct_le4"]:.4f}) | CQI providers only {annual_cqi:.4f} | difference {annual_cqi-annual_all:.3f} pp')
ecds = cqi[(cqi.measure_id == 'AEQI011') & (cqi.org_code == 'ENG')].measure_value.sum()
cov = pd.DataFrame({'source': ['CQI (AEQI011 / AEQI012, my calculation)', 'Report Table 11'],
                    'ecds': [ecds, t11.ecds.iloc[3]], 'msitae': [monthly.cqi_msitae.sum(), t11.msitae.iloc[3]]})
cov['ecds_pct_of_msitae'] = 100 * cov.ecds / cov.msitae
scope.round(3), cov"""),
    ("code", """monthly.reset_index().to_parquet(c.GOLD / 'coverage_gap_monthly.parquet', index=False)
omitted.to_parquet(c.GOLD / 'omitted_providers.parquet', index=False)
scope.reset_index().to_parquet(c.GOLD / 'four_hour_scope_effect_monthly.parquet', index=False)
cov.to_parquet(c.GOLD / 'ecds_coverage_ratio.parquet', index=False)"""),
    ("md", "## The chart\nOne axis, two lines, one reference rule. The y-axis is truncated to make a 0.7-point gap visible, so the axis range is labelled in the subtitle."),
    ("code", """BLUE, ORANGE, INK, MUTED, GRID, SURFACE = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURFACE); ax.set_facecolor(SURFACE)
x = np.arange(len(scope)); labels = pd.to_datetime(scope.index).strftime('%b\\n%y')
ax.plot(x, scope.all_providers, color=BLUE, lw=2, marker='o', ms=5, mec=SURFACE, mew=1.5, label=f'All {m[m.att>0].org_code.nunique()} providers (report-table scope)')
ax.plot(x, scope.cqi_providers_only, color=ORANGE, lw=2, ls='--', marker='s', ms=5, mec=SURFACE, mew=1.5, label=f'{len(inc_orgs)} providers present in CQI')
ax.axhline(74.9, color=MUTED, lw=1, ls=':'); ax.text(8.5, 74.9 + 0.1, 'annual 74.9% (report tables)', ha='center', va='bottom', fontsize=9, color=MUTED)
ax.text(x[-1] + 0.15, scope.all_providers.iloc[-1], 'all providers', color=INK, va='center', fontsize=9)
ax.text(x[-1] + 0.15, scope.cqi_providers_only.iloc[-1] - 0.1, 'CQI providers', color=INK, va='center', fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9, color=MUTED); ax.set_ylim(71, 77.5); ax.set_xlim(-0.4, len(x) + 0.9)
ax.set_ylabel('% of attendances within four hours (axis starts at 71%)', fontsize=9, color=MUTED); ax.tick_params(colors=MUTED, length=0)
ax.grid(axis='y', color=GRID, lw=0.8); [s.set_visible(False) for s in ax.spines.values()]
ax.legend(frameon=False, loc='lower left', fontsize=9, labelcolor=INK)
fig.text(0.07, 0.96, 'Leaving out urgent care sites lowers four-hour performance\\nby about 0.7 points in every month', fontsize=12, fontweight='bold', color=INK, ha='left', va='top')
fig.text(0.07, 0.885, 'England A&E 2025-26. CQI has no four-hour measure; the orange line is my recalculation on CQI\\'s provider set.', fontsize=9, color=MUTED, ha='left', va='top')
fig.subplots_adjust(top=0.82, left=0.1, right=0.97, bottom=0.12)
fig.savefig(c.GOLD / 'charts' / 'four_hour_scope_effect.png', dpi=160, facecolor=SURFACE)
plt.show()"""),
])

# ---------------------------------------------------------------- 05
build("05_dna_rebuild.ipynb", [
    ("md", "# 05 Did-not-attend rebuild\nI rebuild the DNA claims from the Hospital Outpatient Activity report table, test them under three denominators, and cross-check the CSV against the report table."),
    ("code", HEAD),
    ("code", """op = pd.read_parquet(c.SILVER / 'op_summary1_appointments.parquet').set_index('year')
# Components must sum to the published total in every year.
comp = op[['attendances', 'dnas', 'patient_cancellations', 'hospital_cancellations', 'unknown']].sum(axis=1) - op.total
print('max |components - total|:', comp.abs().max()); assert comp.abs().max() == 0"""),
    ("code", """a, b, o = op.loc['2025-26'], op.loc['2024-25'], op.loc['2019-20']
pc = lambda x, y: 100 * (x / y - 1)
claims = pd.DataFrame([
    ('appointments vs 2024-25 (%)', 2.9, pc(a.total, b.total)),
    ('appointments vs 2019-20 (%)', 20.3, pc(a.total, o.total)),
    ('DNAs vs 2024-25 (%)', 0.1, pc(a.dnas, b.dnas)),
    ('DNAs vs 2019-20 (%)', 5.9, pc(a.dnas, o.dnas)),
    ('DNA rate 2025-26 (%)', 5.4, 100 * a.dnas / a.total),
    ('DNA rate 2019-20 (%)', 6.2, 100 * o.dnas / o.total)], columns=['claim', 'stated', 'rebuilt'])
claims['agrees_at_stated_precision'] = (claims.rebuilt.round(1) == claims.stated)
claims"""),
    ("code", """rates = pd.DataFrame({'dna_rate_all_appointments': 100 * op.dnas / op.total,
                      'dna_rate_attended_or_dna': 100 * op.dnas / (op.attendances + op.dnas),
                      'dna_rate_excluding_unknown': 100 * op.dnas / (op.total - op.unknown)})
rates.round(3)"""),
    ("code", """# What the DNA count would have been at an earlier rate, on this year's volume.
cf = pd.Series({'at 2019-20 rate': o.dnas / o.total * a.total, 'at 2024-25 rate': b.dnas / b.total * a.total, 'actual': a.dnas})
print(cf.round(0).astype(int).to_string()); print('fewer DNAs than at the 2019-20 rate:', int(cf['at 2019-20 rate'] - a.dnas))
below = [y for y in op.index if rates.dna_rate_all_appointments[y] < rates.dna_rate_all_appointments['2019-20']]
print('years with a lower rate than 2019-20:', below)"""),
    ("code", """# Cross-check: the CSV's all-genders age bands should sum to the report table's attendances.
csv = pd.read_csv(c.OP_AGE_GENDER)
ag = csv[(csv.MAINSPEF_CODE == 'All') & csv.MEASURE.str.endswith('All Genders')]
xc = ag.groupby('MEASURE_TYPE').MEASURE_VALUE.sum()
print(xc.to_string()); print('report table attendances:', int(a.attendances))
assert xc['All Attendances by Age and Gender'] == a.attendances"""),
    ("code", """claims.to_parquet(c.GOLD / 'dna_claims_rebuilt.parquet', index=False)
rates.reset_index().to_parquet(c.GOLD / 'dna_rate_by_denominator.parquet', index=False)"""),
])

# ---------------------------------------------------------------- 06
build("06_provisional_vs_final.ipynb", [
    ("md", """# 06 First-published against final monthly sitrep
The footnote implies the report tables absorb revisions while CQI does not. The direct test is to compare each month's first-published sitrep with its final revised version, and then ask which of the two CQI agrees with.

I can only test months whose original file I could retrieve from the Internet Archive: April, May, June, October, November and December 2025. July to September and March 2026 originals were not captured, the January 2026 download failed, and February was never revised. I say so rather than fill the gaps."""),
    ("code", HEAD),
    ("code", """final, _ = c.read_msitae_monthly('msitae_monthly')
prov, prov_tot = c.read_msitae_monthly('msitae_provisional')
cqi = c.read_cqi()
src = pd.read_csv(c.BRONZE / 'msitae_provisional' / 'archive_sources.tsv', sep='\\t', header=None, names=['file', 'archive_timestamp', 'url'])
for d in (final, prov):
    d['att'] = d[c.ATT_COLS + c.BOOKED_COLS].sum(axis=1)
    d['over4'] = d[c.OVER4_COLS + c.OVER4_BOOKED_COLS].sum(axis=1)
# The provisional December file writes its total row as 'TOTAL ' with a trailing space; read_msitae_monthly strips it, so I check.
print('provisional provider rows sum to their own TOTAL row:', int((prov.groupby('month')[c.ATT_COLS + c.BOOKED_COLS].sum() - prov_tot.set_index('month')[c.ATT_COLS + c.BOOKED_COLS]).abs().max().max()) == 0)
src[['file', 'archive_timestamp']]"""),
    ("code", """cq = cqi[(cqi.measure_id == 'AEQI012') & (cqi.org_code != 'ENG')].set_index(['month', 'org_code']).measure_value
rows, changed = [], []
for mth in sorted(prov.month.unique()):
    p = prov[prov.month == mth].set_index('org_code'); f = final[final.month == mth].set_index('org_code')
    j = p[['org_name', 'att', 'over4']].join(f[['att', 'over4']], lsuffix='_prov', rsuffix='_final', how='outer').fillna({'att_prov': 0, 'att_final': 0, 'over4_prov': 0, 'over4_final': 0})
    j['cqi'] = [cq.get((mth, o)) for o in j.index]
    j['revision'] = j.att_final - j.att_prov
    sh = j[j.cqi.notna()]
    rows.append({'month': mth, 'provisional_total': j.att_prov.sum(), 'final_total': j.att_final.sum(), 'revision': j.revision.sum(),
                 'revision_pct': 100 * j.revision.sum() / j.att_prov.sum(), 'providers_revised': int((j.revision != 0).sum()),
                 'four_hour_prov': 100 * (1 - j.over4_prov.sum() / j.att_prov.sum()), 'four_hour_final': 100 * (1 - j.over4_final.sum() / j.att_final.sum()),
                 'cqi_providers': len(sh), 'cqi_equals_final': int((sh.cqi == sh.att_final).sum()), 'cqi_equals_prov': int((sh.cqi == sh.att_prov).sum()),
                 'revised_providers_where_cqi_equals_final': int(((sh.revision != 0) & (sh.cqi == sh.att_final)).sum()),
                 'revised_providers_in_cqi': int((sh.revision != 0).sum())})
    changed.append(j[j.revision != 0].assign(month=mth).reset_index())
res = pd.DataFrame(rows); res['four_hour_change_pp'] = res.four_hour_final - res.four_hour_prov
res.round(3).T"""),
    ("code", """revised = pd.concat(changed, ignore_index=True)[['month', 'org_code', 'org_name', 'att_prov', 'att_final', 'revision', 'cqi']]
print('revised provider-months:', len(revised), '| total revision across the six months:', int(revised.revision.sum()))
revised"""),
    ("code", """# The sharp test: for a provider whose attendances were revised AND that CQI includes, does CQI carry the old or the new number?
inc = revised[revised.cqi.notna()]
print('revised providers that CQI includes:', len(inc), '| CQI equals FINAL:', int((inc.cqi == inc.att_final).sum()), '| CQI equals PROVISIONAL:', int((inc.cqi == inc.att_prov).sum()))
print('all CQI provider-months in these six months: equals final', int(res.cqi_equals_final.sum()), 'of', int(res.cqi_providers.sum()), '| equals provisional', int(res.cqi_equals_prov.sum()))"""),
    ("code", """res.to_parquet(c.GOLD / 'provisional_vs_final_monthly.parquet', index=False)
revised.to_parquet(c.GOLD / 'provisional_vs_final_revised_providers.parquet', index=False)"""),
])

# ---------------------------------------------------------------- 07
build("07_deprivation_ratio.ipynb", [
    ("md", """# 07 The 1.85x deprivation ratio
The release says A&E attendance rates for the most deprived areas were 1.85 times those of the least deprived (source: ECDS). I rebuild it from the ECDS National Report Tables. The 13.6 MB workbook is not in the repository; if it is absent this notebook reads the small Silver table it wrote the first time, and says so."""),
    ("code", HEAD),
    ("code", """if c.ECDS_NATIONAL.exists():
    imd = c.read_ecds_imd(); imd.to_parquet(c.SILVER / 'ecds_imd_decile.parquet', index=False); print('read from Bronze workbook')
else:
    imd = pd.read_parquet(c.SILVER / 'ecds_imd_decile.parquet'); print('Bronze workbook not present; read the committed Silver table')
imd[imd.period == '2025/26']"""),
    ("code", """# Internal check: the ten deciles plus the unknown-IMD attendances must sum to the published total.
cur = imd[imd.period == '2025/26'].set_index('group')
deciles = cur.drop(['Unknown', 'IMD_DECILE_TOTAL'])
print('deciles + unknown =', int(deciles.attendances.sum() + cur.loc['Unknown', 'attendances']), '| published total', int(cur.loc['IMD_DECILE_TOTAL', 'attendances']))
assert deciles.attendances.sum() + cur.loc['Unknown', 'attendances'] == cur.loc['IMD_DECILE_TOTAL', 'attendances']
print('unknown-IMD share of attendances: %.2f%%' % (100 * cur.loc['Unknown', 'attendances'] / cur.loc['IMD_DECILE_TOTAL', 'attendances']))
print('rate rises at every step from least to most deprived:', deciles.rate_per_100k.is_monotonic_increasing)"""),
    ("code", """rows = []
for yr, g in imd.groupby('period'):
    g = g.set_index('group'); mo, le = g.loc['Most deprived 10%'], g.loc['Least deprived 10%']
    rows.append({'year': yr, 'most_attendances': mo.attendances, 'least_attendances': le.attendances,
                 'most_population': mo.population, 'least_population': le.population,
                 'ratio_published_rates': mo.rate_per_100k / le.rate_per_100k,
                 'ratio_rebuilt_from_counts': (mo.attendances / mo.population) / (le.attendances / le.population),
                 'ratio_of_raw_counts': mo.attendances / le.attendances})
ratio = pd.DataFrame(rows)
ratio.round(4)"""),
    ("code", """# The gate for this notebook: the published statement is 1.85, and I expect to reproduce it from the counts as well as the rates.
r = ratio.set_index('year').loc['2025/26']
print('published-rate ratio %.4f | rebuilt from counts %.4f' % (r.ratio_published_rates, r.ratio_rebuilt_from_counts))
assert round(r.ratio_published_rates, 2) == 1.85 and abs(r.ratio_published_rates - r.ratio_rebuilt_from_counts) < 1e-3"""),
    ("md", "## The 2025/26 population update\nThe decile populations changed in 2025/26, so part of the apparent fall from 2024/25 is a denominator effect. I hold the populations constant in each direction to see how much."),
    ("code", """a, b = ratio.set_index('year').loc['2024/25'], ratio.set_index('year').loc['2025/26']
def rr(att_m, pop_m, att_l, pop_l): return (att_m / pop_m) / (att_l / pop_l)
sens = pd.Series({
    '2024/25 counts, 2024/25 populations': rr(a.most_attendances, a.most_population, a.least_attendances, a.least_population),
    '2024/25 counts, 2025/26 populations': rr(a.most_attendances, b.most_population, a.least_attendances, b.least_population),
    '2025/26 counts, 2024/25 populations': rr(b.most_attendances, a.most_population, b.least_attendances, a.least_population),
    '2025/26 counts, 2025/26 populations': rr(b.most_attendances, b.most_population, b.least_attendances, b.least_population)})
sens.round(4)"""),
    ("code", """# The outpatient file uses the same IMD populations; I confirm that rather than assume it.
op5 = pd.read_excel(c.OP_REPORT, sheet_name='Summary Report 5', header=7).iloc[:10]
op_pop = op5.set_index(op5.columns[0])['National population per IMD decile']
print('most deprived  ECDS', int(b.most_population), '| outpatient', int(op_pop['Most deprived 10%']))
print('least deprived ECDS', int(b.least_population), '| outpatient', int(op_pop['Less deprived 10%']))
assert b.most_population == op_pop['Most deprived 10%'] and b.least_population == op_pop['Less deprived 10%']"""),
    ("code", """ratio.to_parquet(c.GOLD / 'deprivation_ratio_by_year.parquet', index=False)
sens.rename('ratio').reset_index().rename(columns={'index': 'scenario'}).to_parquet(c.GOLD / 'deprivation_ratio_population_sensitivity.parquet', index=False)"""),
])
print('built')
