# 민원처리 챗봇 실행 가이드

> 터미널 명령어 모음

---

## 📦 1. 패키지 설치

```bash
uv add pandas openpyxl flask openai python-dotenv requests
```

---

## 🗄️ 2. 데이터베이스 변환

### 법령 데이터 변환 (law.xlsx → SQLite)
```bash
uv run python convert_law_to_db_sheets.py
```

**결과**: `data/chatbot.db` 생성 (1,063개 법령)

### FAQ 업로드 (faq_topic.xlsx → Dify)
Dify 콘솔에서 `data/faq_topic.xlsx` 파일 업로드

---

## 🚀 3. 서버 실행

```bash
uv run python app.py
```

**브라우저 접속**: http://localhost:5000

---

## 🔧 4. DB 조회

### DB 파일 확인
```bash
# Windows
dir data\chatbot.db

# Mac/Linux
ls -lh data/chatbot.db
```

### DB 내용 확인
```bash
# Windows
sqlite3 data\chatbot.db "SELECT COUNT(*) FROM laws;"

# Mac/Linux
sqlite3 data/chatbot.db "SELECT COUNT(*) FROM laws;"
```

### Sheet 목록 조회
```bash
sqlite3 data/chatbot.db "SELECT DISTINCT sheet_name FROM laws;"
```

---

## 🎯 전체 프로젝트 실행 (처음부터)

```bash
# 1. 패키지 설치
uv add pandas openpyxl flask openai python-dotenv requests

# 2. 법령 DB 변환
uv run python convert_law_to_db_sheets.py

# 3. .env 파일 생성
echo OPENAI_API_KEY=sk-proj-your-key > .env
echo DIFY_API_URL=http://112.173.179.199:5001/v1 >> .env
echo DIFY_API_KEY=dataset-your-key >> .env
echo DIFY_DATASET_ID=your-dataset-id >> .env
echo AI_MODE=dify >> .env

# 4. 서버 실행
uv run python app.py
```

**브라우저**: http://localhost:5000

---

## 🔄 재실행 (이미 설치된 경우)

```bash
uv run python app.py
```

---

## 🛑 서버 종료

```bash
# 터미널에서 CTRL+C

# 또는 강제 종료 (Windows)
taskkill /F /IM python.exe

# Mac/Linux
pkill -f "python app.py"
```

---

## ✅ 완료 확인

- [ ] `data/chatbot.db` 파일 존재 (약 2-5MB)
- [ ] 서버 실행 성공 (http://localhost:5000)
- [ ] 브라우저에서 UI 확인
- [ ] `.env` 파일에 API 키 설정
