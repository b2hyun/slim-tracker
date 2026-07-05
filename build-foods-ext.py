#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
식약처 "전국통합식품영양성분정보" CSV → foods-ext.json 변환기.

앱(index.html)은 같은 폴더에 foods-ext.json이 있으면 자동으로 읽어
검색 DB에 합칩니다. 서버 불필요 · 오프라인 동작.

사용법:
    1) 공공데이터포털(data.go.kr)에서 "전국통합식품영양성분정보" CSV 다운로드
       (음식 DB / 가공식품 DB 여러 개를 한꺼번에 넘겨도 됩니다)
    2) python3 build-foods-ext.py 파일1.csv 파일2.csv ...
    3) 생성된 foods-ext.json 을 index.html 과 같은 폴더에 커밋 → 배포

컬럼명은 데이터셋마다 조금씩 달라서 흔한 이름들을 자동 인식합니다.
필요하면 아래 CANDIDATES 를 수정하세요.
"""
import csv, json, sys, re, io

# 컬럼 후보 (부분 일치, 우선순위 순)
CANDIDATES = {
    "name":    ["식품명", "제품명", "식품이름", "name"],
    "kcal":    ["에너지(kcal)", "에너지", "열량(kcal)", "열량", "kcal"],
    "protein": ["단백질(g)", "단백질", "protein"],
    "fat":     ["지방(g)", "지방", "fat"],
    "carb":    ["탄수화물(g)", "탄수화물", "carbohydrate", "carb"],
    "serving": ["1회제공량", "영양성분함량기준량", "식품중량", "기준량", "serving"],
}

def pick(header, keys):
    for want in keys:
        for i, h in enumerate(header):
            if want.replace(" ", "") in (h or "").replace(" ", ""):
                return i
    return -1

def to_num(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

def serving_grams(s):
    """'100g 당' 같은 기준량에서 g/ml 수치 추출 (없으면 100)."""
    if not s:
        return 100.0
    m = re.search(r"(\d+(\.\d+)?)\s*(g|ml)", str(s))
    return float(m.group(1)) if m else 100.0

def open_csv(path):
    # 한글 CSV는 보통 cp949 또는 utf-8-sig
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.reader(f))
        except (UnicodeDecodeError, LookupError):
            continue
    raise SystemExit("인코딩을 인식하지 못했어요: " + path)

def round_n(v):
    v = round(v, 1)
    return int(v) if v == int(v) else v

def main(paths):
    seen, out = set(), []
    for path in paths:
        rows = open_csv(path)
        if not rows:
            continue
        header = rows[0]
        idx = {k: pick(header, v) for k, v in CANDIDATES.items()}
        if idx["name"] < 0 or idx["kcal"] < 0:
            print("!! 식품명/에너지 컬럼을 못 찾음, 건너뜀:", path, file=sys.stderr)
            print("   헤더:", header, file=sys.stderr)
            continue
        for r in rows[1:]:
            if len(r) <= idx["name"]:
                continue
            name = (r[idx["name"]] or "").strip()
            kcal = to_num(r[idx["kcal"]]) if idx["kcal"] < len(r) else None
            if not name or kcal is None:
                continue
            g = serving_grams(r[idx["serving"]]) if idx["serving"] >= 0 and idx["serving"] < len(r) else 100.0
            def per(k):
                v = to_num(r[idx[k]]) if idx[k] >= 0 and idx[k] < len(r) else None
                return v if v is not None else 0.0
            # 값들은 보통 "기준량(g)당" → 그대로 사용
            item = {
                "n": name[:40],
                "u": (str(int(g)) + "g") if g and g != 100 else "100g",
                "p": round_n(per("protein")),
                "c": round_n(kcal),
                "f": round_n(per("fat")),
                "b": round_n(per("carb")),
            }
            key = item["n"] + "|" + str(item["c"])
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    with io.open("foods-ext.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("foods-ext.json 생성 완료:", len(out), "개 항목")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
