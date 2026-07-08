#!/usr/bin/env python
"""
Demo: ทดสอบ Fundamental Filter
แสดงว่าหุ้นไหนผ่าน criteria ทางการเงิน
"""
import pandas as pd
from fundamentals import get_fundamentals, passes_fundamental_filter, format_ratio

# หุ้น sample
symbols = [
    "PIMO.BK", "CPF.BK", "ADVANC.BK", "KTB.BK",
    "AOT.BK", "BEM.BK", "BDMS.BK", "SCGP.BK"
]

# Criteria
criteria = {
    'max_pe': 20,
    'min_roe': 0.15,
    'max_de': 1.0,
    'min_gross_margin': 0.4,
    'min_ebit_margin': 0.10,
    'min_eps_growth': 0.10,
}

print("="*80)
print("FUNDAMENTAL FILTER TEST")
print("="*80)
print(f"\nCriteria:")
print(f"  P/E Ratio < 20")
print(f"  ROE > 15%")
print(f"  D/E Ratio < 1")
print(f"  Gross Margin > 40%")
print(f"  EBIT Margin > 10%")
print(f"  EPS Growth > 10%\n")

rows = []
for sym in symbols:
    print(f"Fetching {sym}...", end=" ", flush=True)
    fund = get_fundamentals(sym)
    if fund and fund.get('pe_ratio'):
        passes = passes_fundamental_filter(fund, criteria)
        status = "PASS" if passes else "FAIL"
        print(status)

        rows.append({
            'Stock': sym.replace('.BK', ''),
            'P/E': format_ratio(fund.get('pe_ratio'), '.2f'),
            'ROE': format_ratio(fund.get('roe'), '.2%'),
            'D/E': format_ratio(fund.get('de_ratio'), '.2f'),
            'Gross M.': format_ratio(fund.get('gross_margin'), '.2%'),
            'EBIT M.': format_ratio(fund.get('ebit_margin'), '.2%'),
            'EPS G.': format_ratio(fund.get('eps_growth'), '.2%'),
            'Pass': 'YES' if passes else 'NO'
        })
    else:
        print("NO DATA")

if rows:
    df = pd.DataFrame(rows)
    print("\n" + "="*80)
    print(df.to_string(index=False))
    print("="*80)
    passes_count = sum(1 for r in rows if r['Pass'] == 'YES')
    print(f"\nSummary: {passes_count}/{len(rows)} stocks passed filter")
else:
    print("No data available")
