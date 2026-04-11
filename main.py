import os
import sys
import json
import argparse

from term_consistency.io import load_diff_text, create_terms, create_lookup
from term_consistency.parse import parse_diff
from term_consistency.match import find_terms
from term_consistency.format import format_findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=str, dest="pr_url")
    parser.add_argument(
        "--term",
        type=str,
        dest="term_url",
        default="https://poc.terms.kr/data/",
    )
    args = parser.parse_args()

    term_kr_url = args.term_url  # args 기본값으로
    print(term_kr_url, file=sys.stderr)
    pr_url = args.pr_url  # 'https://github.com/PyTorchKorea/tutorials-kr/pull/1056'
    print(pr_url, file=sys.stderr)
    diff_text = load_diff_text(pr_url)

    # Load terms
    all_terms = load_terms(term_kr_url)
    term_lookup = create_lookup(all_terms)

    segments = parse_diff(diff_text)
    matched, unmatched = find_terms(segments, term_lookup)
    print(format_findings(matched, unmatched), end="")


if __name__ == "__main__":
    main()
