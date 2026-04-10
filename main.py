import os
import re
from collections import defaultdict

import requests
from unidiff import PatchSet
import json

"""
# poc.terms.kr 데이터 구조

```json
{
  "term": "attention",
  "meanings": [
    {
      "korean": "어텐션",
      "definition": "입력 시퀀스의 각 요소에 서로 다른 가중치를 부여하여 중요한 정보에 집중하는 메커니즘",
      "examples": [
        {
          "en": "The Transformer model uses a self-attention mechanism.",
          "ko": "트랜스포머 모델은 셀프 어텐션 메커니즘을 사용한다."
        }
      ],
      "synonyms": ["주의 메커니즘", "집중 메커니즘"]
    }
  ]
}
```
"""

def load_terms(base_url:str):
    index = requests.get(base_url + "index.json").json()  # ["a.json", "b.json", ...]
    all_terms = []
    for filename in index:
        terms = requests.get(base_url + filename).json()  # 각 파일이 리스트
        all_terms.extend(terms)
    return all_terms

def create_lookup(all_terms:list):
    term_lookup = {}
    for entry in all_terms:
        term_lookup[entry["term"].lower()] = entry["meanings"]
    return term_lookup

def normalize_ko(text):
    return text.replace(" ", "")

def strip_text(text):
    return re.sub(r'`{1,3}[^`]+`{1,3}', '', text)

def main():
    # Load terms
    base_url = "https://poc.terms.kr/data/"

    # if - terms_all.json 이 없으면
    if not 'terms_all.json' in os.listdir(os.getcwd()):
        all_terms = load_terms(base_url)
        with open("terms_all.json", "w") as f:
            json.dump(all_terms, f, ensure_ascii=False)
    else:
        with open("terms_all.json", "r") as f:
            all_terms = json.load(f)

    # 내림차순 정렬. 긴 term부터 정렬하여 activation function -> activation 둘을 헷갈리지 않을 수 있다.
    all_terms.sort(key=lambda x: len(x["term"]), reverse=True) 
    term_lookup = create_lookup(all_terms)

    pr_url = "https://github.com/PyTorchKorea/tutorials-kr/pull/1059"
    # pr_url = 'https://github.com/PyTorchKorea/tutorials-kr/pull/1056'
    diff_url = pr_url + '.diff'
    diff_text = requests.get(diff_url).text
    
    ## unidiff 객체
    patch = PatchSet(diff_text)
    # 순회하여 매칭하므로 nested dict 보다는 flat records
    # `#` 로 시작하면 문서주석, 그렇지 않으면 코드
    diffs = []
    for file in patch:
        for idx, hunk in enumerate(file):
            kr_text = " ".join(
                [line.value.strip() for line in hunk
                    if line.is_added and line.value.strip().startswith("#")]
            )
            en_text = " ".join(
                [line.value.strip() for line in hunk
                    if line.is_removed and line.value.strip().startswith("#")]
            )
            diffs.append (
                {
                    "file": file.path,
                    "idx": idx,
                    "en": en_text,
                    "kr": kr_text,
                }
            )

    matched = []
    unmatched = []
    for diff in diffs:      # list[dict]
        for term in all_terms:
            pattern = re.compile(r'\b' + re.escape(term['term']) + r'\b', re.IGNORECASE)
            brace_pattern = re.compile(r'[가-힣]+\(' + re.escape(term['term']) + r'\)', re.IGNORECASE)
            kr_text, en_text = strip_text(diff['kr']), strip_text(diff['en'])
            if pattern.search(en_text):
                # 이 용어가 영문에 있으면 한국어 검사
                # 용어집: korean="요구 사항", synonyms=["필수 요건"]
                # 허용 목록: ["요구사항", "필수요건"]  (공백 제거 후)
                allowed = []
                # "동일한 용어가 여러 도메인에서 다른 의미로 사용될 때, 각각의 정의를 명확히 구분하여 제공합니다"
                # 위에 근거하여 meanings 항목의 길이가 변동될 수 있다. 예: loss 
                # {
                #     "term": "loss", 
                #     "meanings": [
                #         {
                #             "korean": "손실", "definition": "모델의 예측값과 실제값 사이의 차이를 수치화한 값", 
                #             "examples": [ ... ], "synonyms": ["손실값", "오차"]
                #         }, 
                #         {
                #             "korean": "로스", "definition": "정보나 성능의 감소 또는 저하", 
                #              "examples": [], "synonyms": ["손실", "감소"]
                #         }]
                # }
                for meaning in term["meanings"]:
                    allowed.append(normalize_ko(meaning["korean"]))
                
                #############
                # ---- 정규식 --- #
                #############
                if brace_pattern.search(kr_text):
                    matched.append(
                            {
                                "file": diff["file"],
                                "origin": term['term'],
                                "expected": allowed,
                                # "matched(brace)": diff['kr'], 
                                "matched(brace)": kr_text
                            }
                        )
                elif any(a in normalize_ko(kr_text) for a in allowed):
                    matched.append(
                            {
                                "file": diff["file"],
                                "origin": term['term'],
                                "expected": allowed,
                                # "matched": diff['kr'], 
                                "matched": kr_text
                            }
                        )
                elif len(kr_text) > 0:      # 하드코딩 : 조건 분기 후에 조정
                    # 반환: 현재 / 변경 / 근거 이렇게 최소 세개
                    unmatched.append(
                        {
                            "file": diff["file"],
                            "origin": term['term'],
                            "expected": allowed,
                            # "unmatched": diff['kr'], 
                            "unmatched": (en_text, kr_text)
                        }
                    )
                    # break
            # break

    # 검토용 출력
    # for items in matched:
    #     for k, v in items.items():
    #         if k == "file": print(f"\n{k} -> {v}")
    #         elif k == "origin": print(f"{k} -> {v}")
    #         elif k == "expected": print(f"{k} -> {v}")
    #         elif k == "matched" or "matched(brace)":
    #             print(f"{k}\n\t{v}")
    # print("*"*50)
    # for items in unmatched:
    #     for k, v in items.items():
    #         if k == "file": print(f"\n{k} -> {v}")
    #         elif k == "origin": print(f"{k} -> {v}")
    #         elif k == "expected": print(f"{k} -> {v}")
    #         elif k == "unmatched":
    #             print(f"{k}\n\t{v[0]}\n\t{v[1]}")

if __name__ == "__main__":
    main()
