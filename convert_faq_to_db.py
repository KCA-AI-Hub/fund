"""
faq_topic.xlsx를 SQLite DB로 변환하는 스크립트
실행: uv run python convert_faq_to_db.py
"""
import pandas as pd
import sqlite3

# 1. faq_topic.xlsx 읽기
df = pd.read_excel('data/faq_topic.xlsx', engine='openpyxl')

print(f'총 {len(df)}개 FAQ 발견')

# 2. SQLite DB 연결
conn = sqlite3.connect('data/chatbot.db')

# 3. faqs 테이블 생성
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faq_id TEXT UNIQUE NOT NULL,
    question TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    policy_anchor TEXT,
    tag TEXT,
    last_reviewed_at DATE,
    source TEXT
)
''')

# 4. 데이터 삽입
# 날짜 컬럼 문자열 변환
if 'last_reviewed_at' in df.columns:
    df['last_reviewed_at'] = df['last_reviewed_at'].astype(str)

# 컬럼 이름이 다를 수 있으니 확인
if 'tags' in df.columns:
    df.rename(columns={'tags': 'tag'}, inplace=True)

df.to_sql('faqs', conn, if_exists='replace', index=False)

# 5. 인덱스 생성
cursor.execute('CREATE INDEX IF NOT EXISTS idx_faq_question ON faqs(question)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_policy_anchor ON faqs(policy_anchor)')

conn.commit()
conn.close()

print(f"[SUCCESS] 변환 완료!")
print(f"   - 총 {len(df)}개 FAQ")
print(f"   - 저장 위치: data/chatbot.db")
