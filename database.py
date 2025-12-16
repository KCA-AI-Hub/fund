"""
SQLite 데이터베이스 연결 및 쿼리 함수
"""
import sqlite3
from typing import List, Dict, Optional

DB_PATH = 'data/chatbot.db'

def get_db_connection():
    """DB 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리처럼 사용 가능
    return conn

# ========================================
# Sheet 기반 함수 (app.js 3단계 구조 지원)
# ========================================

def get_sheet_list() -> List[str]:
    """Sheet 목록 조회 (1단계: 지침)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT sheet_name FROM laws ORDER BY sheet_name')
    sheets = [row['sheet_name'] for row in cursor.fetchall()]

    conn.close()
    return sheets

def get_articles_by_sheet(sheet_name: str) -> List[Dict]:
    """Sheet별 조항 목록 조회 (2단계: 조항)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # GROUP BY로 article_num 기준 중복 제거, 첫 번째 article_title 사용
    query = '''
    SELECT article_num, MIN(article_title) as article_title
    FROM laws
    WHERE sheet_name = ? AND article_num IS NOT NULL
    GROUP BY article_num
    ORDER BY
        CASE
            WHEN article_num GLOB '[0-9]*' THEN CAST(article_num AS INTEGER)
            ELSE 9999
        END,
        article_num
    '''

    cursor.execute(query, (sheet_name,))
    articles = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return articles

def get_paragraphs_by_article(sheet_name: str, article_num: str) -> List[Dict]:
    """조항별 항 목록 조회 (3단계: 항/내용)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 먼저 paragraph_num이 있는 레코드 조회
    query = '''
    SELECT law_id, paragraph_num, paragraph_content, full_text, article_title
    FROM laws
    WHERE sheet_name = ? AND article_num = ?
    ORDER BY
        CASE WHEN paragraph_num IS NULL THEN 1 ELSE 0 END,
        paragraph_num
    '''

    cursor.execute(query, (sheet_name, article_num))
    rows = cursor.fetchall()

    paragraphs = []
    for row in rows:
        row_dict = dict(row)
        # paragraph_num이 없으면 조항 전체 내용으로 처리
        if row_dict['paragraph_num'] is None:
            row_dict['paragraph_num'] = '본문'
        paragraphs.append(row_dict)

    conn.close()
    return paragraphs

# ========================================
# 검색 함수 (태그 기반)
# ========================================

