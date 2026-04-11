import re


# v0.x: synonyms 를 매칭에 포함할지. 현재 False (SCOPE 제외 6 — terms.kr
# 운영자 의사 미확인). True 로 바꾸면 meanings[i].synonyms 가 allowed 에
# 동등 권위로 포함됨.
INCLUDE_SYNONYMS = False


def normalize_ko(text) -> str:
    return text.replace(" ", "")


def strip_text(text) -> str:
    return re.sub(r"`{1,3}[^`]+`{1,3}", "", text)


def find_terms(
    segments: list[dict], term_lookup: dict
) -> tuple[list[dict], list[dict]]:
    matched, unmatched = [], []
    for diff in segments:
        kr_text, en_text = strip_text(diff["kr"]), strip_text(diff["en"])
        for term in term_lookup.keys():
            term = strip_text(term)
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            brace_pattern = re.compile(
                r"[가-힣]+\(" + re.escape(term) + r"\)", re.IGNORECASE
            )
            if pattern.search(en_text):
                # allowed: 용어집 원문 형태 — 출력용 (expected 필드). 사람 읽기 기준.
                # allowed_normalized: 공백 제거 형태 — 비교용. 한국어 본문이
                # normalize_ko 로 공백 제거되므로 포함 비교 대칭을 위해 필요.
                meanings = term_lookup[term]
                allowed = [meaning["korean"] for meaning in meanings]
                if INCLUDE_SYNONYMS:
                    for m in meanings:
                        allowed.extend(m.get("synonyms", []))
                allowed_normalized = [normalize_ko(k) for k in allowed]
                if brace_pattern.search(kr_text):
                    matched.append(
                        {
                            "file": diff["file"],
                            "origin": term,
                            "expected": allowed,
                            "matched(brace)": (en_text, kr_text),
                        }
                    )
                elif any(a in normalize_ko(kr_text) for a in allowed_normalized):
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

                    # en 에는 토큰이 있음 (위 pattern.search 통과). kr 에 기대 번역어가
                    # 없는 상태에서 원인을 두 종류로 구분:
                    #   1) 영문 토큰이 한국어 본문에 그대로 박힘 → 번역 누락, [ERR] 라벨
                    #   2) 그 외 → 일반 unmatched (en/kr 동시 노출하여 사람 판단)
                    # \b 는 x+와 같이 한글이 바로 붙은 경우 경계가 안 생겨 매칭을
                    # 놓친다 ("Softmax와", "ReLU 및"). ASCII 글자 인접만 차단하는
                    # 전용 경계로 누설을 탐지.
                    leak_pattern = re.compile(
                        r"(?<![a-zA-Z])" + re.escape(term) + r"(?![a-zA-Z])",
                        re.IGNORECASE,
                    )
                    en_review = en_text
                    kr_review = (
                        "[ERR] " + kr_text
                        if leak_pattern.search(kr_text)
                        else kr_text
                    )

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
    return matched, unmatched
