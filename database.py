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
