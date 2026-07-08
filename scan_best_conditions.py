#!/usr/bin/env python
"""
CLI tool: Scan SET100 หา best conditions
Usage: python scan_best_conditions.py
"""
import sys
import pandas as pd
from universe import group_symbols
from optimizer import scan_set100


def main():
    # ได้รายชื่อหุ้น SET100
    symbols = group_symbols("SET100 (ทั้งหมด)")
    print(f"Starting scan for {len(symbols)} stocks...")
    print("=" * 80)

    # Scan
    results = scan_set100(symbols)

    if results.empty:
        print("No results found")
        return

    # Save to CSV
    csv_file = "best_conditions.csv"
    results.to_csv(csv_file, index=False)
    print(f"\n✓ Results saved to {csv_file}\n")

    # Display top results
    print("TOP 20 STOCKS BY RETURN:")
    print("=" * 80)
    print(results.head(20).to_string(index=False))

    print("\n" + "=" * 80)
    print(f"Summary: {len(results)} stocks analyzed")
    print(f"  Avg Return: {results['Return%'].mean():.1f}%")
    print(f"  Max Return: {results['Return%'].max():.1f}%")
    print(f"  Min Return: {results['Return%'].min():.1f}%")

    print(f"\nFull results saved to: {csv_file}")


if __name__ == "__main__":
    main()
