from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import json
import traceback
import requests
import pandas as pd
import re
import database  # SQLite law search functions

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging(app):
    """Configure logging for both file and console output"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up log format
    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    
    # Console handler for development mode
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Configure app logger
    app.logger.handlers.clear()  # Clear default handlers
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Configure werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(console_handler)
    werkzeug_logger.setLevel(logging.INFO)
    
    # Create separate logger for API calls
    api_logger = logging.getLogger('api_calls')
    api_file_handler = RotatingFileHandler(
        'logs/api_calls.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    api_file_handler.setFormatter(log_format)
    api_logger.addHandler(api_file_handler)
    api_logger.addHandler(console_handler)
    api_logger.setLevel(logging.INFO)
    
    return api_logger

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Setup logging
api_logger = setup_logging(app)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
app.logger.info("OpenAI client initialized successfully")

# Dify Configuration
DIFY_API_URL = os.getenv('DIFY_API_URL', 'http://112.173.179.199:5001/v1')
DIFY_API_KEY = os.getenv('DIFY_API_KEY', '')
DIFY_DATASET_ID = os.getenv('DIFY_DATASET_ID', '')
AI_MODE = os.getenv('AI_MODE', 'dify')  # 'dify' or 'openai'
FALLBACK_TO_OPENAI = os.getenv('FALLBACK_TO_OPENAI', 'True').lower() == 'true'

app.logger.info(f"AI Mode: {AI_MODE}")
app.logger.info(f"Dify API URL: {DIFY_API_URL}")
app.logger.info(f"Dify Dataset ID: {DIFY_DATASET_ID}")
app.logger.info(f"Fallback to OpenAI: {FALLBACK_TO_OPENAI}")

# Store chat sessions in memory (in production, use a database)
chat_sessions = {}

# ========================================
# [1단계] 마스터 트리 데이터 로드 (서버 시작 시 1회)
# ========================================
LAW_MASTER_TREE = {}

def build_law_master_tree():
    """
    DB에서 법령 데이터를 읽어 3단 계층형 딕셔너리로 변환
    구조: { 지침명: { 제N조: { title: "조항제목", paragraphs: ["항1내용", "항2내용"] } } }

    [수정사항]
    1. Get or Create 패턴: 조(Article) 중복 생성 방지
    2. 딕셔너리 기반 항(Paragraph) 관리: law_id를 Unique Key로 사용하여 중복 제거
    3. Natural Sort: 제1조, 제2조, ... 제10조 순서로 정렬
    """
    import sqlite3
    global LAW_MASTER_TREE

    def extract_article_number(article_key):
        """'제123조' → 123 추출 (Natural Sort용)"""
        match = re.search(r'제(\d+)조', article_key)
        return int(match.group(1)) if match else float('inf')

    try:
        conn = sqlite3.connect('data/chatbot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 모든 법령 데이터 조회 (정렬 제거 - Python에서 Natural Sort 적용)
        cursor.execute('''
            SELECT sheet_name, article_num, article_title, paragraph_num, paragraph_content, full_text, law_id
            FROM laws
            WHERE sheet_name IS NOT NULL AND article_num IS NOT NULL
        ''')

        rows = cursor.fetchall()
        conn.close()

        # 1단계: 딕셔너리 기반 계층 구조 생성 (중복 제거)
        tree = {}
        for row in rows:
            sheet_name = row['sheet_name']
            article_num = row['article_num']
            article_title = row['article_title'] or ''
            paragraph_num = row['paragraph_num']
            paragraph_content = row['paragraph_content'] or row['full_text'] or ''
            law_id = row['law_id']

            # 지침 (Get or Create)
            if sheet_name not in tree:
                tree[sheet_name] = {}

            # 조 (Get or Create) - 이미 존재하면 기존 객체 사용
            article_key = f"제{article_num}조"
            if article_key not in tree[sheet_name]:
                tree[sheet_name][article_key] = {
                    'title': article_title,
                    'paragraphs': {}  # 딕셔너리로 변경! (Unique Key 기반 중복 제거)
                }

            # 항 (Unique Key로 중복 제거)
            if paragraph_content:
                # law_id를 Unique Key로 사용 (더 안정적)
                para_key = law_id or f"{paragraph_num}_{hash(paragraph_content)}"
                if para_key not in tree[sheet_name][article_key]['paragraphs']:
                    if paragraph_num:
                        try:
                            para_text = f"제{int(float(paragraph_num))}항: {paragraph_content}"
                        except (ValueError, TypeError):
                            para_text = f"{paragraph_num}: {paragraph_content}"
                    else:
                        para_text = paragraph_content
                    tree[sheet_name][article_key]['paragraphs'][para_key] = para_text

        # 2단계: Natural Sort 적용 + 딕셔너리 → 리스트 변환
        sorted_tree = {}
        for sheet_name, articles in tree.items():
            # 조항 정렬 (제1조, 제2조, ... 제10조 순)
            sorted_articles = sorted(articles.items(), key=lambda x: extract_article_number(x[0]))

            sorted_tree[sheet_name] = {}
            for article_key, article_data in sorted_articles:
                sorted_tree[sheet_name][article_key] = {
                    'title': article_data['title'],
                    'paragraphs': list(article_data['paragraphs'].values())  # 리스트로 변환
                }

        LAW_MASTER_TREE = sorted_tree
        print(f"[Server] 마스터 트리 로드 완료: {len(sorted_tree)}개 지침, 총 {sum(len(v) for v in sorted_tree.values())}개 조항")

    except Exception as e:
        print(f"[Server] 마스터 트리 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        LAW_MASTER_TREE = {}

# 서버 시작 시 마스터 트리 로드
build_law_master_tree()

# Load FAQ policy mapping from faq_topic.xlsx
faq_policy_map = {}
faq_df_global = None  # FAQ 전체 데이터 보관 (직접 매칭용)
FAQ_DIRECT_THRESHOLD = float(os.getenv('FAQ_DIRECT_THRESHOLD', '0.85'))  # FAQ 직접 사용 임계값

try:
    faq_file_path = os.path.join(os.path.dirname(__file__), 'data', 'faq_topic.xlsx')
    if os.path.exists(faq_file_path):
        faq_df_global = pd.read_excel(faq_file_path)  # 전체 데이터프레임 보관
        faq_policy_map = dict(zip(faq_df_global['faq_id'], faq_df_global['policy_anchor']))
        app.logger.info(f"Loaded {len(faq_policy_map)} FAQ policy mappings from {faq_file_path}")
        app.logger.info(f"FAQ direct match threshold: {FAQ_DIRECT_THRESHOLD}")
    else:
        app.logger.warning(f"FAQ file not found: {faq_file_path}")
except Exception as e:
    app.logger.error(f"Failed to load FAQ policy mapping: {e}")
    app.logger.error(traceback.format_exc())

# Request/Response logging middleware
@app.before_request
def log_request_info():
    """Log information about incoming requests"""
    app.logger.debug('Request Headers: %s', dict(request.headers))
    app.logger.info('Request: %s %s', request.method, request.path)
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            # Don't log sensitive data
            body = request.get_json()
            if body:
                safe_body = {k: v if k != 'api_key' else '***' for k, v in body.items()}
                app.logger.debug('Request Body: %s', json.dumps(safe_body, ensure_ascii=False)[:500])

@app.after_request
def log_response_info(response):
    """Log information about outgoing responses"""
    app.logger.info('Response: %s %s - Status: %s', 
                    request.method, request.path, response.status)
    return response

@app.route('/')
def index():
    """Render the main chat interface"""
    app.logger.info('Main page accessed from IP: %s', request.remote_addr)
    return render_template('index.html')

def extract_keywords_from_question(question: str) -> list:
    """
    사용자 질문에서 키워드 추출 (간단한 방식)
    향후 NLP 기반으로 개선 가능
    """
    # 불용어 리스트
    stopwords = ['은', '는', '이', '가', '을', '를', '의', '에', '로', '으로', '와', '과',
                 '에서', '까지', '부터', '하다', '되다', '있다', '없다', '하는', '되는',
                 '어떻게', '무엇', '언제', '어디', '왜', '누가', '어떤', '몇', '얼마',
                 '합니다', '입니다', '습니다', '니다', '요', '할', '수', '것', '등']

    # 특수문자 제거 및 공백으로 분리
    import re
    words = re.sub(r'[^\w\s]', ' ', question).split()

    # 불용어 제거 및 2글자 이상만 추출
    keywords = [w for w in words if len(w) >= 2 and w not in stopwords]

    return keywords[:5]  # 최대 5개 키워드

def search_laws_by_keywords(keywords: list, limit: int = 5) -> list:
    """
    키워드 기반 SQLite 법령 검색 (중복 제거 포함)
    - sheet_name + article_num 기준으로 중복 제거
    """
    if not keywords:
        return []

    all_results = []
    seen_keys = set()  # 중복 체크용 (sheet_name + article_num 조합)
    total_raw_count = 0  # 중복 제거 전 총 개수

    for keyword in keywords:
        laws = database.search_laws(keyword, limit=3)
        total_raw_count += len(laws)  # 원본 개수 누적
        for law in laws:
            sheet_name = law.get('sheet_name') or ''
            article_num = law.get('article_num') or ''

            # 고유 키: sheet_name + article_num 조합 (law_id 무시)
            unique_key = f"{sheet_name}_{article_num}"

            # 중복 체크
            if unique_key in seen_keys:
                continue

            seen_keys.add(unique_key)
            all_results.append({
                'law_id': law.get('law_id'),
                'title': law.get('article_title') or law.get('law_title') or '제목 없음',
                'content': law.get('full_text') or law.get('paragraph_content') or '',
                'sheet_name': sheet_name,
                'article_num': article_num,
                'source': 'SQLite DB',
                'matched_keyword': keyword
            })

    # 중복 제거 로그 출력
    print(f"[Dedup] 중복 제거 전: {total_raw_count}개, 후: {len(all_results)}개")

    return all_results[:limit]

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages and generate responses"""
    session_id = None
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        prompt_template = data.get('prompt_template', None)  # 선택적 프롬프트 템플릿

        app.logger.info(f'Chat request from session {session_id}: {user_message[:100]}...')
        api_logger.info(f'Session {session_id} - User message: {user_message}')

        # Initialize session if new
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'messages': [],
                'created_at': datetime.now()
            }

        # Add user message to session
        chat_sessions[session_id]['messages'].append({
            'role': 'user',
            'content': user_message
        })

        assistant_message = None
        retrieved_docs = []
        matched_faq_id = None
        related_laws = []

        # ===== [Action A] 키워드 추출 & SQLite 법령 검색 (즉시 실행) =====
        app.logger.info('[Action A] Extracting keywords and searching SQLite DB')
        keywords = extract_keywords_from_question(user_message)
        app.logger.info(f'Extracted keywords: {keywords}')

        sqlite_laws = search_laws_by_keywords(keywords, limit=5)
        app.logger.info(f'Found {len(sqlite_laws)} laws from SQLite')

        # SQLite 검색 결과를 related_laws에 즉시 저장
        for law in sqlite_laws:
            related_laws.append({
                'title': f"{law['sheet_name']} - {law['title']}",
                'content': law['content'][:300] + ('...' if len(law['content']) > 300 else ''),
                'article_num': law['article_num'],
                'source': 'SQLite DB',
                'matched_keyword': law.get('matched_keyword', '')
            })

        # ===== [Action B] Dify API 호출 (Hybrid RAG Mode) =====
        if AI_MODE == 'dify':
            try:
                app.logger.info('Using Hybrid RAG mode (Dify FAQ + Local Policy Mapping)')

                # STEP 1: Search FAQ in Dify Knowledge
                app.logger.info('Step 1: Searching FAQ in Dify Knowledge')
                faq_result = call_dify_knowledge(user_message, top_k=3)

                if faq_result['success'] and faq_result['records']:
                    retrieved_docs = faq_result['records']
                    app.logger.info(f'Retrieved {len(retrieved_docs)} FAQ records')

                    # STEP 2: Extract faq_id and score from best match
                    app.logger.info('Step 2: Extracting faq_id from best match')
                    best_faq = retrieved_docs[0]
                    faq_score = best_faq.get('score', 0)
                    faq_id = extract_faq_id_from_content(best_faq)

                    app.logger.info(f'Best FAQ score: {faq_score}, threshold: {FAQ_DIRECT_THRESHOLD}')

                    if faq_id:
                        app.logger.info(f'Extracted faq_id: {faq_id}')
                        matched_faq_id = faq_id

                        # ★★★ FAQ 높은 매칭 체크 (score >= threshold) ★★★
                        if faq_score >= FAQ_DIRECT_THRESHOLD:
                            app.logger.info(f'[FAQ High Match] Score {faq_score} >= {FAQ_DIRECT_THRESHOLD}')

                            # FAQ 답변 조회
                            faq_data = get_faq_direct_answer(faq_id)

                            if faq_data and faq_data.get('answer_text'):
                                # ★ policy_anchor 기반 법령만 사용 (키워드 검색 결과 초기화)
                                related_laws = []
                                policy_docs = []

                                if faq_data.get('policy_anchor'):
                                    policy_anchors = [p.strip() for p in faq_data['policy_anchor'].split(';')]
                                    for anchor in policy_anchors:
                                        if anchor:
                                            # ★ 새로운 policy_anchor 전용 검색 함수 사용
                                            laws = database.search_laws_by_policy_anchor(anchor, limit=1)
                                            for law in laws:
                                                related_laws.append({
                                                    'title': f"{law.get('sheet_name', '')} - {law.get('article_title', '')}",
                                                    'content': (law.get('full_text') or law.get('paragraph_content') or '')[:500],
                                                    'article_num': law.get('article_num', ''),
                                                    'sheet_name': law.get('sheet_name', ''),
                                                    'source': 'FAQ High Match',
                                                    'matched_keyword': anchor
                                                })
                                                policy_docs.append({
                                                    'segment': {
                                                        'content': law.get('full_text') or law.get('paragraph_content') or '',
                                                        'document': {'name': law.get('sheet_name', '')}
                                                    },
                                                    'score': 0.9
                                                })

                                # ★ GPT로 답변 생성 (FAQ + 법령 컨텍스트) - 포맷에 맞게
                                app.logger.info('[FAQ High Match] Generating answer with GPT context')
                                assistant_message = generate_answer_with_context(
                                    user_message,
                                    retrieved_docs,  # Dify에서 받은 FAQ 레코드
                                    policy_docs if policy_docs else None
                                )

                                app.logger.info(f'[FAQ High Match] Completed - found {len(related_laws)} laws from policy_anchor')

                                # 이후 정상 흐름 따라감 (suggested_answer 등)

                            else:
                                app.logger.warning(f'[FAQ High Match] Failed to get FAQ data, falling back to normal flow')

                        # ★★★ 기존 로직: score가 낮으면 GPT 생성 ★★★
                        app.logger.info(f'Using GPT generation (score {faq_score} < {FAQ_DIRECT_THRESHOLD} or FAQ data unavailable)')

                        # STEP 3: Get policy_anchor from local mapping
                        app.logger.info('Step 3: Getting policy_anchor from local mapping')
                        policy_anchor = get_policy_anchor(faq_id)

                        if policy_anchor:
                            app.logger.info(f'Mapped policy_anchor: {policy_anchor[:100]}...')

                            # STEP 4: Search policy documents in SQLite DB
                            app.logger.info('Step 4: Searching policy documents in SQLite DB')
                            policy_docs = []
                            policy_anchors = [p.strip() for p in policy_anchor.split(';')]

                            for idx, anchor in enumerate(policy_anchors[:2], 1):  # Max 2 anchors
                                app.logger.debug(f'Searching laws in SQLite {idx}: {anchor[:50]}...')
                                laws = database.search_laws_by_policy_anchor(anchor, limit=2)

                                # Convert SQLite format to Dify-compatible format
                                for law in laws:
                                    policy_docs.append({
                                        'segment': {
                                            'content': law['paragraph_content'] or law['full_text'],
                                            'document': {'name': law['sheet_name']}
                                        },
                                        'score': 0.85  # SQLite doesn't provide scores
                                    })
                                    app.logger.debug(f'Found law: {law["article_title"] or law["law_title"]}')

                            app.logger.info(f'Total policy docs retrieved from SQLite: {len(policy_docs)}')

                            # STEP 5: Generate answer with FAQ + Policy context
                            app.logger.info('Step 5: Generating answer with FAQ + Policy context')
                            assistant_message = generate_answer_with_context(
                                user_message,
                                retrieved_docs,
                                policy_docs
                            )

                            # STEP 6: Build related_laws from policy_anchor (NOT LLM generated!)
                            related_laws = []
                            for anchor in policy_anchors:
                                related_laws.append({
                                    'title': anchor.strip(),
                                    'source': 'FAQ Database',
                                    'faq_id': faq_id
                                })

                            app.logger.info(f'Hybrid RAG completed successfully for faq_id: {faq_id}')

                        else:
                            # No policy_anchor found, use FAQ only
                            app.logger.warning(f'No policy_anchor found for {faq_id}, using FAQ only')
                            assistant_message = generate_answer_with_context(
                                user_message,
                                retrieved_docs,
                                None
                            )

                    else:
                        # Could not extract faq_id, use basic RAG
                        app.logger.warning('Could not extract faq_id, using basic Dify RAG')
                        assistant_message = generate_answer_with_dify_rag(
                            user_message,
                            retrieved_docs,
                            prompt_template
                        )

                    app.logger.info(f'Answer generated for session {session_id}')

                # Fallback: Dify 실패 시 로컬 FAQ 검색 시도
                elif FALLBACK_TO_OPENAI:
                    app.logger.warning('Dify FAQ search failed or no results, trying local FAQ search')

                    # ★ 로컬 FAQ 검색 시도
                    local_faq_match = search_faq_local(user_message, threshold=0.5)

                    if local_faq_match and local_faq_match.get('score', 0) >= FAQ_DIRECT_THRESHOLD:
                        # 로컬 FAQ에서 높은 매칭 발견
                        faq_id = local_faq_match['faq_id']
                        faq_score = local_faq_match['score']
                        matched_faq_id = faq_id
                        app.logger.info(f'[Local FAQ Match] Score {faq_score:.2f} >= {FAQ_DIRECT_THRESHOLD}')

                        faq_data = get_faq_direct_answer(faq_id)

                        if faq_data and faq_data.get('answer_text'):
                            # policy_anchor 기반 법령 검색
                            related_laws = []  # 키워드 검색 결과 초기화
                            policy_docs = []

                            if faq_data.get('policy_anchor'):
                                policy_anchors = [p.strip() for p in faq_data['policy_anchor'].split(';')]
                                for anchor in policy_anchors:
                                    if anchor:
                                        laws = database.search_laws_by_policy_anchor(anchor, limit=2)
                                        for law in laws:
                                            related_laws.append({
                                                'title': f"{law.get('sheet_name', '')} - {law.get('article_title', '')}",
                                                'content': (law.get('full_text') or law.get('paragraph_content') or '')[:500],
                                                'article_num': law.get('article_num', ''),
                                                'sheet_name': law.get('sheet_name', ''),
                                                'source': 'Local FAQ Match',
                                                'matched_keyword': anchor
                                            })
                                            # GPT 컨텍스트용 policy_docs
                                            policy_docs.append({
                                                'segment': {
                                                    'content': law.get('full_text') or law.get('paragraph_content') or '',
                                                    'document': {'name': law.get('sheet_name', '')}
                                                },
                                                'score': 0.9
                                            })

                            # FAQ를 Dify 포맷으로 변환해서 GPT에 전달
                            faq_records = [{
                                'segment': {
                                    'content': f'faq_id":"{faq_id}";"question":"{faq_data["question"]}";"answer_text":"{faq_data["answer_text"]}"',
                                    'document': {'name': 'Local FAQ'}
                                },
                                'score': faq_score
                            }]

                            # ★ GPT로 답변 생성 (FAQ + 법령 컨텍스트)
                            app.logger.info('[Local FAQ Match] Generating answer with GPT context')
                            assistant_message = generate_answer_with_context(
                                user_message,
                                faq_records,
                                policy_docs if policy_docs else None
                            )

                            app.logger.info(f'[Local FAQ Match] Completed - found {len(related_laws)} laws')

                            # 이후 로직은 정상 흐름 따라감 (suggested_answer 생성 등)

                    else:
                        # 로컬 FAQ도 매칭 안 되면 OpenAI 폴백
                        app.logger.warning('Local FAQ search also failed, falling back to OpenAI')
                        assistant_message = generate_openai_response(session_id, user_message)
                else:
                    # No fallback, return error
                    raise Exception('Dify FAQ search failed and fallback is disabled')

            except Exception as e:
                app.logger.error(f'Error in Hybrid RAG mode: {str(e)}')
                app.logger.error(traceback.format_exc())
                if FALLBACK_TO_OPENAI:
                    app.logger.warning('Falling back to OpenAI due to error')
                    assistant_message = generate_openai_response(session_id, user_message)
                else:
                    raise

        # ===== OpenAI Direct Mode =====
        else:
            app.logger.info('Using OpenAI direct mode')
            assistant_message = generate_openai_response(session_id, user_message)

        # Add assistant message to session
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': assistant_message
        })

        # Generate suggested answer
        suggested_answer = generate_suggested_answer(
            user_message,
            assistant_message,
            matched_faq_id=matched_faq_id,
            related_laws=related_laws
        )

        # related_laws는 이미 [Action A]에서 SQLite 검색 결과로 채워져 있음
        # Dify에서 추가 법령 정보가 있으면 병합
        app.logger.info(f'[Final] Total related_laws from SQLite: {len(related_laws)}')

        app.logger.info(f'Successfully processed chat request for session {session_id}')

        # Build response with metadata
        response_data = {
            'success': True,
            'message': assistant_message,
            'suggested_answer': suggested_answer,
            'related_laws': related_laws,
            'session_id': session_id,
            'metadata': {
                'ai_mode': AI_MODE,
                'retrieval_count': len(retrieved_docs) if retrieved_docs else 0,
                'matched_faq_id': matched_faq_id,
                'extracted_keywords': keywords,
                'sqlite_laws_count': len(sqlite_laws)
            }
        }

        # Add retrieved documents info if available
        if retrieved_docs:
            response_data['metadata']['retrieved_docs'] = [
                {
                    'document_name': doc.get('segment', {}).get('document', {}).get('name', '알 수 없음'),
                    'score': doc.get('score', 0),
                    'content_preview': doc.get('segment', {}).get('content', '')[:100] + '...'
                }
                for doc in retrieved_docs
            ]

        return jsonify(response_data)

    except Exception as e:
        error_session = session_id if session_id else 'unknown'
        app.logger.error(f'Error in chat endpoint for session {error_session}: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e),
            'ai_mode': AI_MODE
        }), 500

