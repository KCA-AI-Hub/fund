"""
law.xlsx의 모든 Sheet를 SQLite DB로 변환
총 14개 Sheet, 1,063개 법령 조항
실행: uv run python convert_law_to_db_sheets.py
"""
import pandas as pd
import sqlite3

# 1. law.xlsx의 모든 Sheet 읽기
excel_file = 'data/law.xlsx'
sheets = pd.ExcelFile(excel_file, engine='openpyxl')

print(f'총 {len(sheets.sheet_names)}개 Sheet 발견:')
for i, sheet in enumerate(sheets.sheet_names, 1):
    print(f'  {i}. {sheet}')

# 2. SQLite DB 연결 (파일 자동 생성)
conn = sqlite3.connect('data/chatbot.db')

# 3. laws 테이블 생성 (⭐ sheet_name 컬럼 추가!)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id TEXT UNIQUE NOT NULL,
    law_title TEXT NOT NULL,
    sheet_name TEXT NOT NULL,              -- ⭐ Sheet 이름 (1단계: 지침 그룹)
    chapter_num TEXT,
    chapter_title TEXT,
    article_num TEXT,                      -- 2단계: 조번호
    article_title TEXT,
    paragraph_num REAL,                    -- 3단계: 항번호
    paragraph_content TEXT,
    clause_num REAL,
    clause_content TEXT,
    item_num TEXT,
    item_content TEXT,
    full_text TEXT NOT NULL,
    first_effective_date DATE,
    amendment_date DATE,
    is_active BOOLEAN DEFAULT 1,
    tags TEXT
)
''')

# 4. 모든 Sheet 데이터 삽입
all_data = []
for sheet_name in sheets.sheet_names:
    print(f'읽는 중: {sheet_name}...')
    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')

    # sheet_name 컬럼 추가
    df['sheet_name'] = sheet_name

    # 컬럼 매핑
    df.rename(columns={
        '장번호': 'chapter_num',
        '장제목': 'chapter_title',
        '조번호': 'article_num',
        '조제목': 'article_title',
        '항번호': 'paragraph_num',
        '항내용': 'paragraph_content',
        '호번호': 'clause_num',
        '호내용': 'clause_content',
        '목번호': 'item_num',
        '목내용': 'item_content',
        '최초시행일': 'first_effective_date',
        '개정일': 'amendment_date',
    }, inplace=True)

    all_data.append(df)
    print(f'   → {len(df)}개 법령 조항')

# 6. 전체 데이터 병합 후 DB 삽입
final_df = pd.concat(all_data, ignore_index=True)

# ⭐ 날짜 컬럼을 문자열로 변환 (SQLite 호환성)
if 'first_effective_date' in final_df.columns:
    final_df['first_effective_date'] = final_df['first_effective_date'].astype(str)
if 'amendment_date' in final_df.columns:
    final_df['amendment_date'] = final_df['amendment_date'].astype(str)

final_df.to_sql('laws', conn, if_exists='replace', index=False)

# 7. 인덱스 생성 (데이터 삽입 후)
print('\n인덱스 생성 중...')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_sheet_name ON laws(sheet_name)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_law_title ON laws(law_title)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_article_num ON laws(article_num)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON laws(tag)')  # tag 컬럼 사용

conn.commit()
conn.close()

print(f"\n[SUCCESS] 변환 완료!")
print(f"   - 총 {len(sheets.sheet_names)}개 Sheet")
print(f"   - 총 {len(final_df)}개 법령 조항")
print(f"   - 저장 위치: data/chatbot.db")
