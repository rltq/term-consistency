import os
import re
import json
import argparse

import requests
from unidiff import PatchSet

parser = argparse.ArgumentParser()
parser.add_argument("-pr", "--pr-url", type=str, dest="pr_url", default = "") 
parser.add_argument(
    "-term",
    "--term-url",
    type=str,
    dest="term_url",
    default="https://poc.terms.kr/data/",
)

args = parser.parse_args()

def create_terms(base_url: str = args.term_url) -> list:
    # Create term list
    index = requests.get(base_url + "index.json").json()  # ["a.json", "b.json", ...]
    all_terms = []
    for filename in index:
        terms = requests.get(base_url + filename).json()  # 각 파일이 리스트
        all_terms.extend(terms)
    all_terms.sort(key=lambda x: len(x["term"]), reverse=True)

    return all_terms


def create_lookup(all_terms: list) -> dict:
    term_lookup = {}
    for entry in all_terms:
        term_lookup[entry["term"].lower()] = entry["meanings"]

    return term_lookup


def load_diff_text(pr_url: str = args.pr_url) -> str:
    diff_url = pr_url + ".diff"
    diff_text = requests.get(diff_url).text
    return diff_text


def normalize_ko(text) -> str:
    return text.replace(" ", "")


def strip_text(text) -> str:
    return re.sub(r"`{1,3}[^`]+`{1,3}", "", text)


def main():
    term_kr_url = args.term_url  # args 기본값으로
    pr_url = args.pr_url  # 'https://github.com/PyTorchKorea/tutorials-kr/pull/1056'
    diff_text = load_diff_text(pr_url)

    # Load terms
    # terms_all.json 이 없으면 load - 로컬환경용
    if not "terms_all.json" in os.listdir(os.getcwd()):
        all_terms = create_terms(term_kr_url)
        with open("terms_all.json", "w") as f:
            json.dump(all_terms, f, ensure_ascii=False)
    else:
        with open("terms_all.json", "r") as f:
            all_terms = json.load(f)
    all_terms.sort(key=lambda x: len(x["term"]), reverse=True)
    term_lookup = create_lookup(all_terms)

    ## 파싱 - unidiff 객체
    patch = PatchSet(diff_text)
    # 순회하여 매칭하므로 nested dict 보다는 flat records
    # `#` 로 시작하면 문서주석, 그렇지 않으면 코드
    diffs: list[dict] = []
    for file in patch:
        for idx, hunk in enumerate(file):
            kr_text = " ".join(
                [
                    line.value.strip()
                    for line in hunk
                    if line.is_added and line.value.strip().startswith("#")
                ]
            )  # is_added
            en_text = " ".join(
                [
                    line.value.strip()
                    for line in hunk
                    if line.is_removed and line.value.strip().startswith("#")
                ]
            )  # is_removed
            diffs.append(
                {
                    "file": file.path,
                    "idx": idx,
                    "en": en_text,
                    "kr": kr_text,
                }
            )

    matched, unmatched = [], []
    for diff in diffs:
        for term in term_lookup.keys():
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            brace_pattern = re.compile(
                r"[가-힣]+\(" + re.escape(term) + r"\)", re.IGNORECASE
            )
            kr_text, en_text = strip_text(diff["kr"]), strip_text(diff["en"])
            if pattern.search(en_text):
                # 용어집: korean="요구 사항", synonyms=["필수 요건"]
                # 허용 목록: ["요구사항", "필수요건"]  (공백 제거 후)
                meanings = term_lookup[term]
                allowed = [meaning["korean"] for meaning in meanings]  # 공백제거 전
                if brace_pattern.search(kr_text):
                    matched.append(
                        {
                            "file": diff["file"],
                            "origin": term,
                            "expected": allowed,
                            "matched(brace)": (en_text, kr_text),
                        }
                    )
                elif any(a in normalize_ko(kr_text) for a in allowed):
                    matched.append(
                        {
                            "file": diff["file"],
                            "origin": term,
                            "expected": allowed,
                            "matched": (en_text, kr_text),
                        }
                    )
                elif len(kr_text) > 0:  # 하드코딩 : 조건 분기 후에 조정
                    # 반환: 현재 / 변경 / 근거 이렇게 최소 세개
                    # 한국어까지 번역매칭을 하는건 비효율적. 번역어를 교정해야하는데 번역어가 어떻게 다르게 들어갔을지 알 방법 X. 
                    # 한 문장을 여러 문장으로 분절해 번역하는 경우도 있어 Idx 기반 탐색 효율 X
                    en_diff_lines = en_text.split("#")
                    en_review_sentences, kr_review_sentences = "", ""
                    for diff_line in en_diff_lines:
                        if term in diff_line:
                            en_review_sentences = diff_line
                    for diff_line in kr_text.split("#"):
                        if term in diff_line:
                            kr_review_sentences = diff_line
                        else:
                            kr_review_sentences = "[ERR] " + diff_line

                    unmatched.append(
                        {
                            "file": diff["file"],
                            "origin": term,
                            "expected": allowed,
                            "review_en": en_review_sentences,
                            "review_kr": kr_review_sentences,
                            "hunks": (en_text, kr_text),
                        }
                    )

    # 검토용 출력
    for items in matched:
        for k, v in items.items():
            if k == "file": print(f"\n{k} -> {v}")
            elif k == "origin": print(f"{k} -> {v}")
            elif k == "expected": print(f"{k} -> {v}")
            elif k == "matched" or "matched(brace)":
                print(f"{k}\n\t{v}")
    
    print("*"*50)

    for items in unmatched:
        for k, v in items.items():
            if k == "file":
                print(f"\n{k} -> {v}")
            elif k == "origin":
                print(f"{k} -> {v}")
            elif k == "expected":
                print(f"{k} -> {v}")
            elif k == "review_en":
                print(f"{k} ==> {v}")
            elif k == "review_kr":
                print(f"{k} ==> {v}")


if __name__ == "__main__":
    main()