def generate_openai_response(session_id, user_message):
    """Generate response using OpenAI directly (without RAG)"""
    app.logger.debug('Calling OpenAI API for session %s', session_id)
    start_time = datetime.now()

    # Prepare messages for OpenAI API
    messages = [
        {'role': 'system', 'content': '''당신은 대한민국 공무원이 민원인의 문의에 전문적으로 답변하기 위한 기금 민원처리 전문가 도우미입니다.

다음 지침을 따라주세요:
1. 항상 정중하고 공손한 어투를 사용하세요
2. 관련 법령이나 규정을 인용할 때는 정확한 조항을 명시하세요
3. 필요한 서류나 절차를 구체적으로 안내하세요
4. 추가 문의사항이 있는지 확인하세요'''}
    ]
    messages.extend(chat_sessions[session_id]['messages'])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )

    elapsed_time = (datetime.now() - start_time).total_seconds()
    api_logger.info(f'OpenAI API call completed in {elapsed_time:.2f}s - Tokens used: {response.usage.total_tokens}')

    assistant_message = response.choices[0].message.content
    app.logger.info(f'Generated response for session {session_id}: {assistant_message[:100]}...')

    return assistant_message

def extract_laws_from_retrieved_docs(retrieved_docs):
    """Extract related laws from Dify retrieved documents"""
    related_laws = []

    for doc in retrieved_docs:
        segment = doc.get('segment', {})
        content = segment.get('content', '')
        document_name = segment.get('document', {}).get('name', '알 수 없음')
        score = doc.get('score', 0)

        related_laws.append({
            'title': document_name,
            'content': content[:300] + ('...' if len(content) > 300 else ''),
            'score': score,
            'source': 'Dify Knowledge'
        })

    return related_laws

