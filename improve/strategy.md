# 민원처리 챗봇 - 기술 아키텍처 문서

> **Hybrid RAG Architecture**: Dify (FAQ Semantic Search) + SQLite (Law Keyword Search) + OpenAI GPT (Generation)

---

## 시스템 개요

### 핵심 컴포넌트

| 컴포넌트 | 기술 스택 | 역할 |
|----------|-----------|------|
| **Backend** | Flask (Python 3.13+) | REST API, 비즈니스 로직 |
| **Frontend** | Jinja2 + Vanilla JS | ChatGPT 스타일 UI |
| **FAQ Search** | Dify RAG API | Semantic Search + Reranking |
| **Law Search** | SQLite + LIKE Query | Keyword-based Retrieval |
| **Generation** | OpenAI GPT-4o-mini | Context-based Response |

### 데이터 분리 전략

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid RAG Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FAQ (102개)              법령 (1,063개)                     │
│      │                        │                              │
│      ▼                        ▼                              │
│  ┌────────────┐          ┌────────────┐                      │
│  │   Dify     │          │  SQLite    │                      │
│  │ Knowledge  │          │    DB      │                      │
│  └────────────┘          └────────────┘                      │
│      │                        │                              │
│      │ Semantic Search        │ LIKE Query                   │
│      │ + Reranking            │ + Index                      │
│      ▼                        ▼                              │
│  ┌─────────────────────────────────────┐                     │
│  │         Context Builder              │                     │
│  │   (FAQ answers + Law full_text)     │                     │
│  └─────────────────────────────────────┘                     │
│                    │                                          │
│                    ▼                                          │
│  ┌─────────────────────────────────────┐                     │
│  │       OpenAI GPT-4o-mini             │                     │
│  │   (RAG-based Response Generation)   │                     │
│  └─────────────────────────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 워크플로우 (Request Flow)

### 전체 흐름 (한 줄 요약)

```
User Query → Flask API → Dify FAQ Search → SQLite Law Search → GPT Generation → JSON Response → Frontend Render
```

### 상세 처리 플로우

```
┌─────────────────────────────────────────────────────────────┐
│  POST /api/chat                                              │
│  Body: { message: "사업비 교부는 어떻게 받나요?",            │
│          session_id: "uuid" }                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  [Action A] Keyword Extraction + SQLite Search               │
│  ─────────────────────────────────────────────────────────── │
│  1. extract_keywords_from_question(user_message)             │
│     → ["사업비", "교부"]                                      │
│  2. search_laws_by_keywords(keywords, limit=5)               │
│     → SQLite LIKE query on full_text, article_title, tag    │
│  3. related_laws[] ← 검색 결과 즉시 저장                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  [Action B] Dify FAQ RAG Search                              │
│  ─────────────────────────────────────────────────────────── │
│  1. call_dify_knowledge(user_message, top_k=3)               │
│     → POST {DIFY_API_URL}/datasets/{DATASET_ID}/retrieve     │
│     → Semantic Search + Reranking                            │
│  2. extract_faq_id_from_content(best_faq)                    │
│     → "FAQ-사업비-0005"                                       │
│  3. get_policy_anchor(faq_id)                                │
│     → faq_topic.xlsx 매핑 테이블 조회                        │
│     → "기금운영지침 제10조; 사업비 교부"                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  [Action C] Policy Document Search (SQLite)                  │
│  ─────────────────────────────────────────────────────────── │
│  1. policy_anchors = policy_anchor.split(';')                │
│  2. for anchor in policy_anchors[:2]:                        │
│        database.search_laws(anchor, limit=2)                 │
│  3. Convert to Dify-compatible format                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  [Action D] GPT Response Generation                          │
│  ─────────────────────────────────────────────────────────── │
│  1. generate_answer_with_context(                            │
│        user_message, faq_records, policy_docs)               │
│     → System Prompt + FAQ Context + Law Context              │
│     → OpenAI API (gpt-4o-mini, temp=0.7, max_tokens=1000)   │
│  2. generate_suggested_answer(...)                           │
│     → HTML formatted answer (temp=0.3, max_tokens=800)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Response JSON                                               │
│  {                                                           │
│    "success": true,                                          │
│    "message": "GPT 생성 답변",                               │
│    "suggested_answer": "<div class='answer-section'>...</div>",│
│    "related_laws": [{title, content, article_num, ...}],    │
│    "session_id": "uuid",                                     │
│    "metadata": {                                             │
│      "ai_mode": "dify",                                      │
│      "matched_faq_id": "FAQ-사업비-0005",                    │
│      "extracted_keywords": ["사업비", "교부"],               │
│      "sqlite_laws_count": 5                                  │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 프로젝트 구조

```
test_dify/
│
├── app.py                      # Flask 메인 서버 (Hybrid RAG 로직)
├── database.py                 # SQLite 쿼리 함수
│
├── data/
│   ├── chatbot.db             # SQLite DB (laws 테이블)
│   ├── law.xlsx               # 법령 원본 (14 sheets, 1,063 rows)
│   └── faq_topic.xlsx         # FAQ 원본 + policy_anchor 매핑
│
├── templates/
│   ├── base.html              # Jinja2 베이스 템플릿
│   └── index.html             # 메인 UI (3-column layout)
│
├── static/
│   ├── css/styles.css         # Dark theme CSS
│   └── js/app.js              # Frontend 로직 (ComplaintChatbot class)
│
├── logs/
│   ├── app.log                # 일반 로그
│   └── api_calls.log          # API 호출 로그
│
├── improve/
│   ├── strategy.md            # 이 문서 (개발자용)
│   └── strategy_easy.md       # 비전공자용 가이드
│
└── .env                        # 환경 변수 (API Keys)
```

---

## 데이터베이스 스키마

### SQLite: laws 테이블

```sql
CREATE TABLE laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id TEXT UNIQUE NOT NULL,          -- "중앙기관_제10조_제1항"
    law_title TEXT NOT NULL,              -- "ICT 기금사업 운영지침"
    sheet_name TEXT NOT NULL,             -- Excel Sheet 이름 (14개)
    chapter_num TEXT,
    chapter_title TEXT,
    article_num TEXT,                     -- "10" (조 번호)
    article_title TEXT,                   -- "사업비 교부"
    paragraph_num REAL,                   -- 1.0, 2.0 (항 번호)
    paragraph_content TEXT,               -- 항 내용
    clause_num REAL,
    clause_content TEXT,
    item_num TEXT,
    item_content TEXT,
    full_text TEXT NOT NULL,              -- 전체 텍스트 (검색용)
    first_effective_date DATE,
    amendment_date DATE,
    is_active BOOLEAN DEFAULT 1,
    tags TEXT                             -- 태그 (comma-separated)
);

