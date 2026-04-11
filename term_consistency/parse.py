from unidiff import PatchSet


def parse_diff(diff_text: str) -> list[dict]:
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
                            'en': removed,
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
    return diffs