def call_dify_knowledge(user_message, top_k=3):
    """
    Call Dify Knowledge API to retrieve relevant documents using RAG

    Args:
        user_message: User's query
        top_k: Number of top results to retrieve (default: 3)

    Returns:
        dict: Response containing retrieved documents and generated answer
    """
    try:
        app.logger.debug('Calling Dify Knowledge API')
        start_time = datetime.now()

        # Dify Knowledge Retrieve API endpoint
        url = f"{DIFY_API_URL}/datasets/{DIFY_DATASET_ID}/retrieve"

        headers = {
            'Authorization': f'Bearer {DIFY_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "query": user_message,
            "retrieval_model": {
                "search_method": "semantic_search",  # or "full_text_search", "hybrid_search"
                "reranking_enable": False,  # Reranking 비활성화 (OpenAI API 불필요)
                "top_k": top_k,
                "score_threshold_enabled": True,
                "score_threshold": 0.5
            }
        }

        app.logger.debug(f"Dify API Request URL: {url}")
        app.logger.debug(f"Dify API Request Payload: {json.dumps(payload, ensure_ascii=False)}")

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Extract retrieved documents
        records = result.get('records', [])
        app.logger.info(f"Dify Knowledge API call completed in {elapsed_time:.2f}s - Retrieved {len(records)} documents")
        api_logger.info(f"Dify RAG retrieved {len(records)} documents for query: {user_message[:100]}")

        # Log retrieved documents
        for idx, record in enumerate(records):
            score = record.get('score', 0)
            segment = record.get('segment', {})
            content_preview = segment.get('content', '')[:100]
            app.logger.debug(f"Document {idx+1} - Score: {score:.3f} - Content: {content_preview}...")

        return {
            'success': True,
            'records': records,
            'query': user_message,
            'elapsed_time': elapsed_time
        }

    except requests.exceptions.Timeout:
        app.logger.error('Dify API request timeout')
        return {
            'success': False,
            'error': 'Dify API timeout',
            'records': []
        }
    except requests.exceptions.RequestException as e:
        app.logger.error(f'Dify API request failed: {str(e)}')
        app.logger.error(f'Response: {e.response.text if hasattr(e, "response") else "No response"}')
        return {
            'success': False,
            'error': str(e),
            'records': []
        }
    except Exception as e:
        app.logger.error(f'Unexpected error calling Dify API: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return {
            'success': False,
            'error': str(e),
            'records': []
        }

