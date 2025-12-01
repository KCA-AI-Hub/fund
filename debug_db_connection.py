"""
DB 연결 디버깅 스크립트
- SQLite 파일 경로 확인
- 연결 테스트 및 에러 진단
"""
import os
import sqlite3
import sys

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 기준 경로들
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_DB_PATHS = [
    os.path.join(PROJECT_ROOT, 'data', 'chatbot.db'),
    os.path.join(PROJECT_ROOT, 'chatbot.db'),
    os.path.join(PROJECT_ROOT, 'data', 'laws.db'),
    'data/chatbot.db',
    'chatbot.db',
]

def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)

def check_file_exists(path):
    """파일 존재 여부 및 정보 확인"""
    abs_path = os.path.abspath(path)
    exists = os.path.exists(abs_path)

    print(f"\nPath: {abs_path}")
    print(f"  - Exists: {'[OK] Yes' if exists else '[X] No'}")

    if exists:
        size = os.path.getsize(abs_path)
        print(f"  - File size: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"  - Read permission: {'[OK]' if os.access(abs_path, os.R_OK) else '[X]'}")
        print(f"  - Write permission: {'[OK]' if os.access(abs_path, os.W_OK) else '[X]'}")

    return exists, abs_path

def test_db_connection(db_path):
    """DB 연결 테스트"""
    print_separator("DB Connection Test")
    print(f"Connecting to: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print("[OK] SQLite connection successful!")

        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"\nTables found: {tables}")

        # 각 테이블 샘플 데이터 조회
        for table in tables:
            print_separator(f"Table: {table}")
            try:
                # 컬럼 정보
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                col_names = [col['name'] for col in columns]
                print(f"Columns: {col_names}")

                # 레코드 수
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                count = cursor.fetchone()['cnt']
                print(f"Total records: {count}")

                # 샘플 데이터
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    print(f"\nSample data:")
                    for col in col_names:
                        value = sample[col]
                        if value and len(str(value)) > 100:
                            value = str(value)[:100] + "..."
                        print(f"  - {col}: {value}")
                else:
                    print("  (No data)")

            except Exception as e:
                print(f"  [X] Table query failed: {e}")

        conn.close()
        return True

    except sqlite3.OperationalError as e:
        print(f"[X] SQLite connection failed (OperationalError): {e}")
        if "unable to open database file" in str(e):
            print("  -> Cause: File path is wrong or file does not exist.")
        elif "disk I/O error" in str(e):
            print("  -> Cause: Disk I/O error")
        return False

    except sqlite3.DatabaseError as e:
        print(f"[X] SQLite database error: {e}")
        print("  -> Cause: DB file is corrupted or not a valid SQLite file.")
        return False

    except Exception as e:
        print(f"[X] Unexpected error: {type(e).__name__}: {e}")
        return False

def test_laws_queries(db_path):
    """laws 테이블 관련 쿼리 테스트"""
    print_separator("Laws Table Query Test")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Sheet 목록 조회
        print("\n[1] Sheet list query (get_sheet_list)")
        cursor.execute('SELECT DISTINCT sheet_name FROM laws ORDER BY sheet_name')
        sheets = [row['sheet_name'] for row in cursor.fetchall()]
        print(f"Result: {sheets}")
        print(f"[OK] {len(sheets)} sheets found")

        if sheets:
            test_sheet = sheets[0]

            # 2. 조항 목록 조회
            print(f"\n[2] Articles query (sheet: {test_sheet})")
            cursor.execute('''
                SELECT DISTINCT article_num, article_title
                FROM laws
                WHERE sheet_name = ? AND article_num IS NOT NULL
                ORDER BY article_num
            ''', (test_sheet,))
            articles = [dict(row) for row in cursor.fetchall()]
            print(f"Result: {len(articles)} articles")
            if articles:
                print(f"  First: {articles[0]}")

                # 3. 항 목록 조회
                test_article = articles[0]['article_num']
                print(f"\n[3] Paragraphs query (sheet: {test_sheet}, article: {test_article})")
                cursor.execute('''
                    SELECT law_id, paragraph_num, paragraph_content, full_text
                    FROM laws
                    WHERE sheet_name = ? AND article_num = ?
                    ORDER BY paragraph_num
                ''', (test_sheet, test_article))
                paragraphs = [dict(row) for row in cursor.fetchall()]
                print(f"Result: {len(paragraphs)} paragraphs/records")
                if paragraphs:
                    p = paragraphs[0]
                    content = p.get('paragraph_content') or p.get('full_text') or ''
                    para_num = p.get('paragraph_num') or 'None (full article)'
                    print(f"  First record: {para_num} - {content[:80]}...")

        conn.close()
        print("\n[OK] All query tests passed!")
        return True

    except Exception as e:
        print(f"[X] Query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_separator("SQLite DB Connection Debug Start")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {PROJECT_ROOT}")

    # Step 1: 가능한 DB 경로 확인
    print_separator("Step 1: Check DB file paths")
    found_db = None

    for path in POSSIBLE_DB_PATHS:
        exists, abs_path = check_file_exists(path)
        if exists and found_db is None:
            found_db = abs_path

    # data 디렉토리 내용 확인
    data_dir = os.path.join(PROJECT_ROOT, 'data')
    if os.path.exists(data_dir):
        print(f"\n[DIR] data/ contents:")
        for f in os.listdir(data_dir):
            fpath = os.path.join(data_dir, f)
            size = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
            print(f"  - {f} ({size:,} bytes)")

    if not found_db:
        print("\n[X] DB file not found!")
        print("Solution:")
        print("  1. Check if data/chatbot.db file exists.")
        print("  2. Run convert_law_to_db_sheets.py to create the DB.")
        return

    # Step 2: DB 연결 테스트
    if not test_db_connection(found_db):
        return

    # Step 3: Laws 쿼리 테스트
    test_laws_queries(found_db)

    print_separator("Debug Complete")
    print(f"\n[OK] DB path to use: {found_db}")
    print("\nRecommendation:")
    print(f"  Set database.py DB_PATH to:")

    # 상대 경로로 변환 시도
    try:
        rel_path = os.path.relpath(found_db, PROJECT_ROOT)
        print(f"  DB_PATH = '{rel_path}'")
    except:
        print(f"  DB_PATH = '{found_db}'")

if __name__ == "__main__":
    main()
