# 민원처리 챗봇 시스템 분석 문서

---

## [1단계] 시스템 개요 - 한눈에 보기

### 🎯 이 시스템이 뭔가요?

**공무원들이 민원을 처리할 때 도움을 주는 AI 챗봇 시스템**입니다.
민원 내용을 입력하면 ChatGPT처럼 답변을 제공하고, 관련 법률과 공식 답변 양식까지 자동으로 생성해줍니다.

---

### 🏗️ 전체 구조 한눈에 보기 (최신 - 하이브리드 방식)

```
┌─────────────────────┐
│   사용자 (공무원)    │
│   웹 브라우저에서    │
│   챗봇 사용         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│     프론트엔드 (화면)            │
│  - 채팅 인터페이스              │
│  - 채팅 기록 사이드바           │
│  - React로 만든 웹페이지        │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│     백엔드 (처리 서버)                       │
│  - 메시지 처리                              │
│  - FAQ 하이브리드 매칭 (Dify + 로컬)        │
│  - AI 연결                                  │
│  - Python Flask 서버                        │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│     외부 서비스 & 데이터                     │
│  - Dify Knowledge (FAQ + 법령 DB)          │
│  - OpenAI (GPT-4o-mini)                    │
│  - 로컬 faq_topic.xlsx (매핑 테이블)        │
│  - Supabase (데이터 저장소)                 │
└─────────────────────────────────────────────┘
```

---

### 🔧 사용된 기술

#### 프론트엔드 (화면)
- **React 18.2.0** - 사용자 인터페이스 프레임워크
- **TypeScript 4.9.0** - 타입 안전성을 제공하는 JavaScript
- **Supabase JS 2.56.0** - 데이터베이스 클라이언트
- **react-scripts 5.0.1** - 빌드 도구

#### 백엔드 (서버)
- **Python 3.13** - 프로그래밍 언어
- **Flask 3.1.2** - 웹 서버 프레임워크
- **OpenAI API** - GPT-4o-mini 모델 사용
- **Dify Knowledge** - RAG 기반 문서 검색
- **pandas** - FAQ 매핑 테이블 처리
- **uv** - 패키지 관리 도구

#### 데이터 저장
- **Dify Knowledge** - FAQ 102개 + 법령 문서 (Vector DB)
- **로컬 faq_topic.xlsx** - FAQ policy_anchor 매핑 테이블
- **Supabase (PostgreSQL)** - 채팅 기록 저장
- **로컬 파일 시스템** - 로그 및 참고 문서

---

### 📁 주요 폴더 설명

```
test_dify/
│
├── src/                          # 프론트엔드 소스 코드
│   ├── components/               # 화면 구성 요소
│   │   ├── Chatbot.tsx          # 채팅 화면
│   │   └── ChatSidebar.tsx      # 채팅 기록 목록
│   ├── services/                # 데이터 처리 로직
│   │   ├── chatService.ts       # 데이터베이스 연동
│   │   └── chatbotService.ts    # AI 응답 처리
│   └── lib/                     # 유틸리티
│       └── supabase.ts          # 데이터베이스 설정
│
├── fund/                         # 백엔드 소스 코드
│   ├── app.py                   # Flask 서버 메인 파일 (하이브리드 RAG)
│   ├── design/                  # 대체 UI (HTML/CSS/JS)
│   ├── logs/                    # 서버 로그 파일
│   └── .env                     # 환경 변수 (API 키, Dify 설정)
│
├── data/                         # 참고 자료
│   ├── faq_topic.xlsx           # FAQ 매핑 테이블 (102개)
│   ├── faq_markdown/            # FAQ Markdown 파일 (Dify 업로드용)
│   └── (법률, 규정 문서들)
│
├── scripts/                      # 유틸리티 스크립트
│   └── convert_faq_for_dify.py  # FAQ Excel → Markdown 변환
│
├── public/                       # 정적 파일
│   └── index.html               # HTML 진입점
│
├── plan.md                       # 이 문서
└── DIFY_RAG_SETUP.md            # Dify 설정 가이드
```

#### 각 폴더가 하는 일

