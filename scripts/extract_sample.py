"""Extract reduced sample from full GLPI export."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.ingest.normalize import extract_sample, load_glpi_excel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to Tickets_Consolidados.xlsx")
    parser.add_argument("-o", "--output", default="data/raw/sample_extracted.parquet")
    args = parser.parse_args()

    df = load_glpi_excel(args.input)
    sample = extract_sample(df)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_parquet(out, index=False)
    print(f"Extraídos {len(sample)} tickets → {out}")


if __name__ == "__main__":
    main()