def extract_faq_id_from_content(record):
    """
    Extract faq_id from Dify search result

    Args:
        record: Single record from Dify API response

    Returns:
        str: faq_id (e.g., "FAQ-협약체결-0002") or None
    """
    try:
        content = record.get('segment', {}).get('content', '')

        # Method 1: Regex search for faq_id in CSV format
        # Content format: faq_id":"FAQ-협약체결-0002";"question":"..."
        match = re.search(r'faq_id":"(.+?)"', content)
        if match:
            faq_id = match.group(1)
            app.logger.debug(f"Extracted faq_id from content: {faq_id}")
            return faq_id

        # Method 2: Check document name
        doc_name = record.get('segment', {}).get('document', {}).get('name', '')
        if doc_name and doc_name.startswith('FAQ-') and doc_name.endswith('.md'):
            faq_id = doc_name[:-3]  # Remove .md extension
            app.logger.debug(f"Extracted faq_id from document name: {faq_id}")
            return faq_id

        app.logger.warning("Could not extract faq_id from record")
        return None

    except Exception as e:
        app.logger.error(f"Error extracting faq_id: {e}")
        return None

def get_policy_anchor(faq_id):
    """
    Get policy_anchor from local mapping table

    Args:
        faq_id: FAQ identifier (e.g., "FAQ-협약체결-0002")

    Returns:
        str: policy_anchor or None
    """
    if not faq_id:
        return None

    policy_anchor = faq_policy_map.get(faq_id)

    if policy_anchor:
        app.logger.debug(f"Mapped {faq_id} -> {policy_anchor[:50]}...")
    else:
        app.logger.warning(f"No policy_anchor found for faq_id: {faq_id}")

    return policy_anchor

