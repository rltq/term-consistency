import os
import re
import json
import argparse

import requests
from unidiff import PatchSet


def create_terms(base_url: str) -> list:
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


def load_diff_text(pr_url: str) -> str:
    diff_url = pr_url + ".diff"            # TODO 통신상태 체크 예외처리 필요
    response = requests.get(diff_url)
    if response.status_code == 200:
        return response.text
    else:
        response.raise_for_status()
    # return diff_text


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


def normalize_ko(text) -> str:
    return text.replace(" ", "")


def strip_text(text) -> str:
    return re.sub(r"`{1,3}[^`]+`{1,3}", "", text)


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
    print(term_kr_url)
    pr_url = args.pr_url  # 'https://github.com/PyTorchKorea/tutorials-kr/pull/1056'
    print(pr_url)
    diff_text = load_diff_text(pr_url)

    # Load terms
    all_terms = load_terms(term_kr_url)
    term_lookup = create_lookup(all_terms)

    ## 파싱 - unidiff 객체
    patch = PatchSet(diff_text)

    # 순회하여 매칭하므로 nested dict 보다는 flat records
    # `#` 로 시작하면 문서주석, 그렇지 않으면 코드
    diffs: list[dict] = []
    for file in patch:
        for hunk in file:       # (idx) hunk.source_start : hunk.source_length
            # print(f"[Source] hunk line no: {hunk.source_start} + {hunk.source_length}")
            # print(f"[Target] hunk line no: {hunk.target_start} + {hunk.target_length}")
            # print()
            
            # for line in hunk:
            #     print(f"[{line.line_type}]" #, Content: {line.value.strip()}, "
            #             f"Old: {line.source_line_no}, New: {line.target_line_no}")
            # # return
            """
            경우의 수가
            old no == new no 같은 위치, 유지
            - is_removed, old 만 존재, new == None
            + is_added, old == None, new 만 존재
            keep 을 기준으로 끊자
            """

            # add, remove, keep 라인 번호가 모두 다르니 line객체를 보존하고 독립적인 idx 사용하여 구분. 
            # 라인 추출 필요할 시 객체에서 추출
            added, removed = '', ''       # kr, en --> 리스트로 묶어야 국소적인 문장단위 비교가 가능
            idx = 1
            for line in hunk:
                if line.is_context:
                    diffs.append(
                        {
                            'idx': idx,
                            'hunk': hunk,
                            'file': file.path,
                            'kr': added,
                            'en':removed,
                        }
                    )
                    # added, removed = [], []       # kr ,en
                    added, removed = '', ''       # kr ,en
                    idx += 1
                elif line.is_added:
                    # added.append(line if line.value.strip().startswith("#") else None)
                    # added.append(line.value.strip() if line.value.strip().startswith("#") else None)
                    added += line.value.strip() if line.value.strip().startswith("#") else ''
                elif line.is_removed:
                    # removed.append(line if line.value.strip().startswith("#") else None)
                    # removed.append(line.value.strip() if line.value.strip().startswith("#") else None)
                    removed += line.value.strip() if line.value.strip().startswith("#") else ''
    matched, unmatched = [], []
    for diff in diffs:
        kr_text, en_text = strip_text(diff["kr"]), strip_text(diff["en"])
        for term in term_lookup.keys():
            term = strip_text(term)
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            brace_pattern = re.compile(
                r"[가-힣]+\(" + re.escape(term) + r"\)", re.IGNORECASE
            )
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
                    
                    en_review, kr_review = "", ""
                    if term in en_text and not term in kr_text:
                        en_review = en_text
                        kr_review =kr_text
                    else:
                        kr_review = "[ERR] " +''.join( kr_text )
                        
                    unmatched.append(
                        {
                            "file": diff["file"],
                            "origin": term,
                            "expected": allowed,
                            "review_en": en_review,
                            "review_kr": kr_review,
                            "hunks": (en_text, kr_text),
                        }
                    )

    # 검토용 출력
    # for items in matched:
    #     for k, v in items.items():
    #         if k == "file": print(f"\n{k} -> {v}")
    #         elif k == "origin": print(f"{k} -> {v}")
    #         elif k == "expected": print(f"{k} -> {v}")
    #         elif k == "matched" or "matched(brace)":
    #             print(f"{k}\n\t{v}")

    # print("*"*50)

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
