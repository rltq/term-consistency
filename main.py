import os
import sys
import json
import argparse

from term_consistency.io import load_diff_text, create_terms, create_lookup
from term_consistency.parse import parse_diff
from term_consistency.match import find_terms
from term_consistency.format import format_findings


def load_terms(term_kr_url: str, terms_file_path: str = "terms_all.json") -> list:
    if not os.path.exists(terms_file_path):
        all_terms = create_terms(term_kr_url)
        with open(terms_file_path, "w") as f:
            json.dump(all_terms, f, ensure_ascii=False)
    else:
        with open(terms_file_path, "r") as f:
            all_terms = json.load(f)
    all_terms.sort(key=lambda x: len(x["term"]), reverse=True)
    return all_terms


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
