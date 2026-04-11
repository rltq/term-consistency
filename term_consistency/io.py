import requests


def load_diff_text(pr_url: str) -> str:
    diff_url = pr_url + ".diff"            # TODO 통신상태 체크 예외처리 필요
    response = requests.get(diff_url)
    if response.status_code == 200:
        return response.text
    else:
        response.raise_for_status()
    # return diff_text


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
