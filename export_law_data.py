"""
law.xlsx 엑셀 파일을 분석하여 프론트엔드 UI용 마스터 데이터(JSON)를 생성
- Row-by-Row 상태 머신(State Machine) 알고리즘 적용
- 불규칙한 엑셀 데이터를 완벽하게 처리
"""
import json
import re
import pandas as pd


def extract_number_for_sort(text):
    """자연 정렬을 위한 숫자 추출 (제1조 -> 1, 제10조 -> 10)"""
    if pd.isna(text) or text == '':
        return float('inf')
    match = re.search(r'(\d+)', str(text))
    return int(match.group(1)) if match else float('inf')


def convert_paragraph_num_to_circle(num):
    """항번호를 원문자로 변환 (1 -> ①, 2 -> ②, ...)"""
    if pd.isna(num) or num == '':
        return ''

    circle_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    if str(num) in circle_numbers:
        return str(num)

    try:
        n = int(float(num))
        if 1 <= n <= 20:
            return circle_numbers[n - 1]
        return f"({n})"
    except (ValueError, TypeError):
        return str(num) if num else ''


def format_ho_number(num):
    """호번호 포맷팅 (1 -> '1.', 1.0 -> '1.')"""
    if pd.isna(num) or num == '':
        return ''
    try:
        n = int(float(num))
        return f"{n}."
    except (ValueError, TypeError):
        return str(num)


def safe_str(val):
    """NaN을 빈 문자열로 변환"""
    if pd.isna(val):
        return ''
    return str(val).strip()


def normalize_dataframe(df):
    """
    데이터프레임 정규화
    - 컬럼명 공백 제거
    - 필수 컬럼 확인 및 생성
    - 결측치 처리
    """
    # 컬럼명 공백 제거
    df.columns = [str(col).strip() for col in df.columns]

    # 필수 컬럼 목록
    required_cols = ['조번호', '조제목', '항번호', '항내용', '호번호', '호내용']

    # 없는 컬럼은 빈 문자열로 생성
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''

    # 조번호, 조제목 ffill (병합 셀 대응)
    df['조번호'] = df['조번호'].ffill()
    df['조제목'] = df['조제목'].ffill()

    # 항번호 ffill - 단, 조번호가 바뀔 때는 리셋
    df['_prev_조번호'] = df['조번호'].shift(1)
    df['_조_changed'] = df['조번호'] != df['_prev_조번호']

    # 조가 바뀌는 지점에서 항번호를 NaN으로 마킹하여 ffill이 넘어가지 않게 함
    current_para = None
    para_list = []
    prev_jo = None

    for idx, row in df.iterrows():
        jo = row['조번호']
        para = row['항번호']

        # 조가 바뀌면 항번호 상태 리셋
        if jo != prev_jo:
            current_para = para if pd.notna(para) and para != '' else None
        else:
            # 같은 조 내에서 항번호가 있으면 업데이트
            if pd.notna(para) and para != '':
                current_para = para

        para_list.append(current_para)
        prev_jo = jo

    df['항번호_filled'] = para_list

    # 텍스트 컬럼 NaN -> 빈 문자열
    text_cols = ['항내용', '호내용', '조제목']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('')

    # 임시 컬럼 제거
    df = df.drop(columns=['_prev_조번호', '_조_changed'], errors='ignore')

    return df


