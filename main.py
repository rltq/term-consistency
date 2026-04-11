import os
import sys
import json
import argparse
from urllib.parse import urlparse

from term_consistency.io import load_diff_text, create_terms, create_lookup
from term_consistency.parse import parse_diff
from term_consistency.match import find_terms
from term_consistency.glossary import load_glossary, merge_lookups
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


def extract_repo_id(pr_url: str) -> str:
    """GitHub PR URL → "owner/name" 추출.

    예: https://github.com/PyTorchKorea/tutorials-kr/pull/1056
        → "PyTorchKorea/tutorials-kr"

    GitHub host 가 아니거나 경로가 예상과 다르면 빈 문자열 반환.
    load_glossary 가 빈 문자열에 대해 빈 dict 를 반환하므로 파이프
    라인은 override 없이 terms.kr 만으로 동작한다.
    """
    parsed = urlparse(pr_url)
    if parsed.netloc != "github.com":
        return ""
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


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

    # 레포 override 머지. repo_id 가 매핑에 없으면 load_glossary 가 빈 dict
    # 를 반환하므로 merge_lookups 결과는 terms.kr 과 동등 (단, 모든 meaning
    # 에 _authority="terms.kr" 태그가 부여된다).
    repo_overrides = load_glossary(extract_repo_id(pr_url))
    term_lookup = merge_lookups(repo_overrides, term_lookup)

    segments = parse_diff(diff_text)
    matched, unmatched = find_terms(segments, term_lookup)
    json.dump(unmatched, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)


if __name__ == "__main__":
    main()
