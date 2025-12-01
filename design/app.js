class ComplaintChatbot {
    constructor() {
        this.app = document.getElementById('app');
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.answerPanel = document.getElementById('answerPanel');
        this.lawPanel = document.getElementById('lawPanel');
        this.answerContent = document.getElementById('answerContent');
        this.lawContent = document.getElementById('lawContent');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.chatHistory = document.getElementById('chatHistory');
        this.rightPanels = document.getElementById('rightPanels');
        
        
        // 액션 버튼들
        this.editAnswerBtn = document.getElementById('editAnswerBtn');
        this.copyAnswerBtn = document.getElementById('copyAnswerBtn');
        this.editLawBtn = document.getElementById('editLawBtn');
        this.copyLawBtn = document.getElementById('copyLawBtn');
        
        // 법령 편집 패널 요소들
        this.lawEditPanel = document.getElementById('lawEditPanel');
        this.guidelineStep = document.getElementById('guidelineStep');
        this.articleStep = document.getElementById('articleStep');
        this.clauseStep = document.getElementById('clauseStep');
        this.guidelineList = document.getElementById('guidelineList');
        this.articleList = document.getElementById('articleList');
        this.clauseList = document.getElementById('clauseList');
        this.selectedGuidelineTitle = document.getElementById('selectedGuidelineTitle');
        this.selectedArticleTitle = document.getElementById('selectedArticleTitle');
        
        this.messages = [];
        this.chatSessions = [];
        this.currentSessionId = null;
        this.generateAnswerBtn = null;
        this.isEditMode = false;
        this.currentLawEditStep = 1;
        this.selectedClauses = []; // 선택된 항들
        this.currentSelectedGuideline = null; // 현재 선택된 지침
        this.currentSelectedArticle = null; // 현재 선택된 조항
        this.lastBotResponse = null; // API 응답 저장
        
        this.initializeEventListeners();
        this.createNewChat();
    }
    
    initializeEventListeners() {
        // onclick 속성으로 이벤트 중복 방지 (덮어쓰기 방식)
        this.sendButton.onclick = () => this.sendMessage();
        this.messageInput.onkeypress = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        };
        this.messageInput.oninput = () => this.autoResizeTextarea();

        this.newChatBtn.onclick = () => this.createNewChat();

        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.onclick = () => {
                const example = btn.getAttribute('data-example');
                this.messageInput.value = example;
                this.messageInput.focus();
            };
        });

        // 액션 버튼 이벤트 (onclick으로 중복 방지)
        this.editAnswerBtn.onclick = () => this.toggleEditMode('answer');
        this.copyAnswerBtn.onclick = () => this.copyContent('answer');
        this.editLawBtn.onclick = () => this.showLawEditPanel();
        this.copyLawBtn.onclick = () => this.copyContent('law');

        // 법령 편집 패널 이벤트 리스너
        this.initializeLawEditEventListeners();
    }
    
    createNewChat() {
        if (this.messages.length > 0) {
            this.saveChatSession();
        }
        this.currentSessionId = Date.now();
        this.messages = [];
        this.chatMessages.innerHTML = '';
        this.addChatHistoryItem(`새 채팅 ${this.chatHistory.children.length + 1}`);
        this.addWelcomeMessage();
        
        // 패널 닫기
        this.hidePanels();
        
        // 답변생성 버튼 제거
        this.removeGenerateAnswerBtn();
        
        // 수정 모드 해제
        this.exitEditMode();
    }
    
    addWelcomeMessage() {
        const welcomeMessage = {
            type: 'bot',
            content: '안녕하세요! 민원처리 챗봇입니다. 어떤 민원에 대해 문의하시나요? 자주 들어오는 민원 예시를 클릭하거나 직접 입력해주세요.',
            timestamp: new Date()
        };
        this.addMessage(welcomeMessage);
    }
    
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // 사용자 메시지 추가
        const userMessage = {
            type: 'user',
            content: message,
            timestamp: new Date()
        };
        this.addMessage(userMessage);
        
        // 답변생성 버튼 제거 (사용자가 새 메시지 입력)
        this.removeGenerateAnswerBtn();
        
        // 입력창 초기화
        this.messageInput.value = '';
        this.autoResizeTextarea();
        
        // 챗봇 응답 시뮬레이션
        setTimeout(() => {
            this.simulateBotResponse(message);
        }, 1000);
    }
    
    simulateBotResponse(userMessage) {
        const botResponse = this.generateBotResponse(userMessage);
        const botMessage = {
            type: 'bot',
            content: botResponse,
            timestamp: new Date()
        };
        this.addMessage(botMessage);
        
        // 챗봇 답변 완료 후 답변생성 버튼 표시
        setTimeout(() => {
            this.showGenerateAnswerBtn();
        }, 500);
    }
    
    generateBotResponse(userMessage) {
        const responses = [
            "해당 민원에 대해 자세히 살펴보겠습니다. 구체적인 상황을 더 설명해주시면 더 정확한 답변을 드릴 수 있습니다.",
            "이 민원은 관련 법령에 따라 처리됩니다. 답변생성 버튼을 클릭하시면 상세한 답변과 관련법령을 확인할 수 있습니다.",
            "민원 내용을 검토한 결과, 다음과 같은 절차로 진행하시면 됩니다. 자세한 내용은 답변생성 버튼을 통해 확인해주세요.",
            "해당 민원은 행정절차법에 따라 처리 가능합니다. 구체적인 처리 방법과 관련법령을 답변생성 버튼을 통해 안내드리겠습니다."
        ];
        return responses[Math.floor(Math.random() * responses.length)];
    }
    
    addMessage(message) {
        this.messages.push(message);
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.type}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = message.type === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message.content;
        
        messageElement.appendChild(avatar);
        messageElement.appendChild(content);
        
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    autoResizeTextarea() {
        const textarea = this.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
    
    // 답변생성 버튼 표시
    showGenerateAnswerBtn() {
        // 이미 버튼이 있다면 제거
        this.removeGenerateAnswerBtn();
        
        // 새로운 답변생성 버튼 생성
        this.generateAnswerBtn = document.createElement('button');
        this.generateAnswerBtn.id = 'generateAnswerBtn';
        this.generateAnswerBtn.className = 'generate-answer-btn';
        this.generateAnswerBtn.innerHTML = '<i class="fas fa-magic"></i> 답변생성';
        
        // 버튼을 채팅 메시지 영역 하단에 추가
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'generate-answer-container';
        buttonContainer.appendChild(this.generateAnswerBtn);
        
        this.chatMessages.appendChild(buttonContainer);
        
        // 이벤트 리스너 추가
        this.generateAnswerBtn.addEventListener('click', () => this.togglePanels());
        
        // 스크롤을 버튼이 보이도록 조정
        this.scrollToBottom();
    }
    
    // 답변생성 버튼 제거
    removeGenerateAnswerBtn() {
        if (this.generateAnswerBtn) {
            const buttonContainer = this.generateAnswerBtn.closest('.generate-answer-container');
            if (buttonContainer) {
                buttonContainer.remove();
            }
            this.generateAnswerBtn = null;
        }
    }
    
    // 패널 토글 (핵심 기능)
    togglePanels() {
        if (document.body.classList.contains('has-panels')) {
            this.hidePanels();
        } else {
            this.showPanels();
        }
    }
    
    async showPanels() {
        document.body.classList.add('has-panels');

        // 버튼 텍스트 변경
        if (this.generateAnswerBtn) {
            this.generateAnswerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 생성중...';
            this.generateAnswerBtn.style.background = '#8e8ea0';
        }

        // 마지막 사용자 메시지 가져오기
        const lastUserMessage = this.messages.filter(m => m.type === 'user').pop();
        const userQuestion = lastUserMessage ? lastUserMessage.content : '';

        try {
            // 실제 API 호출
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userQuestion,
                    session_id: this.currentSessionId
                })
            });

            const data = await response.json();

            if (data.success) {
                // API 응답 저장
                this.lastBotResponse = data;

                // 답변추천 업데이트
                if (data.suggested_answer) {
                    this.answerContent.innerHTML = data.suggested_answer;
                } else {
                    this.generateAnswer();
                }

                // 관련법령 업데이트
                this.updateLawContent();
            } else {
                console.error('API Error:', data.error);
                this.generateAnswer();
                this.updateLawContent();
            }
        } catch (error) {
            console.error('Fetch Error:', error);
            this.generateAnswer();
            this.updateLawContent();
        }

        // 버튼 텍스트 변경
        if (this.generateAnswerBtn) {
            this.generateAnswerBtn.innerHTML = '<i class="fas fa-times"></i> 답변닫기';
            this.generateAnswerBtn.style.background = '#e74c3c';
        }
    }
    
    hidePanels() {
        document.body.classList.remove('has-panels');
        
        // 버튼 텍스트 원복
        if (this.generateAnswerBtn) {
            this.generateAnswerBtn.innerHTML = '<i class="fas fa-magic"></i> 답변생성';
            this.generateAnswerBtn.style.background = '#8e8ea0';
            
            // 버튼에 애니메이션 효과 추가
            this.generateAnswerBtn.classList.add('button-pulse');
            setTimeout(() => {
                this.generateAnswerBtn.classList.remove('button-pulse');
            }, 1000);
        }
        
        // 수정 모드 해제
        this.exitEditMode();
    }
    
    // 수정 모드 토글
    toggleEditMode(section) {
        if (this.isEditMode) {
            this.saveEdit(section);
        } else {
            this.enterEditMode(section);
        }
    }
    
    // 수정 모드 진입
    enterEditMode(section) {
        this.isEditMode = true;
        
        if (section === 'answer') {
            this.answerContent.setAttribute('contenteditable', 'true');
            this.answerContent.focus();
            this.answerContent.style.outline = '2px solid #10a37f';
            this.answerContent.style.borderRadius = '6px';
            this.answerContent.style.padding = '8px';
        } else if (section === 'law') {
            this.lawContent.setAttribute('contenteditable', 'true');
            this.lawContent.focus();
            this.lawContent.style.outline = '2px solid #10a37f';
            this.lawContent.style.borderRadius = '6px';
            this.lawContent.style.padding = '8px';
        }
        
        // 버튼 텍스트 변경
        if (section === 'answer') {
            this.editAnswerBtn.innerHTML = '<i class="fas fa-save"></i> 저장';
        } else {
            this.editLawBtn.innerHTML = '<i class="fas fa-save"></i> 저장';
        }
    }
    
    // 수정 모드 해제
    exitEditMode() {
        this.isEditMode = false;
        
        // contenteditable 제거 및 스타일 초기화
        this.answerContent.removeAttribute('contenteditable');
        this.lawContent.removeAttribute('contenteditable');
        
        this.answerContent.style.outline = '';
        this.answerContent.style.borderRadius = '';
        this.answerContent.style.padding = '';
        
        this.lawContent.style.outline = '';
        this.lawContent.style.borderRadius = '';
        this.lawContent.style.padding = '';
        
        // 버튼 텍스트 원복
        this.editAnswerBtn.innerHTML = '<i class="fas fa-edit"></i> 수정';
        this.editLawBtn.innerHTML = '<i class="fas fa-edit"></i> 수정';
    }
    
    // 수정 내용 저장
    saveEdit(section) {
        if (section === 'answer') {
            console.log('답변추천 내용 저장됨');
        } else if (section === 'law') {
            console.log('관련법령 내용 저장됨');
        }
        
        this.exitEditMode();
    }
    
    // 내용 복사
    copyContent(section) {
        let content = '';
        
        if (section === 'answer') {
            content = this.stripHtml(this.answerContent.innerHTML);
        } else if (section === 'law') {
            content = this.stripHtml(this.lawContent.innerHTML);
        }
        
        if (content) {
            navigator.clipboard.writeText(content).then(() => {
                this.showCopyFeedback(section);
            }).catch(err => {
                this.fallbackCopy(content);
            });
        }
    }
    
    // HTML 태그 제거
    stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
    
    // 복사 성공 피드백
    showCopyFeedback(section) {
        const btn = section === 'answer' ? this.copyAnswerBtn : this.copyLawBtn;
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-check"></i> 복사됨';
        btn.style.background = '#10a37f';
        btn.style.color = 'white';
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = 'transparent';
            btn.style.color = '#8e8ea0';
        }, 2000);
    }
    
    // 클립보드 API 실패 시 fallback
    fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showCopyFeedback('answer');
        } catch (err) {
            console.error('복사 실패:', err);
        }
        
        document.body.removeChild(textArea);
    }
    
    generateAnswer() {
        const lastUserMessage = this.messages.filter(m => m.type === 'user').pop();
        if (!lastUserMessage) return;
        
        const answer = this.createDetailedAnswer(lastUserMessage.content);
        this.answerContent.innerHTML = answer;
    }
    
    createDetailedAnswer(userMessage) {
        return `
            <div class="answer-text">
                <h4>📋 민원 처리 답변</h4>
                <p>입력하신 민원 내용: "${userMessage}"</p>
                <p>해당 민원에 대한 상세한 답변을 제공해드립니다.</p>
                
                <div class="answer-details">
                    <div class="detail-item">
                        <strong>처리 절차:</strong> 민원 접수 → 검토 → 답변 작성 → 통보
                    </div>
                    <div class="detail-item">
                        <strong>처리 기간:</strong> 일반적으로 7일 이내
                    </div>
                    <div class="detail-item">
                        <strong>담당 부서:</strong> 민원처리과
                    </div>
                </div>
                
                <p>추가 문의사항이 있으시면 언제든 연락주세요.</p>
            </div>
        `;
    }
    
    updateLawContent() {
        // [핵심] 기존 내용 강제 초기화 (무조건 싹 지우고 시작)
        this.lawContent.innerHTML = '';

        // API 응답에서 관련 법령 가져오기
        if (this.lastBotResponse && this.lastBotResponse.related_laws &&
            this.lastBotResponse.related_laws.length > 0) {
            const laws = this.lastBotResponse.related_laws;

            this.lawContent.innerHTML = laws.map((law, index) => `
                <div class="law-item" data-clause-id="law-${index}">
                    <button class="law-item-remove" onclick="chatbot.removeLawItem('law-${index}')" title="이 항목 삭제">
                        <i class="fas fa-times"></i>
                    </button>
                    <div class="law-header">
                        <span class="law-sheet-name">${law.sheet_name || 'SQLite DB'}</span>
                    </div>
                    <div class="law-article-info">
                        <span class="law-article-num">${law.article_num || ''}</span>
                        <span class="law-article-title">${law.title || ''}</span>
                    </div>
                    <div class="law-content-text">
                        <p>${law.content || ''}</p>
                    </div>
                    ${law.matched_keyword ? `<div class="law-footer"><span class="law-keyword-tag">키워드: ${law.matched_keyword}</span></div>` : ''}
                </div>
            `).join('');
        } else {
            // 관련 법령이 없는 경우
            this.lawContent.innerHTML = `
                <div class="law-item empty">
                    <p>관련 법령을 찾지 못했습니다.</p>
                    <p>아래 "수정" 버튼을 눌러 직접 법령을 추가할 수 있습니다.</p>
                </div>
            `;
        }
    }
    
    saveChatSession() {
        const session = {
            id: this.currentSessionId,
            messages: [...this.messages],
            timestamp: new Date()
        };
        this.chatSessions.push(session);
        // TODO: DB에 저장
    }
    
    addChatHistoryItem(title) {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.innerHTML = `
            <i class="fas fa-comment"></i>
            <span>${title}</span>
        `;
        this.chatHistory.appendChild(chatItem);
    }
    
    // 법령 편집 패널 이벤트 리스너 초기화 (onclick으로 중복 방지)
    initializeLawEditEventListeners() {
        // 닫기 버튼들 (onclick으로 덮어쓰기)
        document.getElementById('closeFromGuideline').onclick = () => this.hideLawEditPanel();
        document.getElementById('closeFromArticle').onclick = () => this.hideLawEditPanel();
        document.getElementById('closeFromClause').onclick = () => this.hideLawEditPanel();

        // 뒤로가기 버튼들
        document.getElementById('backToGuideline').onclick = () => this.navigateLawPanel(1);
        document.getElementById('backToArticle').onclick = () => this.navigateLawPanel(2);

        // 선택된 항 적용 버튼
        document.getElementById('applySelected').onclick = () => this.applySelectedClauses();
    }
    
    // 법령 편집 패널 표시
    showLawEditPanel() {
        this.lawEditPanel.classList.add('show');
        this.currentLawEditStep = 1;
        this.selectedClauses = [];
        this.navigateLawPanel(1);
        this.loadGuidelineData();
    }
    
    // 법령 편집 패널 숨김
    hideLawEditPanel() {
        this.lawEditPanel.classList.remove('show');
        this.currentLawEditStep = 1;
        this.selectedClauses = [];
    }
    
    // 법령 편집 패널 단계 이동
    navigateLawPanel(step) {
        // 모든 단계 숨김
        this.guidelineStep.style.display = 'none';
        this.articleStep.style.display = 'none';
        this.clauseStep.style.display = 'none';
        
        // 현재 단계 표시
        this.currentLawEditStep = step;
        
        switch(step) {
            case 1:
                this.guidelineStep.style.display = 'flex';
                break;
            case 2:
                this.articleStep.style.display = 'flex';
                break;
            case 3:
                this.clauseStep.style.display = 'flex';
                break;
        }
    }
    
    // 지침 데이터 로드 (고정 데이터 사용)
    loadGuidelineData() {
        // LAW_DATA.guidelines 사용 (law_data.js에서 로드)
        this.renderGuidelineList(LAW_DATA.guidelines);
    }
    
    // 지침 목록 렌더링 (싹 지우고 다시 그리기)
    renderGuidelineList(guidelines) {
        // [핵심] 기존 내용 강제 초기화
        this.guidelineList.innerHTML = '';

        guidelines.forEach(guideline => {
            const button = document.createElement('button');
            button.className = 'guideline-btn';
            button.innerHTML = `
                <span class="guideline-name">${guideline.name}</span>
                <span class="guideline-desc">${guideline.description}</span>
            `;
            // onclick으로 이벤트 중복 방지
            button.onclick = () => this.selectGuideline(guideline);
            this.guidelineList.appendChild(button);
        });
    }
    
    // 지침 선택 (⭐ Sheet 이름 전달)
    selectGuideline(guideline) {
        this.selectedGuidelineTitle.textContent = guideline.name;
        this.currentSelectedGuideline = guideline; // 현재 선택된 지침 저장
        this.loadArticleData(guideline.id);  // ⭐ Sheet 이름 전달
        this.navigateLawPanel(2);
    }
    
    // 조항 데이터 로드 (고정 데이터 사용)
    loadArticleData(sheetName) {
        // LAW_DATA.articles 사용 (law_data.js에서 로드)
        const articles = LAW_DATA.articles[sheetName] || [];
        this.renderArticleList(articles);
    }
    
    // 조항 목록 렌더링 (싹 지우고 다시 그리기)
    renderArticleList(articles) {
        // [핵심] 기존 내용 강제 초기화
        this.articleList.innerHTML = '';

        articles.forEach(article => {
            const button = document.createElement('button');
            button.className = 'article-btn';
            button.innerHTML = `
                <span class="article-name">${article.name}</span>
                <span class="article-desc">${article.description}</span>
            `;
            // onclick으로 이벤트 중복 방지
            button.onclick = () => this.selectArticle(article);
            this.articleList.appendChild(button);
        });
    }
    
    // 조항 선택 (⭐ Sheet + 조번호 전달)
    selectArticle(article) {
        this.selectedArticleTitle.textContent = article.name;
        this.currentSelectedArticle = article; // 현재 선택된 조항 저장
        // ⭐ Sheet 이름 + 조번호 전달
        this.loadClauseData(this.currentSelectedGuideline.id, article.id);
        this.navigateLawPanel(3);
    }
    
    // 항 데이터 로드 (고정 데이터 사용)
    loadClauseData(sheetName, articleNum) {
        // LAW_DATA.paragraphs 사용 (law_data.js에서 로드)
        const paragraphs = LAW_DATA.paragraphs[sheetName]?.[articleNum] || [];

        // 렌더링용 형식으로 변환
        const clauses = paragraphs.map(para => ({
            id: para.id,
            title: para.title,
            content: para.content,
            guideline: { name: sheetName },
            article: { name: articleNum }
        }));

        this.renderClauseList(clauses);
    }
    
    // 항 목록 렌더링 (싹 지우고 다시 그리기, 복수선택 가능)
    renderClauseList(clauses) {
        // [핵심] 기존 내용 강제 초기화
        this.clauseList.innerHTML = '';

        clauses.forEach(clause => {
            const button = document.createElement('button');
            button.className = 'clause-btn';
            button.dataset.clauseId = clause.id;
            button.innerHTML = `
                <div class="clause-content">
                    <div class="clause-title">${clause.title}</div>
                    <div class="clause-text">${clause.content}</div>
                </div>
            `;
            // onclick으로 이벤트 중복 방지
            button.onclick = () => this.toggleClauseSelection(clause, button);
            this.clauseList.appendChild(button);
        });
    }
    
    // 항 선택/해제 토글
    toggleClauseSelection(clause, button) {
        const isSelected = button.classList.contains('selected');
        
        if (isSelected) {
            // 선택 해제
            button.classList.remove('selected');
            this.selectedClauses = this.selectedClauses.filter(c => c.id !== clause.id);
        } else {
            // 선택 - 지침과 조항 정보도 함께 저장
            button.classList.add('selected');
            const enrichedClause = {
                ...clause,
                guideline: this.currentSelectedGuideline,
                article: this.currentSelectedArticle
            };
            this.selectedClauses.push(enrichedClause);
        }
        
        this.updateSelectedCount();
    }
    
    // 선택된 항 개수 업데이트
    updateSelectedCount() {
        const applyButton = document.getElementById('applySelected');
        if (this.selectedClauses.length > 0) {
            applyButton.textContent = `선택된 항 적용 (${this.selectedClauses.length}개)`;
        } else {
            applyButton.textContent = '선택된 항 적용';
        }
    }
    
    // 선택된 항들을 관련법령에 적용 (싹 지우고 다시 그리기 방식)
    applySelectedClauses() {
        if (this.selectedClauses.length === 0) {
            alert('적용할 항을 선택해주세요.');
            return;
        }

        // 선택된 항들을 관련법령 패널에 표시 (지침, 조항, 항 정보 모두 포함)
        const selectedContent = this.selectedClauses.map(clause => `
            <div class="law-item" data-clause-id="${clause.id}">
                <button class="law-item-remove" onclick="chatbot.removeLawItem('${clause.id}')" title="이 항목 삭제">
                    <i class="fas fa-times"></i>
                </button>
                <div class="law-source">
                    <span class="law-guideline">${clause.guideline.name}</span>
                    <span class="law-article">${clause.article.name}</span>
                </div>
                <h4>${clause.title}</h4>
                <p>${clause.content}</p>
            </div>
        `).join('');

        // [핵심] 기존 내용 싹 지우고 새로 그리기 (덮어쓰기)
        this.lawContent.innerHTML = '';
        this.lawContent.innerHTML = selectedContent;

        console.log(`[Frontend] ${this.selectedClauses.length}개 항목 렌더링 완료`);

        // 패널 닫기
        this.hideLawEditPanel();

        // 성공 메시지 표시
        const detailMessage = this.selectedClauses.map(clause =>
            `${clause.guideline.name} ${clause.article.name} ${clause.title}`
        ).join(', ');
        this.showSuccessMessage(`${this.selectedClauses.length}개의 항이 적용되었습니다: ${detailMessage}`);
    }
    
    // 성공 메시지 표시
    showSuccessMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            z-index: 2000;
            font-weight: 500;
        `;
        messageElement.textContent = message;
        document.body.appendChild(messageElement);
        
        setTimeout(() => {
            messageElement.remove();
        }, 3000);
    }
    
    // 개별 법령 항목 삭제
    removeLawItem(clauseId) {
        const lawItem = this.lawContent.querySelector(`[data-clause-id="${clauseId}"]`);
        if (lawItem) {
            // 삭제 확인
            const lawTitle = lawItem.querySelector('h4').textContent;
            if (confirm(`"${lawTitle}" 항목을 삭제하시겠습니까?`)) {
                // 부드러운 삭제 애니메이션
                lawItem.style.transition = 'all 0.3s ease';
                lawItem.style.transform = 'translateX(100%)';
                lawItem.style.opacity = '0';
                
                setTimeout(() => {
                    lawItem.remove();
                    this.showSuccessMessage('항목이 삭제되었습니다.');
                    
                    // TODO: DB에서도 삭제
                    console.log('법령 항목 삭제됨:', clauseId);
                }, 300);
            }
        }
    }
}

// 앱 초기화
let chatbot;
document.addEventListener('DOMContentLoaded', () => {
    chatbot = new ComplaintChatbot();
});
