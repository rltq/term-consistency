def format_findings(matched: list[dict], unmatched: list[dict]) -> str:
    # 검토용 출력
    # for items in matched:
    #     for k, v in items.items():
    #         if k == "file": print(f"\n{k} -> {v}")
    #         elif k == "origin": print(f"{k} -> {v}")
    #         elif k == "expected": print(f"{k} -> {v}")
    #         elif k == "matched" or "matched(brace)":
    #             print(f"{k}\n\t{v}")

    # print("*"*50)

    parts: list[str] = []
    for items in unmatched:
        for k, v in items.items():
            if k == "file":
                parts.append(f"\n{k} -> {v}\n")
            elif k == "origin":
                parts.append(f"{k} -> {v}\n")
            elif k == "expected":
                parts.append(f"{k} -> {v}\n")
            elif k == "review_en":
                parts.append(f"{k} ==> {v}\n")
            elif k == "review_kr":
                parts.append(f"{k} ==> {v}\n")
    return "".join(parts)