def process_sheet_with_state_machine(df, sheet_name):
    """
    Row-by-Row 상태 머신으로 데이터 처리

    상태 변수:
    - current_article: 현재 처리 중인 조
    - current_paragraph: 현재 처리 중인 항
    - prev_para_content: 이전 행의 항내용 (중복 방지용)
    """
    result = {}

    # 상태 변수 초기화
    current_article = None
    current_para_num = None
    prev_para_content = None

    # 조별 데이터 저장 (조 키 -> 항 목록)
    articles_data = {}

    for row in df.itertuples(index=False):
        # 현재 행 데이터 추출
        jo_num = safe_str(getattr(row, '조번호', ''))
        jo_title = safe_str(getattr(row, '조제목', ''))
        para_num = getattr(row, '항번호_filled', None)
        para_content = safe_str(getattr(row, '항내용', ''))
        ho_num = getattr(row, '호번호', None)
        ho_content = safe_str(getattr(row, '호내용', ''))

        # 조 키 생성
        if jo_num:
            if jo_title:
                article_key = f"{jo_num} ({jo_title})"
            else:
                article_key = jo_num
        else:
            # 조번호가 없는 시트 (별표 등)
            article_key = "일반 조항"

        # 새로운 조 감지
        if article_key != current_article:
            current_article = article_key
            current_para_num = None
            prev_para_content = None

            if article_key not in articles_data:
                articles_data[article_key] = {}

        # 항 처리
        para_num_str = safe_str(para_num) if para_num is not None else ''

        # 새로운 항 시작 감지
        if para_num_str and para_num_str != current_para_num:
            current_para_num = para_num_str
            prev_para_content = None

            # 새 항 생성
            circle_num = convert_paragraph_num_to_circle(para_num)
            if para_content:
                content = f"{circle_num} {para_content}" if circle_num else para_content
            else:
                content = f"{circle_num}" if circle_num else ''

            if current_para_num not in articles_data[article_key]:
                articles_data[article_key][current_para_num] = {
                    'no': circle_num,
                    'content': content,
                    'sort_key': extract_number_for_sort(para_num)
                }

            prev_para_content = para_content

        # 같은 항 내에서 호 추가 (Case B)
        elif para_num_str and para_num_str == current_para_num:
            # 호 내용 추가
            if ho_num is not None and safe_str(ho_num) and ho_content:
                ho_formatted = format_ho_number(ho_num)
                ho_text = f"  {ho_formatted} {ho_content}"

                if current_para_num in articles_data[article_key]:
                    existing = articles_data[article_key][current_para_num]['content']
                    # 중복 방지: 동일한 호 내용이 이미 있으면 추가하지 않음
                    if ho_text not in existing:
                        articles_data[article_key][current_para_num]['content'] = existing + "\n" + ho_text

            # 항내용이 이전과 다르면 추가 (중복 방지)
            elif para_content and para_content != prev_para_content:
                if current_para_num in articles_data[article_key]:
                    existing = articles_data[article_key][current_para_num]['content']
                    if para_content not in existing:
                        articles_data[article_key][current_para_num]['content'] = existing + "\n" + para_content
                prev_para_content = para_content

        # 항번호 없이 호만 있는 경우 (Case 2)
        elif not para_num_str and (ho_num is not None and safe_str(ho_num)):
            ho_formatted = format_ho_number(ho_num)
            ho_key = f"_ho_{safe_str(ho_num)}"  # 임시 키

            if ho_key not in articles_data[article_key]:
                content = f"{ho_formatted} {ho_content}" if ho_content else ho_formatted
                articles_data[article_key][ho_key] = {
                    'no': '',
                    'content': content,
                    'sort_key': extract_number_for_sort(ho_num) + 1000  # 항 뒤에 정렬되도록
                }

    # 결과 정리: 조별로 항 목록 생성
    for article_key, paras_dict in articles_data.items():
        if paras_dict:
            # 정렬
            paras_list = list(paras_dict.values())
            paras_list.sort(key=lambda x: x.get('sort_key', float('inf')))

            # sort_key 제거
            for p in paras_list:
                p.pop('sort_key', None)

            # 빈 content 제거
            paras_list = [p for p in paras_list if p['content'].strip()]

            if paras_list:
                result[article_key] = paras_list

    return result


def process_all_sheets(filepath='data/law.xlsx'):
    """
    모든 시트 처리
    """
    all_sheets = pd.read_excel(filepath, sheet_name=None)
    result = {}

    for sheet_name, df in all_sheets.items():
        # 데이터프레임 정규화
        df_normalized = normalize_dataframe(df.copy())

        # 상태 머신으로 처리
        sheet_data = process_sheet_with_state_machine(df_normalized, sheet_name)

        if sheet_data:
            # 조 순서 정렬 (자연 정렬)
            sorted_articles = dict(sorted(
                sheet_data.items(),
                key=lambda x: extract_number_for_sort(x[0])
            ))
            result[sheet_name] = sorted_articles

    return result


def generate_js_file(data, output_path='design/law_data.js'):
    """JS 파일 생성"""
    js_code = """// ============================================
// 법령 데이터 (law.xlsx에서 추출한 마스터 데이터)
// 구조: 시트명(규정) > 조(full_title) > 항(리스트)
// Row-by-Row 상태 머신 알고리즘 적용
// ============================================

const LAW_DATA = %s;
""" % json.dumps(data, ensure_ascii=False, indent=2)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_code)

    return js_code


def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("law.xlsx -> law_data.js 변환 시작")
    print("(Row-by-Row State Machine Algorithm)")
    print("=" * 50)

    # 1. 모든 시트 처리
    print("\n[1/2] 엑셀 파일 로딩 및 상태 머신 처리...")
    result = process_all_sheets('data/law.xlsx')

    # 통계 출력
    print(f"  - 처리된 시트 수: {len(result)}")
    total_articles = 0
    total_paragraphs = 0
    for sheet_name, articles in result.items():
        print(f"    - {sheet_name}: {len(articles)} 조항")
        total_articles += len(articles)
        for article_title, paras in articles.items():
            total_paragraphs += len(paras)

    print(f"\n  - 총 조항 수: {total_articles}")
    print(f"  - 총 항 수: {total_paragraphs}")

    # 2. JS 파일 생성
    print("\n[2/2] JS 파일 생성...")
    js_code = generate_js_file(result)
    print(f"  - 출력 파일: design/law_data.js")
    print(f"  - 파일 크기: {len(js_code):,} bytes")

    print("\n" + "=" * 50)
    print("변환 완료!")
    print("=" * 50)


if __name__ == '__main__':
    main()