| 폴더 | 역할 |
|------|------|
| **src/components/** | 사용자가 보는 화면 (채팅창, 사이드바 등) |
| **src/services/** | 서버와 통신, 데이터 처리 |
| **fund/app.py** | FAQ 하이브리드 매칭 + Dify RAG + 답변 생성 |
| **fund/design/** | ChatGPT 스타일의 대체 UI |
| **fund/logs/** | 서버 동작 기록, 에러 추적 |
| **data/faq_topic.xlsx** | FAQ policy_anchor 매핑 테이블 |
| **data/faq_markdown/** | Dify에 업로드할 FAQ Markdown 파일 |
| **scripts/** | FAQ 변환 등 유틸리티 스크립트 |

---
---

## [2단계] 개발자용 구조 설명

### 시스템 아키텍처 상세 (하이브리드 RAG 방식)

#### Multi-tier Architecture with Hybrid RAG

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│                  (프레젠테이션 계층)                      │
├─────────────────────────────────────────────────────────┤
│  • React Components (Chatbot, ChatSidebar)              │
│  • TypeScript Type Definitions                          │
│  • CSS Styling                                          │
│  • User Input/Output Handling                           │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP REST API (JSON)
                   │
┌──────────────────▼──────────────────────────────────────┐
│                   Backend Layer                          │
│                 (하이브리드 RAG 로직)                     │
├─────────────────────────────────────────────────────────┤
│  Flask Application (app.py)                             │
│  • Routes: /, /api/chat, /api/new-session              │
│  • FAQ Hybrid Matching Logic                            │
│    ├─ Dify Knowledge: FAQ Semantic Search              │
│    ├─ Local Mapping: faq_id → policy_anchor            │
│    └─ Dify Knowledge: Policy Document Search           │
│  • Session Management (in-memory)                       │
│  • Logging System                                       │
└──────────────────┬──────────────────────────────────────┘
                   │ API Calls
                   │
┌──────────────────▼──────────────────────────────────────┐
│               External Services Layer                    │
│               (외부 서비스 계층)                          │
├─────────────────────────────────────────────────────────┤
│  • Dify Knowledge API                                   │
│    ├─ FAQ Vector DB (102개)                            │
│    └─ Policy Document Vector DB (법령/규정)             │
│  • OpenAI API (GPT-4o-mini)                             │
│  • Local Data                                           │
│    └─ faq_topic.xlsx (policy_anchor 매핑)               │
│  • Supabase PostgreSQL Database                         │
└─────────────────────────────────────────────────────────┘
```

---

### 핵심: 하이브리드 RAG 방식

#### 왜 하이브리드인가?

```
Dify만 사용할 경우:
  ✅ FAQ 검색 정확도 높음 (80-90%)
  ❌ policy_anchor를 정확히 추출하기 어려움 (LLM 환각 가능성)

로컬만 사용할 경우:
  ❌ FAQ 매칭 정확도 낮음 (60-70%, 키워드 매칭)
  ✅ policy_anchor 정확도 100%

하이브리드 방식:
  ✅ Dify로 FAQ 검색 (정확도 높음)
  ✅ 로컬 매핑으로 policy_anchor 보장 (정확도 100%)
  ✅ Dify로 법령 문서 검색
  → 최고의 정확도!
```

---

### 주요 컴포넌트 및 역할

#### 1. 프론트엔드 컴포넴트 (변경 없음)

##### Chatbot.tsx (`src/components/Chatbot.tsx`)
**역할**: 메인 채팅 인터페이스
- 메시지 목록 렌더링
- 사용자 입력 처리
- AI 응답 로딩 상태 표시
- 자동 스크롤 기능
- 빠른 액션 버튼 제공

##### ChatSidebar.tsx (`src/components/ChatSidebar.tsx`)
**역할**: 채팅 세션 관리 사이드바
- 세션 목록 표시
- 새 세션 생성
- 세션 선택/삭제

#### 2. 백엔드 레이어 (하이브리드 RAG 추가)

##### Flask Application (`fund/app.py`)

**주요 엔드포인트**:

| 엔드포인트 | 메서드 | 기능 | 요청 | 응답 |
|-----------|--------|------|------|------|
| `/` | GET | HTML 페이지 제공 | - | index.html |
| `/api/chat` | POST | 하이브리드 RAG 처리 | `{message, session_id}` | `{success, message, related_laws, matched_faq_id}` |
| `/api/new-session` | POST | 새 세션 생성 | - | `{session_id}` |

**핵심 함수**:

1. **call_dify_knowledge(query, top_k)**
   - Dify Knowledge API 호출
   - FAQ 또는 법령 문서 검색
   - Semantic search 사용

2. **extract_faq_id_from_content(record)**
   - Dify 검색 결과에서 faq_id 추출
   - Metadata 또는 정규식 사용

3. **get_policy_anchor(faq_id)**
   - 로컬 faq_topic.xlsx에서 매핑
   - faq_id → policy_anchor
   - **정확도 100% 보장**

4. **generate_answer_with_context(user_message, faq_content, policy_docs)**
   - FAQ 답변 + 법령 문서를 컨텍스트로 사용
   - OpenAI GPT-4o-mini로 최종 답변 생성

---

### 외부 연동 시스템

#### 1. Dify Knowledge API 연동

**엔드포인트**:
```
http://112.173.179.199:5001/v1/datasets/{dataset_id}/retrieve
```

**두 가지 Dataset**:

| Dataset | 내용 | 용도 |
|---------|------|------|
| **FAQ Dataset** | faq_topic.xlsx 102개 FAQ | FAQ 검색 (semantic search) |
| **Policy Dataset** | 기금사업 협약체결 지침, 사업비 산정 지침 등 | 법령 문서 검색 |

**검색 설정**:
```json
{
  "retrieval_model": {
    "search_method": "semantic_search",
    "reranking_enable": true,
    "top_k": 3,
    "score_threshold_enabled": true,
    "score_threshold": 0.5
  }
}
```

#### 2. OpenAI API 연동

**모델**: gpt-4o-mini
**온도**: 0.7
**최대 토큰**: 1000

**사용 목적**:
- FAQ + 법령 문서 기반 답변 생성
- 제안 답변서 생성 (공식 양식)

#### 3. 로컬 데이터 (faq_topic.xlsx)

**역할**: policy_anchor 매핑 테이블

**구조**:
```
faq_id | question | answer_text | policy_anchor | tag
-------|----------|-------------|---------------|----
FAQ-협약체결-0002 | 사업비 교부... | ... | 지침 제13조; 별지 제2호 | 협약체결,사업비 교부
```

**사용 방법**:
```python
# 서버 시작 시 로드
faq_df = pd.read_excel('data/faq_topic.xlsx')
faq_policy_map = dict(zip(faq_df['faq_id'], faq_df['policy_anchor']))

# 매핑
policy_anchor = faq_policy_map.get(faq_id)  # "지침 제13조; 별지 제2호"
```

---

### 환경 설정

#### 환경 변수 설정 (`fund/.env`)

```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Dify Knowledge Configuration
DIFY_API_URL=http://112.173.179.199:5001/v1
DIFY_API_KEY=dataset-Q0C0AIJh8le8WMK8SpU1Bkh2
DIFY_DATASET_ID=68f0788b-4623-4ecc-bd4f-20199b4517a4

# AI Response Mode
AI_MODE=dify
FALLBACK_TO_OPENAI=True

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=False

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

### 실행 방법

#### 백엔드 실행
```bash
cd fund
python app.py
```

#### 프론트엔드 실행
```bash
npm start
# → http://localhost:3000
```

---

### 개발 상태

#### ✅ 완료된 기능
- React 기반 ChatGPT 스타일 UI
- Flask 백엔드 서버 구축
- Dify Knowledge RAG 연동
- 하이브리드 FAQ 매칭 시스템 설계
- FAQ Markdown 변환 스크립트
- 로깅 시스템
- Supabase 스키마 정의

#### 🚧 진행 예정
- [ ] FAQ를 Dify에 업로드
- [ ] 하이브리드 매칭 로직 구현
- [ ] policy_anchor 매핑 시스템 구현
- [ ] 법령 문서 Dify 업로드
- [ ] 통합 테스트

---
---

## [3단계] 신입개발자용 데이터 흐름

### 하이브리드 RAG 방식 전체 플로우

```
사용자: "사업비 교부는 어떻게 받나요?"
        ↓
┌──────────────────────────────────────────────────────┐
│ STEP 1: Flask /api/chat 엔드포인트                   │
│ - 사용자 메시지 수신                                 │
│ - session_id 확인/생성                               │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 2: Dify Knowledge - FAQ 검색                    │
│                                                      │
│ call_dify_knowledge("사업비 교부는 어떻게 받나요?")   │
│                                                      │
│ Dify Response:                                       │
│ {                                                    │
│   "records": [                                       │
│     {                                                │
│       "segment": {                                   │
│         "content": "---\nfaq_id: FAQ-협약체결-0002   │
│                     \n# 사업비 교부 신청 및 절차는?  │
│                     \n## 답변\n사업비는..."          │
│       },                                             │
│       "score": 0.89                                  │
│     }                                                │
│   ]                                                  │
│ }                                                    │
│                                                      │
│ ✅ FAQ 내용 확보: "사업비는 자금배정신청서를..."      │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 3: faq_id 추출                                  │
│                                                      │
│ extract_faq_id_from_content(record)                  │
│                                                      │
│ 추출 방법:                                           │
│ 1. Metadata에서 파싱 (YAML frontmatter)              │
│ 2. 정규식으로 "faq_id: ..." 찾기                     │
│ 3. 문서명에서 추출                                   │
│                                                      │
│ 결과: faq_id = "FAQ-협약체결-0002"                   │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 4: 로컬 매핑 (policy_anchor 가져오기)           │
│                                                      │
│ faq_policy_map = {                                   │
│   "FAQ-협약체결-0002": "기금사업 협약체결 및 사업비  │
│                         관리 등에 관한 지침 제13조;  │
│                         별지 제2호 서식"             │
│ }                                                    │
│                                                      │
│ policy_anchor = faq_policy_map["FAQ-협약체결-0002"]  │
│                                                      │
│ ✅ 결과: "기금사업 협약체결 및 사업비 관리 등에       │
│          관한 지침 제13조; 별지 제2호 서식"          │
│                                                      │
│ ⚠️ 중요: 이 값을 그대로 related_laws로 사용!         │
│          (LLM 생성 X, 데이터에서 직접 가져옴)        │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 5: Dify Knowledge - 법령 문서 검색              │
│                                                      │
│ policy_anchors = [                                   │
│   "기금사업 협약체결 및 사업비 관리 등에 관한 지침    │
│    제13조",                                          │
│   "별지 제2호 서식"                                   │
│ ]                                                    │
│                                                      │
│ for anchor in policy_anchors:                        │
│   dify_result = call_dify_knowledge(anchor, top_k=2) │
│                                                      │
│ Dify Response:                                       │
│ {                                                    │
│   "records": [                                       │
│     {                                                │
│       "segment": {                                   │
│         "content": "제13조 (사업비의 교부)            │
│                     ① 주관기관은 협약체결 후..."     │
│       }                                              │
│     }                                                │
│   ]                                                  │
│ }                                                    │
│                                                      │
│ ✅ 법령 문서 내용 확보                                │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 6: LLM 답변 생성                                │
│                                                      │
│ 컨텍스트 구성:                                       │
│                                                      │
│ context = """                                        │
│ 참고 FAQ:                                            │
│ Q: 사업비 교부 신청 및 절차는?                        │
│ A: 사업비는 자금배정신청서를 제출하여...              │
│                                                      │
│ 참고 법령:                                           │
│ 제13조 (사업비의 교부)                                │
│ ① 주관기관은 협약체결 후 자금배정신청서를...          │
│ """                                                  │
│                                                      │
│ OpenAI API 호출:                                     │
│ response = client.chat.completions.create(           │
│   model="gpt-4o-mini",                               │
│   messages=[                                         │
│     {"role": "system", "content": context},          │
│     {"role": "user", "content": "사업비 교부는..."}  │
│   ]                                                  │
│ )                                                    │
│                                                      │
│ ✅ 생성된 답변:                                       │
│ "사업비 교부는 다음과 같이 진행됩니다.                │
│  먼저 협약 체결 후 자금배정신청서를 제출하고..."      │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 7: 제안 답변 생성 (선택)                         │
│                                                      │
│ generate_suggested_answer(user_message, answer)      │
│                                                      │
│ → 공식 민원 답변서 양식 생성                          │
│   "민원인님께, 귀하의 문의에..."                      │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 8: 응답 구성 및 전송                             │
│                                                      │
│ response = {                                         │
│   "success": true,                                   │
│   "message": "사업비 교부는 다음과 같이...",          │
│   "suggested_answer": "민원인님께...",               │
│   "related_laws": [                                  │
│     {                                                │
│       "title": "기금사업 협약체결 및 사업비 관리 등에  │
│                관한 지침 제13조",                     │
│       "source": "FAQ Database",                      │
│       "faq_id": "FAQ-협약체결-0002"                  │
│     },                                               │
│     {                                                │
│       "title": "별지 제2호 서식",                     │
│       "source": "FAQ Database",                      │
│       "faq_id": "FAQ-협약체결-0002"                  │
│     }                                                │
│   ],                                                 │
│   ↑ 로컬 매핑에서 가져온 값 그대로!                   │
│   (LLM이 생성하지 않음)                               │
│                                                      │
│   "session_id": "abc-123",                           │
│   "metadata": {                                      │
│     "matched_faq_id": "FAQ-협약체결-0002",           │
│     "ai_mode": "dify"                                │
│   }                                                  │
│ }                                                    │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│ STEP 9: 프론트엔드 표시                               │
│                                                      │
│ - 답변: "사업비 교부는 다음과 같이..."               │
│ - 관련 법령:                                         │
│   • 기금사업 협약체결 및 사업비 관리 등에 관한 지침   │
│     제13조                                           │
│   • 별지 제2호 서식                                   │
│                                                      │
│ 사용자가 확인                                         │
└──────────────────────────────────────────────────────┘
```

---

### 핵심 포인트 정리

#### 1. **Dify의 역할**
```
✅ FAQ 검색 (Semantic Search)
   - 사용자 질문 → 관련 FAQ 찾기
   - 검색 정확도: 80-90%

✅ FAQ 답변 내용 제공
   - LLM에게 컨텍스트로 전달

✅ 법령 문서 검색
   - policy_anchor 키워드 → 법령 문서 찾기

✅ 법령 내용 제공
   - LLM에게 컨텍스트로 전달
```

#### 2. **로컬 faq_topic.xlsx의 역할**
```
✅ policy_anchor 매핑 (정확도 100%)
   - faq_id → policy_anchor
   - "FAQ-협약체결-0002" → "지침 제13조; 별지 제2호"

✅ 이 값을 그대로 related_laws로 사용
   - LLM이 생성하지 않음
   - 데이터 무결성 보장
```

#### 3. **LLM(OpenAI)의 역할**
```
✅ 답변 생성
   - Dify에서 받은 FAQ 답변 참고
   - Dify에서 받은 법령 내용 참고
   - 최종 답변 생성

✅ 제안 답변서 생성
   - 공식 양식 작성

❌ 관련법령은 생성하지 않음
   - 로컬 매핑값 그대로 사용
```

---

### 에러 처리

#### 1. FAQ 매칭 실패 시
```python
if not dify_result['success'] or not dify_result['records']:
    app.logger.warning("No FAQ matched")

    if FALLBACK_TO_OPENAI:
        # OpenAI 직접 호출 (Dify 없이)
        answer = generate_openai_response(user_message)
    else:
        return jsonify({'error': 'FAQ 매칭 실패'})
```

#### 2. faq_id 추출 실패 시
```python
faq_id = extract_faq_id_from_content(record)

if not faq_id:
    app.logger.warning("faq_id extraction failed")
    # FAQ 내용만으로 답변 생성 (policy_anchor 없이)
```

#### 3. policy_anchor 매핑 실패 시
```python
policy_anchor = faq_policy_map.get(faq_id)

if not policy_anchor:
    app.logger.error(f"No policy_anchor for {faq_id}")
    # FAQ 답변만으로 생성
    # related_laws는 빈 배열
```

---

### 로깅

#### app.log
```
[2025-10-21 15:30:00] [INFO] Chat request: 사업비 교부는?
[2025-10-21 15:30:01] [INFO] Dify FAQ search completed - Retrieved 3 FAQs
[2025-10-21 15:30:01] [INFO] Extracted faq_id: FAQ-협약체결-0002
[2025-10-21 15:30:01] [INFO] Mapped policy_anchor: 지침 제13조; 별지 제2호
[2025-10-21 15:30:02] [INFO] Dify policy search completed - Retrieved 4 docs
[2025-10-21 15:30:04] [INFO] Answer generated successfully
```

#### api_calls.log
```
[2025-10-21 15:30:01] Dify FAQ search: Query="사업비 교부는?" Results=3 Time=0.8s
[2025-10-21 15:30:02] Dify Policy search: Query="지침 제13조" Results=2 Time=0.6s
[2025-10-21 15:30:04] OpenAI answer generation: Tokens=456 Time=1.8s
```

---

### 주요 데이터 타입

#### TypeScript 인터페이스 (프론트엔드)

```typescript
// src/types/index.ts

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

export interface RelatedLaw {
  title: string;          // "기금사업 협약체결... 제13조"
  source: string;         // "FAQ Database"
  faq_id?: string;        // "FAQ-협약체결-0002"
  content?: string;       // 선택적 내용
}

export interface ChatResponse {
  success: boolean;
  message: string;                    // LLM 생성 답변
  suggested_answer?: string;          // 제안 답변서
  related_laws: RelatedLaw[];         // 로컬 매핑값 그대로
  session_id: string;
  metadata?: {
    matched_faq_id?: string;
    ai_mode: 'dify' | 'openai';
  };
}
```

---
---

## [다음 진행 단계] 구현 로드맵

### 📋 Phase 1: FAQ Dify 업로드 준비 (30분)

#### Step 1-1: FAQ Markdown 변환
```bash
cd C:\cursor_work\test_dify
python scripts/convert_faq_for_dify.py
# 선택: 1 (개별 Markdown 파일 - 추천)
```

**결과 확인**:
- `data/faq_markdown/` 폴더에 102개 `.md` 파일 생성
- 각 파일에 metadata 포함 확인

**예시 파일 (`FAQ-협약체결-0002.md`)**:
```markdown
---
faq_id: FAQ-협약체결-0002
tags: 협약체결,사업비 교부,자금배정신청서,자금배정
policy_anchor: 기금사업 협약체결 및 사업비 관리 등에 관한 지침 제13조; 별지 제2호 서식
---

# 사업비 교부 신청 및 절차는?

## 답변

사업비는 자금배정신청서를 제출하여 교부받습니다...

## 관련 법령

기금사업 협약체결 및 사업비 관리 등에 관한 지침 제13조; 별지 제2호 서식

## 태그

협약체결,사업비 교부,자금배정신청서,자금배정
```

#### Step 1-2: Dify에 FAQ 업로드

1. Dify 웹 인터페이스 접속
   ```
   http://112.173.179.199:5001
   ```

2. **Knowledge** 섹션으로 이동

3. **기존 Dataset 선택** 또는 **새 Dataset 생성**
   - 이름: "ICT 기금사업 FAQ"

4. **Add Document** 클릭

5. **폴더 전체 업로드**
   - `data/faq_markdown/` 폴더 선택
   - 102개 파일 모두 선택

6. **Chunking 설정**:
   ```
   Chunk Strategy: Custom
   Chunk Size: 1000 (FAQ 하나가 하나의 chunk)
   Overlap: 0 (FAQ는 독립적)
   Separator: \n---\n (각 FAQ 구분)
   ```

7. **Embedding 설정**:
   ```
   Embedding Model: text-embedding-3-small (또는 기본값)
   ```

8. **Save and Process** 클릭

9. **처리 완료 대기** (약 2-3분)

10. **새 Dataset ID 복사**
    ```
    예: faq-12345678-1234-1234-1234-123456789abc
    ```

#### Step 1-3: .env 파일 업데이트
```bash
# fund/.env

# 기존 Dataset ID를 FAQ Dataset ID로 교체
DIFY_DATASET_ID_FAQ=faq-12345678-1234-1234-1234-123456789abc

# Policy 문서용 Dataset ID (기존 유지 또는 별도 생성)
DIFY_DATASET_ID_POLICY=68f0788b-4623-4ecc-bd4f-20199b4517a4
```

---

### 📋 Phase 2: 백엔드 하이브리드 로직 구현 (2-3시간)

#### Step 2-1: faq_id 추출 함수 추가

**파일**: `fund/app.py`

```python
import re
import yaml

def extract_faq_id_from_content(record):
    """
    Dify 검색 결과에서 faq_id 추출

    Args:
        record: Dify API 응답의 records[0]

    Returns:
        str: faq_id (예: "FAQ-협약체결-0002") or None
    """
    try:
        content = record.get('segment', {}).get('content', '')

        # 방법 1: YAML frontmatter 파싱
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                try:
                    metadata = yaml.safe_load(parts[1])
                    faq_id = metadata.get('faq_id')
                    if faq_id:
                        app.logger.debug(f"Extracted faq_id from metadata: {faq_id}")
                        return faq_id
                except yaml.YAMLError as e:
                    app.logger.warning(f"YAML parsing failed: {e}")

        # 방법 2: 정규식으로 추출
        match = re.search(r'faq_id:\s*(.+)', content)
        if match:
            faq_id = match.group(1).strip()
            app.logger.debug(f"Extracted faq_id from regex: {faq_id}")
            return faq_id

        # 방법 3: 문서명에서 추출
        doc_name = record.get('segment', {}).get('document', {}).get('name', '')
        if doc_name.endswith('.md'):
            faq_id = doc_name[:-3]
            app.logger.debug(f"Extracted faq_id from filename: {faq_id}")
            return faq_id

        app.logger.warning("faq_id extraction failed")
        return None

    except Exception as e:
        app.logger.error(f"Error extracting faq_id: {e}")
        return None
```

#### Step 2-2: 로컬 매핑 테이블 로드

**파일**: `fund/app.py`

```python
import pandas as pd

# 서버 시작 시 FAQ 매핑 테이블 로드
try:
    faq_df = pd.read_excel('data/faq_topic.xlsx')
    faq_policy_map = dict(zip(faq_df['faq_id'], faq_df['policy_anchor']))
    app.logger.info(f"Loaded {len(faq_policy_map)} FAQ policy mappings")
except Exception as e:
    app.logger.error(f"Failed to load FAQ mapping: {e}")
    faq_policy_map = {}
```

#### Step 2-3: /api/chat 엔드포인트 수정

**파일**: `fund/app.py`

```python
@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with hybrid FAQ RAG"""
    session_id = None
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))

        app.logger.info(f'Chat request from session {session_id}: {user_message[:100]}...')

        # Initialize session
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

        # ===== STEP 1: Dify FAQ 검색 =====
        app.logger.info('Step 1: Searching FAQ in Dify')
        faq_result = call_dify_knowledge(user_message, top_k=3)

        if not faq_result['success'] or not faq_result['records']:
            app.logger.warning('FAQ search failed, using fallback')
            # Fallback to OpenAI
            assistant_message = generate_openai_response(session_id, user_message)
            related_laws = []
            matched_faq_id = None
        else:
            # ===== STEP 2: faq_id 추출 =====
            app.logger.info('Step 2: Extracting faq_id')
            best_faq_record = faq_result['records'][0]
            faq_id = extract_faq_id_from_content(best_faq_record)

            if not faq_id:
                app.logger.warning('faq_id extraction failed')
                # FAQ 내용만으로 답변
                assistant_message = generate_answer_with_dify_rag(
                    user_message,
                    faq_result['records'],
                    None
                )
                related_laws = []
                matched_faq_id = None
            else:
                # ===== STEP 3: 로컬 매핑 (policy_anchor) =====
                app.logger.info(f'Step 3: Mapping policy_anchor for {faq_id}')
                policy_anchor = faq_policy_map.get(faq_id, '')

                if not policy_anchor:
                    app.logger.error(f'No policy_anchor for {faq_id}')
                    # FAQ만으로 답변
                    assistant_message = generate_answer_with_dify_rag(
                        user_message,
                        faq_result['records'],
                        None
                    )
                    related_laws = []
                    matched_faq_id = faq_id
                else:
                    app.logger.info(f'Mapped policy_anchor: {policy_anchor}')

                    # ===== STEP 4: policy_anchor로 법령 문서 검색 =====
                    app.logger.info('Step 4: Searching policy documents')
                    policy_docs = []
                    policy_anchors = [p.strip() for p in policy_anchor.split(';')]

                    for anchor in policy_anchors[:2]:  # 최대 2개만
                        policy_result = call_dify_knowledge(anchor, top_k=2)
                        if policy_result['success']:
                            policy_docs.extend(policy_result['records'])

                    # ===== STEP 5: LLM 답변 생성 =====
                    app.logger.info('Step 5: Generating answer with context')
                    assistant_message = generate_answer_with_context(
                        user_message,
                        faq_result['records'],
                        policy_docs
                    )

                    # ===== STEP 6: policy_anchor를 그대로 related_laws로 =====
                    related_laws = []
                    for anchor in policy_anchors:
                        related_laws.append({
                            'title': anchor,
                            'source': 'FAQ Database',
                            'faq_id': faq_id
                        })

                    matched_faq_id = faq_id

        # Add assistant message to session
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': assistant_message
        })

        # Generate suggested answer
        suggested_answer = generate_suggested_answer(user_message, assistant_message)

        # Response
        return jsonify({
            'success': True,
            'message': assistant_message,
            'suggested_answer': suggested_answer,
            'related_laws': related_laws,
            'session_id': session_id,
            'metadata': {
                'matched_faq_id': matched_faq_id,
                'ai_mode': AI_MODE
            }
        })

    except Exception as e:
        error_session = session_id if session_id else 'unknown'
        app.logger.error(f'Error in chat endpoint: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### Step 2-4: 컨텍스트 기반 답변 생성 함수

**파일**: `fund/app.py`

```python
def generate_answer_with_context(user_message, faq_records, policy_docs):
    """
    FAQ + Policy 문서 컨텍스트로 답변 생성

    Args:
        user_message: 사용자 질문
        faq_records: Dify에서 검색한 FAQ 레코드
        policy_docs: Dify에서 검색한 법령 문서 레코드

    Returns:
        str: 생성된 답변
    """
    try:
        # FAQ 컨텍스트 구성
        faq_context = ""
        for idx, record in enumerate(faq_records[:2]):  # 상위 2개만
            content = record.get('segment', {}).get('content', '')
            faq_context += f"\n[참고 FAQ {idx+1}]\n{content}\n"

        # Policy 문서 컨텍스트 구성
        policy_context = ""
        if policy_docs:
            for idx, doc in enumerate(policy_docs[:3]):  # 상위 3개만
                content = doc.get('segment', {}).get('content', '')
                policy_context += f"\n[참고 법령 {idx+1}]\n{content}\n"

        # 시스템 프롬프트
        system_prompt = f"""당신은 대한민국 기금 민원처리 전문가입니다.

다음 자료를 참고하여 질문에 답변하세요:

{faq_context}

{policy_context}

답변 시 지침:
1. 위 참고 자료의 내용을 정확히 활용하세요
2. 법령이나 규정을 인용할 때는 정확한 조항을 명시하세요
3. 필요한 서류나 절차를 구체적으로 안내하세요
4. 참고 자료에 없는 내용은 추측하지 말고, 추가 확인이 필요하다고 안내하세요
5. 정중하고 공손한 어투를 사용하세요"""

        # OpenAI 호출
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

        return assistant_message

    except Exception as e:
        app.logger.error(f'Error generating answer: {str(e)}')
        raise
```

#### Step 2-5: requirements 추가

**파일**: `fund/pyproject.toml`

```toml
[project]
dependencies = [
    "flask>=3.1.2",
    "openai>=1.106.1",
    "python-dotenv>=1.1.1",
    "requests>=2.32.5",
    "pandas>=2.0.0",      # 추가
    "openpyxl>=3.1.0",    # 추가 (Excel 읽기)
    "pyyaml>=6.0"         # 추가 (YAML 파싱)
]
```

**설치**:
```bash
cd fund
uv sync
```

---

### 📋 Phase 3: 테스트 (30분)

#### Step 3-1: 서버 시작
```bash
cd fund
python app.py
```

**로그 확인**:
```
[INFO] Loaded 102 FAQ policy mappings
[INFO] AI Mode: dify
[INFO] Starting Civil Complaint Chatbot Application
```

#### Step 3-2: API 테스트

**테스트 1: FAQ 매칭 확인**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "사업비 교부 절차가 궁금합니다"}'
```

**예상 응답**:
```json
{
  "success": true,
  "message": "사업비 교부는 다음과 같이 진행됩니다...",
  "related_laws": [
    {
      "title": "기금사업 협약체결 및 사업비 관리 등에 관한 지침 제13조",
      "source": "FAQ Database",
      "faq_id": "FAQ-협약체결-0002"
    }
  ],
  "metadata": {
    "matched_faq_id": "FAQ-협약체결-0002"
  }
}
```

**테스트 2: 다양한 질문**
```bash
# 인건비 관련
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "인건비 보수와 상용임금 차이는?"}'

# 협약 관련
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "사업수행계획서에 뭐 포함해야 하나요?"}'
```

#### Step 3-3: 로그 확인
```bash
# 애플리케이션 로그
tail -f fund/logs/app.log

# API 호출 로그
tail -f fund/logs/api_calls.log
```

---

### 📋 Phase 4: 프론트엔드 통합 테스트 (10분)

#### Step 4-1: 프론트엔드 시작
```bash
npm start
```

#### Step 4-2: 브라우저 테스트

1. `http://localhost:3000` 접속

2. 채팅창에 질문 입력:
   - "사업비 교부는 어떻게 받나요?"
   - "인건비 계산 방법이 궁금합니다"
   - "협약 체결 절차를 알려주세요"

3. **확인 사항**:
   - ✅ 답변이 FAQ 기반으로 생성되는지
   - ✅ 관련 법령이 정확히 표시되는지
   - ✅ 로딩 상태가 정상인지
   - ✅ 에러 없이 동작하는지

---

### 📋 Phase 5: 최적화 및 마무리 (선택)

#### Step 5-1: Chunking 최적화

Dify에서 FAQ 검색 정확도 테스트 후 조정:
```
Chunk Size: 800-1200 사이에서 조정
Overlap: 0-50 사이에서 조정
```

#### Step 5-2: 캐싱 추가 (선택)

자주 묻는 질문 캐싱:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_faq_result(user_message):
    return call_dify_knowledge(user_message, top_k=3)
```

#### Step 5-3: 성능 모니터링

```python
# 각 단계별 시간 측정 추가
app.logger.info(f'FAQ search: {faq_time:.2f}s')
app.logger.info(f'Policy search: {policy_time:.2f}s')
app.logger.info(f'Answer generation: {answer_time:.2f}s')
app.logger.info(f'Total: {total_time:.2f}s')
```

---

## 체크리스트

### ✅ FAQ Dify 업로드
- [ ] FAQ Markdown 변환 완료 (102개 파일)
- [ ] Dify에 업로드 완료
- [ ] 새 Dataset ID 복사
- [ ] .env 파일 업데이트

### ✅ 백엔드 구현
- [ ] `extract_faq_id_from_content()` 함수 추가
- [ ] `faq_policy_map` 로드 코드 추가
- [ ] `/api/chat` 엔드포인트 수정
- [ ] `generate_answer_with_context()` 함수 추가
- [ ] `requirements.txt` 업데이트 및 설치

### ✅ 테스트
- [ ] 서버 시작 확인
- [ ] API 테스트 (curl)
- [ ] 로그 확인
- [ ] 프론트엔드 통합 테스트
- [ ] 다양한 질문으로 정확도 확인

---

## 예상 소요 시간

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Phase 1 | FAQ Dify 업로드 | 30분 |
| Phase 2 | 백엔드 구현 | 2-3시간 |
| Phase 3 | 테스트 | 30분 |
| Phase 4 | 프론트엔드 통합 | 10분 |
| Phase 5 | 최적화 (선택) | 1시간 |
| **총계** | | **약 4-5시간** |

---

## 문제 해결 가이드

### 문제 1: FAQ 검색 결과 없음

**증상**: `retrieval_count: 0`

**해결**:
1. Dify Dataset ID가 올바른지 확인
2. FAQ가 정상적으로 업로드되었는지 확인
3. Chunking이 정상적으로 완료되었는지 확인

### 문제 2: faq_id 추출 실패

**증상**: `"matched_faq_id": null`

**해결**:
1. FAQ Markdown 파일에 metadata가 포함되어 있는지 확인
2. `extract_faq_id_from_content()` 로그 확인
3. 정규식 패턴 조정

### 문제 3: policy_anchor 매핑 실패

**증상**: `related_laws: []`

**해결**:
1. `faq_topic.xlsx` 파일 경로 확인
2. faq_id가 정확히 일치하는지 확인
3. 매핑 테이블 로드 로그 확인

---

**다음 단계**: Phase 1부터 차근차근 진행하세요! 🚀