def search_laws(keyword: str, limit: int = 10) -> List[Dict]:
    """키워드로 법령 검색 (중복 제거)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # GROUP BY로 sheet_name + article_num 기준 중복 제거
    query = '''
    SELECT law_id, sheet_name, article_num,
           MIN(article_title) as article_title,
           MIN(full_text) as full_text,
           MIN(paragraph_content) as paragraph_content,
           MIN(tag) as tag,
           MAX(is_active) as is_active
    FROM laws
    WHERE full_text LIKE ?
       OR article_title LIKE ?
       OR tag LIKE ?
    GROUP BY sheet_name, article_num
    ORDER BY is_active DESC
    LIMIT ?
    '''

    pattern = f'%{keyword}%'
    cursor.execute(query, (pattern, pattern, pattern, limit))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results

def search_laws_by_policy_anchor(policy_anchor: str, limit: int = 5) -> List[Dict]:
    """
    policy_anchor로 법령 검색 (조항 번호 추출 + 키워드 매칭)

    예: 「방송통신발전기금 운용·관리규정」 제35조
        → '방송' OR '방발' + '제35조' 검색
    """
    import re

    conn = get_db_connection()
    cursor = conn.cursor()

    results = []

    # 조항 번호 추출 (제35조, 제33조제2항 등)
    article_match = re.search(r'제(\d+)조', policy_anchor)
    article_num = article_match.group(1) if article_match else None

    # 항 번호 추출 (제2항 등)
    paragraph_match = re.search(r'제(\d+)항', policy_anchor)
    paragraph_num = paragraph_match.group(1) if paragraph_match else None

    # 키워드 추출 - DB sheet_name과 매핑
    # DB sheet_names: ICT예산정책협의체 운영, 결과평가, 방발기금 운용관리규정,
    #                 사업비 산정 및 정산, 성과관리 및 활용, 수행상황 및 정산보고,
    #                 점검계획, 정진기금 운용관리규정, 협약체결 및 사업비 관리
    keywords = []

    # 방송통신발전기금 → 방발기금 운용관리규정
    if '방송통신' in policy_anchor or '방발' in policy_anchor or '방송통신발전기금' in policy_anchor:
        keywords.append('방발기금')

    # 정보통신진흥기금 → 정진기금 운용관리규정
    if '정보통신' in policy_anchor or '정진' in policy_anchor or '정보통신진흥기금' in policy_anchor:
        keywords.append('정진기금')

    # 수행상황 및 정산 보고 등에 관한 지침 → 수행상황 및 정산보고
    if '수행상황' in policy_anchor or '정산 보고' in policy_anchor or '정산보고' in policy_anchor:
        keywords.append('수행상황')

    # 협약 관련 → 협약체결 및 사업비 관리
    if '협약' in policy_anchor:
        keywords.append('협약체결')

    # 사업비 관련 → 사업비 산정 및 정산
    if '사업비' in policy_anchor:
        keywords.append('사업비')

    # 성과 관련 → 성과관리 및 활용
    if '성과' in policy_anchor:
        keywords.append('성과관리')

    # 결과평가 → 결과평가
    if '결과평가' in policy_anchor:
        keywords.append('결과평가')

    # ICT예산정책협의체
    if 'ICT' in policy_anchor or '예산정책협의체' in policy_anchor:
        keywords.append('ICT예산')

    # 점검계획
    if '점검' in policy_anchor:
        keywords.append('점검계획')

    # 조항 번호가 있으면 조항 번호로 검색
    if article_num:
        # sheet_name에 키워드가 포함되고 article_num이 일치하는 법령 검색
        if keywords:
            keyword_conditions = ' OR '.join([f"sheet_name LIKE '%{kw}%'" for kw in keywords])
            query = f'''
            SELECT law_id, sheet_name, article_num,
                   MIN(article_title) as article_title,
                   MIN(full_text) as full_text,
                   MIN(paragraph_content) as paragraph_content,
                   MIN(tag) as tag,
                   MAX(is_active) as is_active
            FROM laws
            WHERE ({keyword_conditions})
              AND article_num LIKE ?
            GROUP BY sheet_name, article_num
            ORDER BY is_active DESC
            LIMIT ?
            '''
            cursor.execute(query, (f'%{article_num}%', limit))
        else:
            # 키워드 없으면 조항 번호만으로 검색
            query = '''
            SELECT law_id, sheet_name, article_num,
                   MIN(article_title) as article_title,
                   MIN(full_text) as full_text,
                   MIN(paragraph_content) as paragraph_content,
                   MIN(tag) as tag,
                   MAX(is_active) as is_active
            FROM laws
            WHERE article_num LIKE ?
            GROUP BY sheet_name, article_num
            ORDER BY is_active DESC
            LIMIT ?
            '''
            cursor.execute(query, (f'%{article_num}%', limit))

        results = [dict(row) for row in cursor.fetchall()]

    # 결과가 없으면 일반 키워드 검색으로 폴백
    if not results:
        # policy_anchor에서 핵심 단어 추출해서 검색
        for kw in keywords:
            if not results:
                results = search_laws(kw, limit)

    conn.close()
    return results

# ========================================
# FAQ 함수
# ========================================

def get_faq_by_question(question: str) -> Optional[Dict]:
    """질문으로 FAQ 검색"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM faqs WHERE question LIKE ? LIMIT 1'
    cursor.execute(query, (f'%{question}%',))

    result = cursor.fetchone()
    conn.close()

    return dict(result) if result else None

def get_laws_by_faq(faq_id: str) -> List[Dict]:
    """FAQ ID로 관련 법령 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # policy_anchor로 법령 검색
    cursor.execute('SELECT policy_anchor FROM faqs WHERE faq_id = ?', (faq_id,))
    faq = cursor.fetchone()

    if not faq or not faq['policy_anchor']:
        return []

    # policy_anchor를 파싱해서 관련 법령 검색
    anchor = faq['policy_anchor']
    cursor.execute('SELECT * FROM laws WHERE full_text LIKE ?', (f'%{anchor}%',))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results