def get_faq_direct_answer(faq_id):
    """
    FAQ 답변을 직접 조회 (높은 유사도 매칭 시 GPT 호출 없이 사용)

    Args:
        faq_id: FAQ identifier (e.g., "FAQ-협약체결-0002")

    Returns:
        dict: {'answer_text': str, 'policy_anchor': str, 'question': str} or None
    """
    global faq_df_global

    if faq_df_global is None or faq_id is None:
        return None

    try:
        row = faq_df_global[faq_df_global['faq_id'] == faq_id]
        if row.empty:
            app.logger.warning(f"FAQ not found for direct answer: {faq_id}")
            return None

        result = {
            'faq_id': faq_id,
            'answer_text': str(row['answer_text'].values[0]) if pd.notna(row['answer_text'].values[0]) else '',
            'policy_anchor': str(row['policy_anchor'].values[0]) if pd.notna(row['policy_anchor'].values[0]) else '',
            'question': str(row['question'].values[0]) if pd.notna(row['question'].values[0]) else ''
        }
        app.logger.info(f"[FAQ Direct] Retrieved answer for {faq_id}")
        return result

    except Exception as e:
        app.logger.error(f"Error getting FAQ direct answer: {e}")
        return None

def format_faq_as_html(faq_data, user_message):
    """
    FAQ 답변을 HTML 포맷으로 변환 (suggested_answer용)

    Args:
        faq_data: get_faq_direct_answer()의 반환값
        user_message: 사용자 질문

    Returns:
        str: HTML 포맷 답변
    """
    if not faq_data:
        return "<p>답변을 찾을 수 없습니다.</p>"

    answer_text = faq_data.get('answer_text', '')

    # 줄바꿈을 <br>로 변환
    formatted_answer = answer_text.replace('\n', '<br>')

    return f"""
<div class="answer-section">
    <h4>📌 답변</h4>
    <p>{formatted_answer}</p>
</div>
<div class="answer-section">
    <h4>💡 참고사항</h4>
    <p>관련 법령은 오른쪽 '관련법령' 탭에서 확인하실 수 있습니다.</p>
</div>
"""

