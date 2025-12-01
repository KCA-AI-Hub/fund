# 민원처리 챗봇 하이브리드 RAG 전략

> **핵심 아키텍처**: Dify RAG (FAQ) + SQLite (법령) + OpenAI GPT (답변 생성)

---

## 📊 시스템 구조

### 데이터 저장 전략

```
FAQ (102개)          →  Dify 지식베이스 (시맨틱 검색 + Reranking)
법령 (1,063개)       →  SQLite DB (정확한 SQL 검색)
답변 생성            →  OpenAI GPT-4o-mini (컨텍스트 기반)
```

### 선택 이유

| 데이터 | 저장소 | 이유 |
|--------|--------|------|
| **FAQ** | Dify | 자연어 이해 필요 (시맨틱 검색), Reranking으로 정확도 향상 |
| **법령** | SQLite | policy_anchor로 정확한 키워드 매칭, 파일 크기 제한 없음, 빠른 검색 |

---

## 🔄 답변 생성 플로우

```
사용자 질문
    ↓
┌─────────────────────────────────────────────┐
│ STEP 1: FAQ 검색 (Dify API)                │
│ - 시맨틱 검색으로 유사 FAQ 찾기              │
│ - Reranking으로 정확도 향상                 │
│ - Top 3 FAQ 반환 (score 포함)              │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ STEP 2: faq_id 추출                        │
│ - best_faq (최고 score) 사용                │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ STEP 3: policy_anchor 매핑                 │
│ - faq_topic.xlsx에서 관련 법령 참조 찾기    │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ STEP 4: 법령 검색 (SQLite)                 │
│ - policy_anchor로 법령 키워드 검색          │
│ - LIKE 패턴 매칭으로 관련 법령 추출         │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ STEP 5: OpenAI GPT 답변 생성                │
│ - Context: FAQ 답변 + 법령 전체 텍스트      │
│ - GPT-4o-mini로 답변 생성                   │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ STEP 6: 응답 반환                           │
│ - message: GPT 답변                         │
│ - suggested_answer: HTML 포맷 답변          │
│ - related_laws: policy_anchor 기반 법령     │
└─────────────────────────────────────────────┘
```

---

## 🗄️ 데이터베이스 스키마 (SQLite)

### laws 테이블

```sql
CREATE TABLE laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id TEXT UNIQUE NOT NULL,
    law_title TEXT NOT NULL,
    sheet_name TEXT NOT NULL,              -- Sheet 이름 (14개)
    chapter_num TEXT,
    chapter_title TEXT,
    article_num TEXT,                      -- 조번호 (제1조, 제2조...)
    article_title TEXT,                    -- 조항 제목
    paragraph_num REAL,                    -- 항번호
    paragraph_content TEXT,                -- 항 내용
    clause_num REAL,
    clause_content TEXT,
    item_num TEXT,
    item_content TEXT,
    full_text TEXT NOT NULL,               -- 전체 텍스트 (검색용)
    first_effective_date DATE,
    amendment_date DATE,
    is_active BOOLEAN DEFAULT 1,
    tags TEXT
);

CREATE INDEX idx_sheet_name ON laws(sheet_name);
CREATE INDEX idx_article_num ON laws(article_num);
CREATE INDEX idx_tags ON laws(tags);
CREATE INDEX idx_full_text ON laws(full_text);
```

**데이터 구조**: 14개 Sheet → 조(Article) → 항(Paragraph)

---

## 📂 파일 구조

```
test_dify/
├── data/
│   ├── law.xlsx                          # 법령 원본 (14 sheets, 1,063개)
│   ├── faq_topic.xlsx                    # FAQ 원본 (102개) → Dify 업로드
│   └── chatbot.db                        # SQLite DB (법령만)
│
├── app.py                                # Flask 서버 (Dify + SQLite 하이브리드)
├── database.py                           # SQLite 쿼리 함수 (법령 검색)
├── convert_law_to_db_sheets.py          # 법령 변환 스크립트
│
├── design/                               # 프론트엔드 (ChatGPT 스타일)
│   ├── index.html
│   ├── script.js
│   ├── app.js
│   └── styles.css
│
└── improve/
    ├── strategy.md                       # 이 문서
    └── strategy_easy.md                  # 초보자용 가이드
```

---

## 🔧 주요 함수

### app.py

| 함수 | 역할 |
|------|------|
| `call_dify_knowledge()` | Dify API 호출 (FAQ 검색, Reranking) |
| `extract_faq_id_from_content()` | Dify 응답에서 faq_id 추출 |
| `get_policy_anchor()` | faq_topic.xlsx에서 법령 참조 찾기 |
| `generate_answer_with_context()` | FAQ + 법령 컨텍스트로 GPT 답변 생성 |
| `generate_suggested_answer()` | HTML 포맷 답변 생성 |

### database.py (법령 검색 전용)

| 함수 | 역할 |
|------|------|
| `search_laws(keyword, limit)` | 키워드로 법령 검색 (LIKE 패턴) |
| `get_sheet_list()` | 14개 Sheet 목록 반환 |
| `get_articles_by_sheet()` | Sheet별 조항 목록 |
| `get_paragraphs_by_article()` | 조항별 항 목록 |

---

## 🚀 실행 방법

### 1. 초기 설정

