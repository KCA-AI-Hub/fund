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

# Load FAQ policy mapping from faq_topic.xlsx
faq_policy_map = {}
try:
    faq_file_path = os.path.join(os.path.dirname(__file__), 'data', 'faq_topic.xlsx')
    if os.path.exists(faq_file_path):
        faq_df = pd.read_excel(faq_file_path)
        faq_policy_map = dict(zip(faq_df['faq_id'], faq_df['policy_anchor']))
        app.logger.info(f"Loaded {len(faq_policy_map)} FAQ policy mappings from {faq_file_path}")
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

        # ===== Hybrid RAG Mode (Dify + Local Mapping) =====
        if AI_MODE == 'dify':
            try:
                app.logger.info('Using Hybrid RAG mode (Dify FAQ + Local Policy Mapping)')

                # STEP 1: Search FAQ in Dify Knowledge
                app.logger.info('Step 1: Searching FAQ in Dify Knowledge')
                faq_result = call_dify_knowledge(user_message, top_k=3)

                if faq_result['success'] and faq_result['records']:
                    retrieved_docs = faq_result['records']
                    app.logger.info(f'Retrieved {len(retrieved_docs)} FAQ records')

                    # STEP 2: Extract faq_id from best match
                    app.logger.info('Step 2: Extracting faq_id from best match')
                    best_faq = retrieved_docs[0]
                    faq_id = extract_faq_id_from_content(best_faq)

                    if faq_id:
                        app.logger.info(f'Extracted faq_id: {faq_id}')
                        matched_faq_id = faq_id

                        # STEP 3: Get policy_anchor from local mapping
                        app.logger.info('Step 3: Getting policy_anchor from local mapping')
                        policy_anchor = get_policy_anchor(faq_id)

                        if policy_anchor:
                            app.logger.info(f'Mapped policy_anchor: {policy_anchor[:100]}...')

                            # STEP 4: Search policy documents in Dify
                            app.logger.info('Step 4: Searching policy documents in Dify')
                            policy_docs = []
                            policy_anchors = [p.strip() for p in policy_anchor.split(';')]

                            for idx, anchor in enumerate(policy_anchors[:2], 1):  # Max 2 anchors
                                app.logger.debug(f'Searching policy doc {idx}: {anchor[:50]}...')
                                policy_result = call_dify_knowledge(anchor, top_k=2)
                                if policy_result['success'] and policy_result['records']:
                                    policy_docs.extend(policy_result['records'])
                                    app.logger.debug(f'Found {len(policy_result["records"])} policy docs')

                            app.logger.info(f'Total policy docs retrieved: {len(policy_docs)}')

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

                # Fallback to OpenAI if Dify fails or no results
                elif FALLBACK_TO_OPENAI:
                    app.logger.warning('Dify FAQ search failed or no results, falling back to OpenAI')
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

        # Generate related_laws if not already set by Hybrid RAG
        if not related_laws:
            if AI_MODE == 'dify' and retrieved_docs:
                related_laws = extract_laws_from_retrieved_docs(retrieved_docs)
            else:
                related_laws = generate_related_laws(user_message)

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
                'matched_faq_id': matched_faq_id
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
                "reranking_enable": True,
                "reranking_model": {
                    "reranking_provider_name": "",
                    "reranking_model_name": ""
                },
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
    print('🚀 Civil Complaint Chatbot Server Started!')
    print('='*60)
    print(f'📍 Local:   http://localhost:5000')
    print(f'📍 Network: http://127.0.0.1:5000')
    print('='*60)
    print('Press CTRL+C to quit\n')

    app.run(debug=True, port=5000, host='127.0.0.1')