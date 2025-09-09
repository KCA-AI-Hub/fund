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

# Store chat sessions in memory (in production, use a database)
chat_sessions = {}

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
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
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
        
        # Prepare messages for OpenAI API
        messages = [
            {'role': 'system', 'content': '''당신은 대한민국 공무원으로서 민원인의 문의에 친절하고 전문적으로 답변하는 민원처리 전문가입니다.
            
다음 지침을 따라주세요:
1. 항상 정중하고 공손한 어투를 사용하세요
2. 관련 법령이나 규정을 인용할 때는 정확한 조항을 명시하세요
3. 민원인이 이해하기 쉽도록 전문용어는 풀어서 설명하세요
4. 필요한 서류나 절차를 구체적으로 안내하세요
5. 추가 문의사항이 있는지 확인하세요'''}
        ]
        messages.extend(chat_sessions[session_id]['messages'])
        
        # Generate response using OpenAI
        app.logger.debug('Calling OpenAI API for session %s', session_id)
        start_time = datetime.now()
        
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
        
        # Add assistant message to session
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': assistant_message
        })
        
        # Generate suggested answer and related laws (simplified version)
        suggested_answer = generate_suggested_answer(user_message, assistant_message)
        related_laws = generate_related_laws(user_message)
        
        app.logger.info(f'Successfully processed chat request for session {session_id}')
        return jsonify({
            'success': True,
            'message': assistant_message,
            'suggested_answer': suggested_answer,
            'related_laws': related_laws,
            'session_id': session_id
        })
        
    except Exception as e:
        app.logger.error(f'Error in chat endpoint for session {session_id}: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_suggested_answer(user_message, assistant_response):
    """Generate a formal answer template based on the chat"""
    try:
        app.logger.debug('Generating suggested answer')
        prompt = f"""다음 민원 문의와 답변을 바탕으로 공식적인 민원 답변서를 작성해주세요.

민원 문의: {user_message}
초기 답변: {assistant_response}

답변서는 다음 형식을 따라주세요:
1. 인사말
2. 민원 내용 확인
3. 구체적인 답변
4. 필요한 조치사항
5. 맺음말

공식적이고 정중한 어투로 작성해주세요."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7,
            max_tokens=800
        )
        
        api_logger.info(f'Suggested answer generated - Tokens used: {response.usage.total_tokens}')
        return response.choices[0].message.content
    except Exception as e:
        app.logger.error(f'Error generating suggested answer: {str(e)}')
        return "답변 생성 중 오류가 발생했습니다."

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

if __name__ == '__main__':
    app.logger.info('='*50)
    app.logger.info('Starting Civil Complaint Chatbot Application')
    app.logger.info(f'Debug Mode: {app.debug}')
    app.logger.info(f'Log files location: logs/')
    app.logger.info('='*50)
    app.run(debug=True, port=5000)