def search_faq_local(user_message, threshold=0.6):
    """
    로컬 faq_topic.xlsx에서 유사한 FAQ 검색 (Dify 실패 시 폴백용)
    간단한 키워드 매칭 기반 검색

    Args:
        user_message: 사용자 질문
        threshold: 매칭 임계값 (0~1)

    Returns:
        dict: {'faq_id': str, 'score': float, 'question': str} or None
    """
    global faq_df_global

    if faq_df_global is None:
        return None

    try:
        # 사용자 질문에서 키워드 추출
        user_keywords = set(user_message.replace('?', '').replace('？', '').split())

        best_match = None
        best_score = 0

        for _, row in faq_df_global.iterrows():
            faq_question = str(row.get('question', ''))
            faq_keywords = set(faq_question.replace('?', '').replace('？', '').split())

            # Jaccard 유사도 계산
            if len(user_keywords | faq_keywords) > 0:
                score = len(user_keywords & faq_keywords) / len(user_keywords | faq_keywords)

                # 정확히 일치하는 경우 보너스
                if user_message.strip() == faq_question.strip():
                    score = 1.0

                if score > best_score:
                    best_score = score
                    best_match = {
                        'faq_id': row.get('faq_id'),
                        'score': score,
                        'question': faq_question
                    }

        if best_match and best_score >= threshold:
            app.logger.info(f'[Local FAQ] Found match: {best_match["faq_id"]} (score: {best_score:.2f})')
            return best_match

        app.logger.info(f'[Local FAQ] No match found above threshold {threshold} (best: {best_score:.2f})')
        return None

    except Exception as e:
        app.logger.error(f'Error in local FAQ search: {e}')
        return None

def generate_answer_with_context(user_message, faq_records, policy_docs):
    """
    Generate answer using FAQ + Policy documents as context

    Args:
        user_message: User's question
        faq_records: FAQ records from Dify search
        policy_docs: Policy document records from Dify search (can be None/empty)

    Returns:
        str: Generated answer
    """
    try:
        # Build FAQ context
        faq_context = ""
        if faq_records:
            for idx, record in enumerate(faq_records[:2], 1):  # Top 2 FAQs
                content = record.get('segment', {}).get('content', '')
                # Extract question and answer from CSV format
                # Format: faq_id":"FAQ-...";"question":"질문";"answer_text":"답변"
                question_match = re.search(r'question":"(.+?)"', content)
                answer_match = re.search(r'answer_text":"(.+?)"', content)

                if question_match and answer_match:
                    question = question_match.group(1)
                    answer = answer_match.group(1)
                    faq_context += f"\n[참고 FAQ {idx}]\n질문: {question}\n답변: {answer}\n"
                else:
                    # Fallback: use first 500 chars
                    faq_context += f"\n[참고 FAQ {idx}]\n{content[:500]}\n"

        # Build policy documents context
        policy_context = ""
        if policy_docs:
            for idx, doc in enumerate(policy_docs[:3], 1):  # Top 3 policy docs
                content = doc.get('segment', {}).get('content', '')
                policy_context += f"\n[참고 법령 {idx}]\n{content[:500]}\n"

        # System prompt
        system_prompt = f"""당신은 대한민국 ICT 기금사업 민원처리 전문가입니다.

다음 자료를 참고하여 질문에 답변하세요:

{faq_context}

{policy_context}

답변 시 지침:
1. 위 참고 자료의 내용을 정확히 활용하세요
2. 법령이나 규정을 인용할 때는 정확한 조항을 명시하세요
3. 필요한 서류나 절차를 구체적으로 안내하세요
4. 참고 자료에 없는 내용은 추측하지 말고, 추가 확인이 필요하다고 안내하세요
5. 정중하고 공손한 어투를 사용하세요"""

        # Call OpenAI API
        start_time = datetime.now()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        elapsed_time = (datetime.now() - start_time).total_seconds()
        assistant_message = response.choices[0].message.content

        api_logger.info(f'Answer generated in {elapsed_time:.2f}s - Tokens: {response.usage.total_tokens}')
        app.logger.debug(f'Generated answer: {assistant_message[:100]}...')

        return assistant_message

    except Exception as e:
        app.logger.error(f'Error generating answer with context: {str(e)}')
        app.logger.error(traceback.format_exc())
        raise