```bash
# 패키지 설치
uv add pandas openpyxl flask openai python-dotenv requests

# 법령 데이터 변환
uv run python convert_law_to_db_sheets.py

# FAQ 업로드 (Dify 콘솔)
# faq_topic.xlsx를 Dify 지식베이스에 업로드
```

### 2. 환경 변수 설정 (.env)

```bash
OPENAI_API_KEY=sk-proj-...
DIFY_API_URL=http://112.173.179.199:5001/v1
DIFY_API_KEY=dataset-...
DIFY_DATASET_ID=...
AI_MODE=dify
```

### 3. 서버 실행

```bash
python app.py
```

### 4. 브라우저 접속

```
http://localhost:5000
```

---

## 🎯 핵심 개선 사항

### Phase A: 법령 검색 하이브리드 통합 ✅

**완료**: app.py STEP 4를 SQLite 기반으로 수정
- Dify에서 법령 검색 → SQLite에서 법령 검색
- FAQ는 Dify 유지 (시맨틱 검색 + Reranking)

### Phase B: 검색 품질 개선

1. **법령 중복 제거** ✅
   - law_id 기준으로 중복 제거 완료

2. **GPT 컨텍스트 확장** ✅
   - 법령 전체 텍스트를 GPT에 전달 (200자 → 전체)
   - FAQ 답변 + 법령 3개 전체 포함

3. **관련도 점수 기반 검색** (추후)
   - 조항 제목 매칭: 10점
   - 태그 매칭: 5점
   - 항 내용 매칭: 3점
   - 전체 텍스트 매칭: 1점

---

## 📊 데이터 흐름 예시

### 질문: "사업비 교부는 어떻게 받나요?"

```
STEP 1: Dify FAQ 검색
→ 시맨틱 검색 결과:
  {score: 0.89, faq_id: "FAQ-사업비-0005", content: "..."}
  {score: 0.76, faq_id: "FAQ-교부금-0012", content: "..."}

STEP 2: faq_id 추출
→ "FAQ-사업비-0005" (best match)

STEP 3: policy_anchor 매핑
→ "기금운영지침 제10조; 사업비 교부"

STEP 4: SQLite 법령 검색
→ SELECT * FROM laws
   WHERE full_text LIKE '%기금운영지침 제10조%'
      OR full_text LIKE '%사업비 교부%'
→ 결과: [법령1, 법령2]

STEP 5: GPT 답변 생성
→ Context:
  [참고 FAQ 1]
  질문: 사업비 교부는...
  답변: 협약 체결 후...

  [참고 법령 1]
  기금운영지침 제10조 (전체 텍스트)

  [참고 법령 2]
  사업비 교부 관련 조항 (전체 텍스트)

→ GPT가 컨텍스트 기반 답변 생성

STEP 6: 응답 반환
{
  message: "사업비 교부는 협약 체결 후...",
  suggested_answer: "<h4>📌 핵심 답변</h4>...",
  related_laws: [
    {title: "기금운영지침 제10조", source: "FAQ Database"},
    {title: "사업비 교부", source: "FAQ Database"}
  ]
}
```

---

## 🔍 Reranking 설명

### Dify RAG Reranking (STEP 1)

```python
# app.py:407-420
payload = {
    "query": user_message,
    "retrieval_model": {
        "search_method": "semantic_search",
        "reranking_enable": True,          # ✨ Reranking 활성화
        "top_k": 3,
        "score_threshold": 0.5
    }
}
```

**Reranking 프로세스**:
1. 임베딩 검색으로 100개 후보 찾기
2. Reranking 모델로 재정렬 (관련도 높은 순)
3. top_k=3개만 반환 (score 포함)

**SQLite는 Reranking 없음**:
- policy_anchor가 정확한 키워드 제공 → LIKE 검색으로 충분
- 빠른 검색 속도 (인덱싱)

---

## 🎯 이 전략의 장점

### 1. 최적화된 검색
- FAQ: 자연어 이해 (Dify Reranking)
- 법령: 정확한 키워드 매칭 (SQLite)

### 2. 비용 효율
- Dify API 호출 1번만 (FAQ)
- 법령은 로컬 SQLite (무료, 빠름)

### 3. 확장성
- 법령 데이터 증가해도 파일 크기 제한 없음
- Dify 용량 절약

### 4. 정확성
- policy_anchor로 FAQ-법령 연결
- GPT가 정확한 법령 컨텍스트 참고

---

## ✅ 구현 완료 상태

- [x] SQLite DB 구축 (1,063개 법령)
- [x] Dify 지식베이스 구축 (102개 FAQ)
- [x] app.py 하이브리드 RAG 구현
- [x] database.py 법령 검색 함수
- [x] 프론트엔드 연동 (design/)
- [x] 법령 중복 제거
- [x] GPT 컨텍스트 확장

---

## 📝 결론

이 전략은 **Dify RAG의 시맨틱 검색 장점**과 **SQLite의 빠른 정확한 검색**을 결합한 하이브리드 아키텍처입니다.

**핵심 원칙**:
- FAQ는 자연어 이해가 중요 → Dify (Reranking)
- 법령은 정확한 참조가 중요 → SQLite (policy_anchor)
- 답변은 컨텍스트가 중요 → OpenAI GPT

**최종 목표**: 직원이 민원 질문을 입력하면 자동으로 FAQ와 법령을 참고한 정확한 답변 초안을 제공