-- Indexes
CREATE INDEX idx_sheet_name ON laws(sheet_name);
CREATE INDEX idx_article_num ON laws(article_num);
CREATE INDEX idx_tags ON laws(tags);
CREATE INDEX idx_full_text ON laws(full_text);
```

### 메모리: LAW_MASTER_TREE (서버 시작 시 로드)

```python
# 3-level 계층 구조 (JSON-like)
LAW_MASTER_TREE = {
    "중앙기관 시행지침서": {
        "제1조": {
            "title": "목적",
            "paragraphs": ["제1항: ...", "제2항: ..."]
        },
        "제2조": { ... }
    },
    "사업비 집행지침": { ... }
}
```

---

## 핵심 함수 레퍼런스

### app.py

| 함수 | 라인 | 역할 |
|------|------|------|
| `build_law_master_tree()` | 103-192 | 서버 시작 시 SQLite → 메모리 트리 로드 |
| `extract_keywords_from_question()` | 238-256 | 불용어 제거 후 키워드 추출 |
| `search_laws_by_keywords()` | 258-298 | 키워드 기반 법령 검색 (중복 제거) |
| `call_dify_knowledge()` | 571-655 | Dify RAG API 호출 |
| `extract_faq_id_from_content()` | 657-690 | Dify 응답에서 faq_id 파싱 |
| `get_policy_anchor()` | 692-712 | faq_id → policy_anchor 매핑 |
| `generate_answer_with_context()` | 714-791 | FAQ + 법령 컨텍스트로 GPT 답변 |
| `generate_suggested_answer()` | 868-979 | HTML 포맷 답변 생성 |

### database.py

| 함수 | 역할 |
|------|------|
| `get_sheet_list()` | 14개 Sheet 목록 반환 |
| `get_articles_by_sheet(sheet_name)` | Sheet별 조항 목록 (GROUP BY) |
| `get_paragraphs_by_article(sheet, article)` | 조항별 항 목록 |
| `search_laws(keyword, limit)` | LIKE 패턴 검색 (중복 제거) |

### static/js/app.js

| 클래스/함수 | 역할 |
|-------------|------|
| `ComplaintChatbot` | 메인 클래스 (싱글톤) |
| `sendMessage()` | POST /api/chat 호출 |
| `showGenerateAnswerBtn()` | 답변생성 버튼 동적 생성 |
| `togglePanels()` | 오른쪽 패널 토글 |
| `loadMasterTree()` | GET /api/laws/master-tree 호출 |
| `applySelectedClauses()` | 선택 법령 관련법령 패널에 추가 |

---

## API Endpoints

| Method | Endpoint | 역할 |
|--------|----------|------|
| GET | `/` | 메인 페이지 렌더링 |
| POST | `/api/chat` | 하이브리드 RAG 답변 생성 |
| POST | `/api/chat/confirm` | 질문 확인 (2단계 플로우용) |
| POST | `/api/new-session` | 새 세션 ID 생성 |
| GET | `/api/laws/master-tree` | 법령 3단 트리 데이터 |
| GET | `/api/laws/sheets` | Sheet 목록 |
| GET | `/api/laws/articles?sheet_name=` | 조항 목록 |
| GET | `/api/laws/paragraphs?sheet_name=&article_num=` | 항 목록 |

---

## 환경 변수 (.env)

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Dify
DIFY_API_URL=http://112.173.179.199:5001/v1
DIFY_API_KEY=dataset-...
DIFY_DATASET_ID=...

# Mode
AI_MODE=dify                    # 'dify' or 'openai'
FALLBACK_TO_OPENAI=True        # Dify 실패 시 OpenAI 폴백

# Flask
FLASK_SECRET_KEY=...
```