def generate_answer_with_dify_rag(user_message, retrieved_docs, prompt_template=None):
    """
    Generate answer using OpenAI with Dify retrieved documents as context

    Args:
        user_message: User's query
        retrieved_docs: Documents retrieved from Dify Knowledge
        prompt_template: Optional custom prompt template

    Returns:
        str: Generated answer
    """
    try:
        app.logger.debug('Generating answer with RAG context')

        # Build context from retrieved documents
        context_parts = []
        for idx, record in enumerate(retrieved_docs):
            segment = record.get('segment', {})
            content = segment.get('content', '')
            dataset_name = record.get('dataset_name', '문서')
            document_name = segment.get('document', {}).get('name', '알 수 없음')
            score = record.get('score', 0)

            context_parts.append(f"""
[참고자료 {idx+1}] (관련도: {score:.2f})
출처: {dataset_name} - {document_name}
내용: {content}
""")

        context = "\n".join(context_parts)

        # Use custom prompt template or default
        if prompt_template:
            system_prompt = prompt_template
        else:
            system_prompt = f"""당신은 대한민국 공무원이 민원인의 문의에 전문적으로 답변하기 위한 기금 민원처리 전문가 도우미입니다.

다음 참고자료를 바탕으로 답변해주세요:

{context}

답변 시 다음 지침을 따라주세요:
1. 항상 정중하고 공손한 어투를 사용하세요
2. 위 참고자료의 내용을 정확히 인용하고 활용하세요
3. 참고자료에 명시된 법령이나 규정이 있다면 정확한 조항을 인용하세요
4. 필요한 서류나 절차를 구체적으로 안내하세요
5. 참고자료에 없는 내용은 추측하지 말고, 추가 확인이 필요하다고 안내하세요
6. 추가 문의사항이 있는지 확인하세요"""

        # Call OpenAI with RAG context
        start_time = datetime.now()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        elapsed_time = (datetime.now() - start_time).total_seconds()
        assistant_message = response.choices[0].message.content

        api_logger.info(f'RAG answer generated in {elapsed_time:.2f}s - Tokens: {response.usage.total_tokens}')

        return assistant_message

    except Exception as e:
        app.logger.error(f'Error generating RAG answer: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        raise

def generate_suggested_answer(user_message, assistant_response, matched_faq_id=None, related_laws=None):
    """
    FAQ RAG 기반 민원처리 답변 생성

    Args:
        user_message: 사용자 질문
        assistant_response: 챗봇 답변 (FAQ RAG 기반)
        matched_faq_id: 매칭된 FAQ ID (선택)
        related_laws: 관련 법령 리스트 (선택, 별도 탭에 표시됨)

    Returns:
        str: HTML 형식의 민원처리 답변
    """
    try:
        app.logger.debug(f'Generating suggested answer (FAQ ID: {matched_faq_id})')

        # ========================================
        # 📝 답변지침란 (나중에 수정 가능)
        # ========================================
        system_instruction = """당신은 ICT 기금사업규정 전문가입니다.
기금규정 업무를 담당하는 직원들의 질문에 답변하는 역할입니다.
업무 조언 형식으로 답변하며, 문의처 안내는 필요하지 않습니다.

⚠️ 중요 규칙:
- 관련 법령은 언급하지 마세요 (별도 탭에 표시됨)
- 문의처(전화번호, 이메일)는 포함하지 마세요
- 깔끔하고 보기 좋은 HTML로 작성하세요

📋 HTML 포맷 지침:
- <div class="answer-section">로 각 섹션을 감싸세요
- 제목은 <h4>를 사용하세요 (예: <h4>📌 핵심 답변</h4>)
- 본문은 <p>를 사용하세요
- 목록은 <ul><li>를 사용하세요
- 절차/단계는 <ol><li>를 사용하세요
- 강조는 <strong>을 사용하세요
- 여백을 위해 <br> 대신 별도 <p> 태그 사용

📝 권장 섹션 구조 (상황에 맞게 선택):
- 📌 핵심 답변 / 개요
- 📝 작성 내용 / 필수 항목 / 포함되어야 할 내용
- 📋 필요 서류 / 준비 서류
- 🔄 처리 절차 / 진행 과정
- ⏰ 처리 기간 / 소요 시간
- ⚠️ 주의사항 / 유의사항
- 💡 참고사항 / 추가 정보 (관련 처리지침 포함)

✅ 좋은 예시:
<div class="answer-section">
    <h4>📌 핵심 답변</h4>
    <p>사업비 교부는 다음과 같은 절차로 진행됩니다.</p>
</div>

<div class="answer-section">
    <h4>📝 필요 서류</h4>
    <ul>
        <li><strong>협약서:</strong> 사업 협약 체결 후 제출</li>
        <li><strong>계좌 사본:</strong> 사업자 명의 계좌</li>
    </ul>
</div>

<div class="answer-section">
    <h4>🔄 처리 절차</h4>
    <ol>
        <li>협약 체결 및 서류 제출</li>
        <li>서류 검토 (3-5일 소요)</li>
        <li>교부 승인 및 입금</li>
    </ol>
</div>

<div class="answer-section">
    <h4>💡 참고사항</h4>
    <p>관련 처리지침: ICT 기금사업 운영지침 제XX조에 따라 처리됩니다.</p>
    <p>추가로 필요한 정보가 있으면 언제든 문의하세요.</p>
</div>
"""
        # ========================================

        prompt = f"""{system_instruction}

질문: {user_message}
참고 답변: {assistant_response}

위 내용을 바탕으로 직원 업무 조언 형식의 답변을 작성하세요.
반드시 위의 HTML 포맷 지침을 따라 깔끔하고 보기 좋게 구조화하세요.

✅ 필수 포함 사항:
- 참고사항 섹션에 관련 처리지침(운영지침, 시행세칙 등)을 반드시 포함하세요
- 처리지침이 참고 답변에 있다면 반드시 명시하세요

⚠️ 중요: HTML 코드만 출력하세요. ```html``` 같은 마크다운 코드 블록 태그는 절대 사용하지 마세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,  # 낮춰서 더 일관성 있는 답변
            max_tokens=800
        )

        api_logger.info(f'Suggested answer generated - Tokens used: {response.usage.total_tokens}')

        # 마크다운 코드 블록 제거 (```html, ``` 등)
        answer = response.choices[0].message.content
        answer = answer.replace('```html', '').replace('```', '').strip()

        app.logger.debug(f'Generated answer length: {len(answer)}')

        return answer

    except Exception as e:
        app.logger.error(f'Error generating suggested answer: {str(e)}')
        app.logger.error(traceback.format_exc())
        return "<p>답변 생성 중 오류가 발생했습니다.</p>"

def generate_related_laws(user_message):
    """Generate related laws and regulations"""
    # Simplified version - in production, this would query a legal database
    common_laws = {
        '건축': [
            {
                'title': '건축법',
                'content': '제11조 (건축허가) 건축물을 건축하거나 대수선하려는 자는 특별자치시장ㆍ특별자치도지사 또는 시장ㆍ군수ㆍ구청장의 허가를 받아야 한다.'
            },
            {
                'title': '건축법 시행령',
                'content': '제6조 (적용의 완화) 건축물의 대지가 지역ㆍ지구 또는 구역에 걸치는 경우 그 건축물과 대지의 전부에 대하여 대지의 과반이 속하는 지역ㆍ지구 또는 구역 안의 건축물 및 대지에 관한 규정을 적용한다.'
            }
        ],
        '도로': [
            {
                'title': '도로법',
                'content': '제61조 (도로점용허가) 도로를 점용하려는 자는 도로관리청의 허가를 받아야 한다.'
            }
        ],
        '환경': [
            {
                'title': '환경정책기본법',
                'content': '제3조 (기본이념) 환경의 질적인 향상과 그 보전을 통한 쾌적한 환경의 조성 및 이를 통한 인간과 환경간의 조화와 균형의 유지는 국민의 건강과 문화적인 생활의 향유 및 국토의 보전과 항구적인 국가발전에 필수불가결한 요소임을 인식하고...'
            }
        ]
    }
    
    # Simple keyword matching
    for keyword, laws in common_laws.items():
        if keyword in user_message:
            return laws
    
    # Default laws
    return [
        {
            'title': '민원 처리에 관한 법률',
            'content': '제9조 (민원의 처리기간) 행정기관의 장은 민원의 처리기간을 종류별로 미리 정하여 민원인이 이를 알 수 있도록 게시하거나 민원편람에 수록하는 등의 방법으로 공표하여야 한다.'
        },
        {
            'title': '행정절차법',
            'content': '제17조 (처분의 신청) 행정청에 처분을 구하는 신청은 문서로 하여야 한다. 다만, 다른 법령등에 특별한 규정이 있는 경우와 행정청이 미리 다른 방법을 정하여 공시한 경우에는 그러하지 아니하다.'
        }
    ]

# ========================================
# 관련 법령 API 엔드포인트
# ========================================

@app.route('/api/laws/master-tree', methods=['GET'])
def get_law_master_tree():
    """
    [2단계] 마스터 트리 데이터 반환
    서버 시작 시 로드한 전역 변수를 그대로 반환 (DB 실시간 조회 X)
    """
    try:
        app.logger.info(f'Master tree requested: {len(LAW_MASTER_TREE)} sheets')
        return jsonify({
            'success': True,
            'data': LAW_MASTER_TREE,
            'sheet_count': len(LAW_MASTER_TREE),
            'article_count': sum(len(v) for v in LAW_MASTER_TREE.values())
        })
    except Exception as e:
        app.logger.error(f'Error getting master tree: {str(e)}')
        return jsonify({'success': False, 'error': str(e), 'data': {}}), 500

@app.route('/api/laws/sheets', methods=['GET'])
def get_sheets():
    """Sheet 목록 조회 (지침 목록)"""
    try:
        sheets = database.get_sheet_list()
        app.logger.info(f'Retrieved {len(sheets)} sheets')
        return jsonify({'sheets': sheets})
    except Exception as e:
        app.logger.error(f'Error getting sheets: {str(e)}')
        return jsonify({'error': str(e), 'sheets': []}), 500

@app.route('/api/laws/articles', methods=['GET'])
def get_articles():
    """조항 목록 조회"""
    try:
        sheet_name = request.args.get('sheet_name')
        if not sheet_name:
            return jsonify({'error': 'sheet_name is required', 'articles': []}), 400

        articles = database.get_articles_by_sheet(sheet_name)
        app.logger.info(f'Retrieved {len(articles)} articles for sheet: {sheet_name}')
        return jsonify({'articles': articles})
    except Exception as e:
        app.logger.error(f'Error getting articles: {str(e)}')
        return jsonify({'error': str(e), 'articles': []}), 500

@app.route('/api/laws/paragraphs', methods=['GET'])
def get_paragraphs():
    """항 목록 조회"""
    try:
        sheet_name = request.args.get('sheet_name')
        article_num = request.args.get('article_num')

        if not sheet_name or not article_num:
            return jsonify({'error': 'sheet_name and article_num are required', 'paragraphs': []}), 400

        paragraphs = database.get_paragraphs_by_article(sheet_name, article_num)
        app.logger.info(f'Retrieved {len(paragraphs)} paragraphs for {sheet_name} - {article_num}')
        return jsonify({'paragraphs': paragraphs})
    except Exception as e:
        app.logger.error(f'Error getting paragraphs: {str(e)}')
        return jsonify({'error': str(e), 'paragraphs': []}), 500

@app.route('/api/new-session', methods=['POST'])
def new_session():
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = {
        'messages': [],
        'created_at': datetime.now()
    }
    app.logger.info(f'New session created: {session_id} from IP: {request.remote_addr}')
    return jsonify({'session_id': session_id})

@app.route('/api/chat/confirm', methods=['POST'])
def chat_confirm():
    """
    1단계: 질문 요약 및 확인
    사용자 질문을 이해하고 확인 메시지만 생성 (FAQ RAG 호출 X)
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))

        app.logger.info(f'[CONFIRM] Question from session {session_id}: {user_message[:100]}...')

        # 질문 요약/확인 프롬프트
        confirmation_prompt = f"""다음 질문을 이해하고 간단히 요약하여 되물어주세요.

사용자 질문: {user_message}

답변 형식:
"[요약된 내용]에 대해 문의하시는 것이 맞나요?"

예시:
- 질문: "사업비 교부는 어떻게 받나요?"
  → "사업비 교부 절차에 대해 문의하시는 것이 맞나요?"
- 질문: "인건비 계산 방법 알려줘"
  → "인건비 산정 방법에 대해 문의하시는 것이 맞나요?"
- 질문: "협약 체결 시 필요한 서류는?"
  → "협약 체결 시 필요한 서류에 대해 문의하시는 것이 맞나요?"

간결하고 정중하게 답변하세요."""

        start_time = datetime.now()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{'role': 'user', 'content': confirmation_prompt}],
            temperature=0.3,
            max_tokens=100
        )

        elapsed_time = (datetime.now() - start_time).total_seconds()
        confirmation_message = response.choices[0].message.content

        app.logger.info(f'[CONFIRM] Generated confirmation in {elapsed_time:.2f}s: {confirmation_message}')
        api_logger.info(f'Confirmation generated - Tokens: {response.usage.total_tokens}')

        return jsonify({
            'success': True,
            'message': confirmation_message,
            'session_id': session_id,
            'requires_confirmation': True
        })

    except Exception as e:
        app.logger.error(f'Error in confirmation: {str(e)}')
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.logger.info('='*50)
    app.logger.info('Starting Civil Complaint Chatbot Application')
    app.logger.info(f'Debug Mode: {app.debug}')
    app.logger.info(f'Log files location: logs/')
    app.logger.info('='*50)

    # 터미널에 명확하게 URL 출력
    print('\n' + '='*60)
    print('Civil Complaint Chatbot Server Started!')
    print('='*60)
    print(f'Local:   http://localhost:5000')
    print(f'Network: http://127.0.0.1:5000')
    print('='*60)
    print('Press CTRL+C to quit\n')

    app.run(debug=True, port=5000, host='127.0.0.1')