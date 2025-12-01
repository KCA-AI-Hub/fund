"""
DB 데이터를 JS 파일용 고정 데이터로 변환
"""
import json
from database import get_sheet_list, get_articles_by_sheet, get_paragraphs_by_article

# 고정 지침 목록 (순서 지정)
GUIDELINE_ORDER = [
    ('협약체결 및 사업비 관리', '협약체결 및 사업비 관리', '협약 체결, 변경, 해약 및 사업비 관리'),
    ('사업비 산정 및 정산', '사업비 산정 및 정산', '사업비 산정 기준 및 정산 절차'),
    ('사업비 산정 및 정산_별표1', '사업비 산정 및 정산 [별표1]', '인건비 기준단가표'),
    ('사업비 산정 및 정산_별표2', '사업비 산정 및 정산 [별표2]', '연구시설·장비 사용료 산정기준'),
    ('사업비 산정 및 정산_별표3', '사업비 산정 및 정산 [별표3]', '위탁연구개발비 계상 기준'),
    ('수행상황 및 정산보고', '수행상황 및 정산보고', '사업 수행상황 보고 및 정산'),
    ('결과평가', '결과평가', '사업 결과평가 기준 및 절차'),
    ('결과평가_별지', '결과평가 [별지]', '결과평가 서식'),
    ('성과관리 및 활용', '성과관리 및 활용', '연구성과 관리 및 활용'),
    ('성과관리_별지', '성과관리 [별지]', '성과관리 서식'),
    ('점검계획', '점검계획', '사업 점검 계획'),
    ('방발기금 운용관리규정', '방송통신발전기금 운용관리규정', '방발기금 운용 및 관리'),
    ('정진기금 운용관리규정', '정보통신진흥기금 운용관리규정', '정진기금 운용 및 관리'),
    ('ICT예산정책협의체 운영', 'ICT예산정책협의체 운영', '예산정책협의체 운영 지침'),
]

def export_data():
    """모든 데이터를 수집하여 JS 객체로 변환"""

    # 1. 지침 목록
    guidelines = []
    for sheet_id, name, desc in GUIDELINE_ORDER:
        guidelines.append({
            'id': sheet_id,
            'name': name,
            'description': desc
        })

    # 2. 조항 데이터 (지침별)
    articles_data = {}
    for sheet_id, _, _ in GUIDELINE_ORDER:
        articles = get_articles_by_sheet(sheet_id)
        articles_data[sheet_id] = []
        for art in articles:
            articles_data[sheet_id].append({
                'id': art['article_num'],
                'name': f"제{art['article_num']}조" if art['article_num'].isdigit() else art['article_num'],
                'description': art['article_title'] or '조항'
            })

    # 3. 항 데이터 (지침+조항별) - 중복 제거
    paragraphs_data = {}
    for sheet_id, _, _ in GUIDELINE_ORDER:
        paragraphs_data[sheet_id] = {}
        articles = get_articles_by_sheet(sheet_id)

        for art in articles:
            article_num = art['article_num']
            paras = get_paragraphs_by_article(sheet_id, article_num)

            # 중복 제거 (law_id 기준)
            seen_ids = set()
            unique_paras = []
            for p in paras:
                if p['law_id'] not in seen_ids:
                    seen_ids.add(p['law_id'])

                    # paragraph_num 정리
                    para_num = p['paragraph_num']
                    if para_num == '본문' or para_num is None:
                        title = art['article_title'] or '본문'
                    elif isinstance(para_num, float):
                        title = f"제{int(para_num)}항"
                    else:
                        title = f"제{para_num}항"

                    content = p['paragraph_content'] or p['full_text'] or ''
                    # 내용 길이 제한 (너무 길면 자름)
                    if len(content) > 500:
                        content = content[:500] + '...'

                    unique_paras.append({
                        'id': p['law_id'],
                        'title': title,
                        'content': content
                    })

            paragraphs_data[sheet_id][article_num] = unique_paras

    return guidelines, articles_data, paragraphs_data

def generate_js_code():
    """JS 코드 생성"""
    guidelines, articles_data, paragraphs_data = export_data()

    js_code = """// ============================================
// 법령 데이터 (DB에서 추출한 고정 데이터)
// ============================================

const LAW_DATA = {
    // 1단계: 지침 목록
    guidelines: %s,

    // 2단계: 조항 목록 (지침별)
    articles: %s,

    // 3단계: 항 목록 (지침+조항별)
    paragraphs: %s
};
""" % (
        json.dumps(guidelines, ensure_ascii=False, indent=8),
        json.dumps(articles_data, ensure_ascii=False, indent=8),
        json.dumps(paragraphs_data, ensure_ascii=False, indent=8)
    )

    return js_code

if __name__ == '__main__':
    js_code = generate_js_code()

    # 파일로 저장
    with open('design/law_data.js', 'w', encoding='utf-8') as f:
        f.write(js_code)

    print("design/law_data.js 파일 생성 완료!")
    print(f"파일 크기: {len(js_code):,} bytes")