---

## Dify RAG 설정

### Retrieve API 호출

```python
payload = {
    "query": user_message,
    "retrieval_model": {
        "search_method": "semantic_search",
        "reranking_enable": False,      # 비용 절감 (OpenAI 불필요)
        "top_k": 3,
        "score_threshold_enabled": True,
        "score_threshold": 0.5
    }
}
```

### FAQ 데이터 포맷 (Dify 업로드용)

```csv
faq_id,question,answer_text,policy_anchor,tag
FAQ-사업비-0005,사업비 교부는 어떻게 받나요?,협약 체결 후...,기금운영지침 제10조,사업비,교부
```

---

## 프론트엔드 아키텍처

### 레이아웃 구조

```
┌─────────────────────────────────────────────────────────────┐
│                        <body>                                │
├──────────┬──────────────────────────┬───────────────────────┤
│ .sidebar │      .chat-pane          │    .right-panels      │
│ (fixed)  │      (flex: 1)           │    (fixed, toggled)   │
├──────────┼──────────────────────────┼───────────────────────┤
│ 새채팅   │ .messages                │ .right-reco           │
│ 히스토리  │ .composer               │ .right-laws           │
│          │   .complaint-examples    │                       │
│          │   .input-container       │                       │
└──────────┴──────────────────────────┴───────────────────────┘
```

### 상태 관리

```javascript
class ComplaintChatbot {
    // Core State
    sessionId = null;              // Backend session
    messages = [];                 // Chat history
    lastBotResponse = null;        // { suggested_answer, related_laws, metadata }

    // UI State
    isEditMode = false;
    currentLawEditStep = 1;        // 1: 지침, 2: 조항, 3: 항
    selectedClauses = [];          // 선택된 법령 항목

    // Data Cache
    masterTreeData = null;         // /api/laws/master-tree 응답
}
```

---

## 개선 포인트

### 완료

- [x] Hybrid RAG 아키텍처 구현
- [x] SQLite 법령 검색 + Dify FAQ 검색 통합
- [x] 법령 중복 제거 (sheet_name + article_num 기준)
- [x] 마스터 트리 캐싱 (서버 시작 시 1회 로드)
- [x] GPT 컨텍스트 확장 (법령 전체 텍스트 포함)

### 추후 개선 가능

- [ ] 관련도 점수 기반 검색 (조항 제목: 10점, 태그: 5점, 항 내용: 3점)
- [ ] 채팅 세션 DB 영구 저장 (현재 메모리)
- [ ] 사용자 인증/권한 관리
- [ ] 법령 데이터 자동 동기화 (Excel → DB)
- [ ] 응답 캐싱 (동일 질문 재사용)

---

## 실행 명령

```bash
# 의존성 설치
uv sync

# 법령 DB 생성 (최초 1회)
uv run python convert_law_to_db_sheets.py

# 서버 실행
uv run app.py

# 접속
open http://localhost:5000
```

---

## 로깅

### 로그 레벨

| Logger | 파일 | 내용 |
|--------|------|------|
| `app.logger` | logs/app.log | 일반 요청/응답 |
| `api_logger` | logs/api_calls.log | Dify/OpenAI API 호출 |
| `werkzeug` | logs/app.log | HTTP 요청 |

### 디버깅 팁

```bash
# 실시간 로그 확인
tail -f logs/app.log

# API 호출 로그
tail -f logs/api_calls.log
```

---

**작성일**: 2025-12-16
**버전**: 2.1
**작성자**: Claude Code
