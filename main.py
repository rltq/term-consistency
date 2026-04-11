import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
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


def extract_pr_number(pr_url: str) -> int:
    """GitHub PR URL → pull 번호 (int). 실패 시 0.

    extract_repo_id 와 쌍을 이루는 헬퍼. write_log 가 pr_number 로 출력
    파일명을 결정한다. 잘못된 입력에 크래시하지 않고 0 을 돌려줘야
    파이프라인이 fallback 경로 (log/pr_0.json) 로 안전하게 흐른다.
    """
    parsed = urlparse(pr_url)
    if parsed.netloc != "github.com":
        return 0
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 4 and parts[2] == "pull":
        try:
            return int(parts[3])
        except ValueError:
            return 0
    return 0


def get_tool_sha() -> str:
    """현재 HEAD 의 short sha. git 호출 실패 시 "unknown".

    수검토 중 "이 JSON 은 어느 코드 버전이 만든거지?" 질문에 답하기 위해
    런타임에 기록. 박제는 의미 없으므로 fallback 은 플레이스홀더.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def write_log(
    pr_url: str,
    repo_id: str,
    pr_number: int,
    matched: list[dict],
    unmatched: list[dict],
    log_dir: str = "log",
) -> Path:
    """log/pr_<N>.json 생성 — 수검토용 스냅샷.

    **툴링 레이어.** 기존 stdout 덤프 (`json.dump(unmatched, sys.stdout, ...)`)
    는 그대로 두고 파이프라인 말미에 부가적으로 파일도 남긴다. 회귀 픽스처
    테스트 (`tests/test_regression.py`) 가 `capsys` 로 stdout 을 읽어 스냅샷
    비교하므로 stdout 커플링은 건드리지 않는다.

    수검토용이라 matched/unmatched 둘 다 담는다 (false-negative 를 사람이
    눈으로 짚을 수 있도록). 엔트리에 pr_number + github_file_url 을 덧붙여
    여러 PR 로그를 합쳐 grep 하거나 파일 경로를 바로 클릭해서 소스로 점프할
    수 있게 한다. github_file_url 은 `blob/HEAD` 를 쓰므로 GitHub 가 기본
    브랜치로 리다이렉트한다 (PR head sha 를 몰라도 동작).
    """
    def enrich(items: list[dict]) -> list[dict]:
        enriched = []
        for item in items:
            e = dict(item)
            e["pr_number"] = pr_number
            file_path = item.get("file", "")
            e["github_file_url"] = (
                f"https://github.com/{repo_id}/blob/HEAD/{file_path}"
                if file_path
                else ""
            )
            enriched.append(e)
        return enriched

    payload = {
        "pr_url": pr_url,
        "pr_number": pr_number,
        "repo_id": repo_id,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "tool_sha": get_tool_sha(),
        "counts": {"matched": len(matched), "unmatched": len(unmatched)},
        "matched": enrich(matched),
        "unmatched": enrich(unmatched),
    }

    Path(log_dir).mkdir(exist_ok=True)
    out_path = Path(log_dir) / f"pr_{pr_number}.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


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

    # 툴링: 수검토용 스냅샷을 추가로 파일에 남긴다. stdout 덤프는 위에서
    # 그대로 유지 — 회귀 픽스처 테스트가 capsys 로 읽는 커플링을 깨지 않음.
    write_log(
        pr_url=pr_url,
        repo_id=extract_repo_id(pr_url),
        pr_number=extract_pr_number(pr_url),
        matched=matched,
        unmatched=unmatched,
    )


if __name__ == "__main__":
    main()
