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
        
        // Session ID 관리 (백엔드 연결용)
        this.sessionId = localStorage.getItem('sessionId') || null;
        
        this.messages = [];
        this.chatSessions = [];
        this.currentSessionId = null;
        this.generateAnswerBtn = null;
        this.isEditMode = false;
        this.currentLawEditStep = 1;
        this.selectedClauses = []; // 선택된 항들
        this.currentSelectedGuideline = null; // 현재 선택된 지침
        this.currentSelectedArticle = null; // 현재 선택된 조항

        // 2단계 플로우를 위한 상태
        this.awaitingConfirmation = false;  // 확인 대기 중
        this.pendingQuestion = null;        // 대기 중인 질문
        this.lastBotResponse = null;        // API 응답 저장 (suggested_answer, related_laws)

        this.initializeEventListeners();
        this.createNewChat();
    }
    
    initializeEventListeners() {
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
        }
        
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', () => this.createNewChat());
        }
        
        // 예시 버튼 이벤트 리스너
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const example = btn.getAttribute('data-example');
                if (this.messageInput) {
                    this.messageInput.value = example;
                    this.messageInput.focus();
                    this.autoResizeTextarea();
                }
            });
        });
        
        // 액션 버튼 이벤트 리스너
        if (this.editAnswerBtn) {
            this.editAnswerBtn.addEventListener('click', () => this.toggleEditMode('answer'));
        }
        if (this.copyAnswerBtn) {
            this.copyAnswerBtn.addEventListener('click', () => this.copyContent('answer'));
        }
        if (this.editLawBtn) {
            this.editLawBtn.addEventListener('click', () => this.showLawEditPanel());
        }
        if (this.copyLawBtn) {
            this.copyLawBtn.addEventListener('click', () => this.copyContent('law'));
        }
        
        // 법령 편집 패널 이벤트 리스너
        this.initializeLawEditEventListeners();
    }
    
    createNewChat() {
        if (this.messages.length > 0) {
            this.saveChatSession();
        }
        this.currentSessionId = Date.now();
        this.sessionId = null;
        localStorage.removeItem('sessionId');
        this.messages = [];
        
        if (this.chatMessages) {
            this.chatMessages.innerHTML = '';
        }
        
        if (this.chatHistory) {
            this.addChatHistoryItem(`새 채팅 ${this.chatHistory.children.length + 1}`);
        }
        this.addWelcomeMessage();
        
        // 패널 닫기
        this.hidePanels();
        
        // 답변생성 버튼 제거
        this.removeGenerateAnswerBtn();
        
        // 수정 모드 해제
        this.exitEditMode();
        
        // 새 세션 생성 (백엔드 API)
        this.createNewSession();
    }
    
    // 백엔드 새 세션 생성
    async createNewSession() {
        try {
            const response = await fetch('/api/new-session', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.session_id) {
                this.sessionId = data.session_id;
                localStorage.setItem('sessionId', this.sessionId);
            }
        } catch (error) {
            console.error('Error creating new session:', error);
        }
    }
    
    addWelcomeMessage() {
        const welcomeMessage = {
            type: 'bot',
            content: '안녕하세요! 민원처리 챗봇입니다. 어떤 민원에 대해 문의하시나요? 자주 들어오는 민원 예시를 클릭하거나 직접 입력해주세요.',
            timestamp: new Date()
        };
        this.addMessage(welcomeMessage);
    }

    // 사용자 응답이 확인(긍정)인지 판단
    isConfirmationResponse(message) {
        const confirmWords = ['네', '맞아요', '맞습니다', '예', 'yes', 'ok', '응', '맞음', '맞', '그래'];
        const lowerMessage = message.toLowerCase().trim();
        return confirmWords.some(word => lowerMessage.includes(word));
    }

    // 1단계: 질문 확인 (API 호출)
    async confirmQuestion(question) {
        this.showTypingIndicator();

        try {
            const response = await fetch('/api/chat/confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: question,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                throw new Error(`API 호출 실패: ${response.status}`);
            }

            const data = await response.json();

            this.hideTypingIndicator();

            if (data.success) {
                // 확인 메시지를 봇 메시지로 추가
                const confirmMessage = {
                    type: 'bot',
                    content: data.message,
                    timestamp: new Date()
                };
                this.addMessage(confirmMessage);

                // 상태 설정
                this.awaitingConfirmation = true;
                this.pendingQuestion = question;

                return true;
            } else {
                throw new Error(data.error || '확인 질문 생성 실패');
            }

        } catch (error) {
            console.error('confirmQuestion 오류:', error);
            this.hideTypingIndicator();

            // 에러 메시지 표시
            const errorMessage = {
                type: 'bot',
                content: '질문 확인 중 오류가 발생했습니다. 다시 시도해주세요.',
                timestamp: new Date()
            };
            this.addMessage(errorMessage);

            return false;
        }
    }

    // 2단계: 실제 FAQ RAG 답변 생성 (API 호출)
    async generateActualAnswer(question) {
        this.showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: question,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                throw new Error(`API 호출 실패: ${response.status}`);
            }

            const data = await response.json();

            this.hideTypingIndicator();

            if (data.success) {
                // 세션 ID 저장
                if (data.session_id) {
                    this.sessionId = data.session_id;
                    localStorage.setItem('sessionId', this.sessionId);
                }

                // 실제 답변을 봇 메시지로 추가
                const answerMessage = {
                    type: 'bot',
                    content: data.message,
                    timestamp: new Date()
                };
                this.addMessage(answerMessage);

                // API 응답 저장 (suggested_answer, related_laws 포함)
                this.lastBotResponse = {
                    suggested_answer: data.suggested_answer || null,
                    related_laws: data.related_laws || [],
                    metadata: data.metadata || {}
                };

                // 상태 리셋
                this.awaitingConfirmation = false;
                this.pendingQuestion = null;

                // 답변생성 버튼 표시
                setTimeout(() => {
                    this.showGenerateAnswerBtn();
                }, 500);

                return true;
            } else {
                throw new Error(data.error || '답변 생성 실패');
            }

        } catch (error) {
            console.error('generateActualAnswer 오류:', error);
            this.hideTypingIndicator();

            // 에러 메시지 표시
            const errorMessage = {
                type: 'bot',
                content: '답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
                timestamp: new Date()
            };
            this.addMessage(errorMessage);

            // 상태 리셋
            this.awaitingConfirmation = false;
            this.pendingQuestion = null;

            return false;
        }
    }

    async sendMessage() {
        if (!this.messageInput) return;

        const message = this.messageInput.value.trim();
        if (!message) return;

        // 버튼 비활성화
        if (this.sendButton) {
            this.sendButton.disabled = true;
        }

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

        // 타이핑 인디케이터 표시
        this.showTypingIndicator();

        try {
            // 백엔드 API 호출
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (data.success) {
                // 세션 ID 저장
                if (data.session_id) {
                    this.sessionId = data.session_id;
                    localStorage.setItem('sessionId', this.sessionId);
                }

                // 타이핑 인디케이터 제거
                this.hideTypingIndicator();

                // AI 응답 추가
                const botMessage = {
                    type: 'bot',
                    content: data.message,
                    timestamp: new Date()
                };
                this.addMessage(botMessage);

                // API 응답 저장 (suggested_answer, related_laws 포함)
                this.lastBotResponse = {
                    suggested_answer: data.suggested_answer || null,
                    related_laws: data.related_laws || [],
                    metadata: data.metadata || {}
                };

                // 답변생성 버튼 표시
                setTimeout(() => {
                    this.showGenerateAnswerBtn();
                }, 500);

            } else {
                this.hideTypingIndicator();
                this.simulateBotResponse(message);
            }
        } catch (error) {
            console.error('Error:', error);
            this.hideTypingIndicator();
            // 백엔드 연결 실패시 시뮬레이션 모드
            this.simulateBotResponse(message);
        } finally {
            if (this.sendButton) {
                this.sendButton.disabled = false;
            }
        }
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
        
        if (!this.chatMessages) return;
        
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
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
    
    autoResizeTextarea() {
        if (!this.messageInput) return;
        
        const textarea = this.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
    
    // 타이핑 인디케이터 표시
    showTypingIndicator() {
        if (!this.chatMessages) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message bot';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="width: 8px; height: 8px; background: #6b7280; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out;"></span>
                <span style="width: 8px; height: 8px; background: #6b7280; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; animation-delay: -0.32s;"></span>
                <span style="width: 8px; height: 8px; background: #6b7280; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; animation-delay: -0.16s;"></span>
            </div>
            <style>
                @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
            </style>
        `;
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(content);
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    // 타이핑 인디케이터 제거
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
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
    
    showPanels() {
        document.body.classList.add('has-panels');
        this.generateAnswer();
        this.updateLawContent();
        
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
        
        if (section === 'answer' && this.answerContent) {
            this.answerContent.setAttribute('contenteditable', 'true');
            this.answerContent.focus();
            this.answerContent.style.outline = '2px solid #10a37f';
            this.answerContent.style.borderRadius = '6px';
            this.answerContent.style.padding = '8px';
        } else if (section === 'law' && this.lawContent) {
            this.lawContent.setAttribute('contenteditable', 'true');
            this.lawContent.focus();
            this.lawContent.style.outline = '2px solid #10a37f';
            this.lawContent.style.borderRadius = '6px';
            this.lawContent.style.padding = '8px';
        }
        
        // 버튼 텍스트 변경
        if (section === 'answer' && this.editAnswerBtn) {
            this.editAnswerBtn.innerHTML = '<i class="fas fa-save"></i> 저장';
        } else if (this.editLawBtn) {
            this.editLawBtn.innerHTML = '<i class="fas fa-save"></i> 저장';
        }
    }
    
    // 수정 모드 해제
    exitEditMode() {
        this.isEditMode = false;
        
        // contenteditable 제거 및 스타일 초기화
        if (this.answerContent) {
            this.answerContent.removeAttribute('contenteditable');
            this.answerContent.style.outline = '';
            this.answerContent.style.borderRadius = '';
            this.answerContent.style.padding = '';
        }
        
        if (this.lawContent) {
            this.lawContent.removeAttribute('contenteditable');
            this.lawContent.style.outline = '';
            this.lawContent.style.borderRadius = '';
            this.lawContent.style.padding = '';
        }
        
        // 버튼 텍스트 원복
        if (this.editAnswerBtn) {
            this.editAnswerBtn.innerHTML = '<i class="fas fa-edit"></i> 수정';
        }
        if (this.editLawBtn) {
            this.editLawBtn.innerHTML = '<i class="fas fa-edit"></i> 수정';
        }
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
        
        if (section === 'answer' && this.answerContent) {
            content = this.stripHtml(this.answerContent.innerHTML);
        } else if (section === 'law' && this.lawContent) {
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
        if (!btn) return;
        
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
        if (!this.answerContent) return;

        // FAQ RAG 데이터가 있으면 사용, 없으면 fallback
        if (this.lastBotResponse && this.lastBotResponse.suggested_answer) {
            this.answerContent.innerHTML = this.lastBotResponse.suggested_answer;
        } else {
            // Fallback: 마지막 사용자 메시지 기반 더미 답변
            const lastUserMessage = this.messages.filter(m => m.type === 'user').pop();
            if (!lastUserMessage) return;

            const answer = this.createDetailedAnswer(lastUserMessage.content);
            this.answerContent.innerHTML = answer;
        }
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
        if (!this.lawContent) return;

        // ========================================
        // 🔗 관련법령 데이터 연결 (FAQ RAG 기반)
        // ========================================

        // FAQ RAG 데이터가 있으면 사용, 없으면 fallback
        if (this.lastBotResponse && this.lastBotResponse.related_laws && this.lastBotResponse.related_laws.length > 0) {
            const laws = this.lastBotResponse.related_laws;

            this.lawContent.innerHTML = laws.map((law, index) => `
                <div class="law-item" data-clause-id="rag-${index}">
                    <button class="law-item-remove" onclick="chatbot.removeLawItem('rag-${index}')" title="이 항목 삭제">
                        <i class="fas fa-times"></i>
                    </button>
                    <div class="law-source">
                        <span class="law-guideline">📋 FAQ RAG</span>
                        ${law.faq_id ? `<small>FAQ ID: ${law.faq_id}</small>` : ''}
                    </div>
                    <h4>${law.title || 'N/A'}</h4>
                    <p>${law.content || law.summary || 'N/A'}</p>
                    ${law.source ? `<p><small>출처: ${law.source}</small></p>` : ''}
                </div>
            `).join('');
        } else {
            // Fallback: 더미 법령 데이터
            const laws = [
                {
                    id: 'default-1',
                    title: '민원사무처리에 관한 법률',
                    content: '제1조 (목적) 이 법은 민원사무의 처리에 관한 기본사항을 정함으로써 민원사무의 신속하고 공정한 처리와 국민의 권익보호를 도모함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                },
                {
                    id: 'default-2',
                    title: '행정절차법',
                    content: '제1조 (목적) 이 법은 행정청의 처리가 국민의 권리와 의무에 직접적인 영향을 미치는 행정절차에 대하여 공통적으로 적용될 사항을 규정함으로써 행정의 공정성과 투명성을 확보하고 국민의 권익을 보호함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                },
                {
                    id: 'default-3',
                    title: '정보공개법',
                    content: '제1조 (목적) 이 법은 공공기관이 보유·관리하는 정보를 국민의 알권리 보장과 국정에 대한 국민의 참여와 국정에 대한 국민의 감시를 위하여 국민에게 공개하도록 함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                }
            ];

            this.lawContent.innerHTML = laws.map(law => `
                <div class="law-item" data-clause-id="${law.id}">
                    <button class="law-item-remove" onclick="chatbot.removeLawItem('${law.id}')" title="이 항목 삭제">
                        <i class="fas fa-times"></i>
                    </button>
                    <div class="law-source">
                        <span class="law-guideline">📋 기본법령</span>
                    </div>
                    <h4>${law.title}</h4>
                    <p>${law.content}</p>
                    <div class="law-articles">
                        ${law.articles.map(article => `<span class="article-tag">${article}</span>`).join('')}
                    </div>
                </div>
            `).join('');
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
        if (!this.chatHistory) return;
        
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.innerHTML = `
            <i class="fas fa-comment"></i>
            <span>${title}</span>
        `;
        this.chatHistory.appendChild(chatItem);
    }
    
    // 법령 편집 패널 이벤트 리스너 초기화
    initializeLawEditEventListeners() {
        // 닫기 버튼들
        const closeFromGuideline = document.getElementById('closeFromGuideline');
        const closeFromArticle = document.getElementById('closeFromArticle');
        const closeFromClause = document.getElementById('closeFromClause');
        
        if (closeFromGuideline) {
            closeFromGuideline.addEventListener('click', () => this.hideLawEditPanel());
        }
        if (closeFromArticle) {
            closeFromArticle.addEventListener('click', () => this.hideLawEditPanel());
        }
        if (closeFromClause) {
            closeFromClause.addEventListener('click', () => this.hideLawEditPanel());
        }
        
        // 뒤로가기 버튼들
        const backToGuideline = document.getElementById('backToGuideline');
        const backToArticle = document.getElementById('backToArticle');
        
        if (backToGuideline) {
            backToGuideline.addEventListener('click', () => this.navigateLawPanel(1));
        }
        if (backToArticle) {
            backToArticle.addEventListener('click', () => this.navigateLawPanel(2));
        }
        
        // 선택된 항 적용 버튼
        const applySelected = document.getElementById('applySelected');
        if (applySelected) {
            applySelected.addEventListener('click', () => this.applySelectedClauses());
        }
    }
    
    // 법령 편집 패널 표시
    showLawEditPanel() {
        if (this.lawEditPanel) {
            this.lawEditPanel.classList.add('show');
            this.currentLawEditStep = 1;
            this.selectedClauses = [];
            this.navigateLawPanel(1);
            this.loadGuidelineData();
        }
    }
    
    // 법령 편집 패널 숨김
    hideLawEditPanel() {
        if (this.lawEditPanel) {
            this.lawEditPanel.classList.remove('show');
            this.currentLawEditStep = 1;
            this.selectedClauses = [];
        }
    }
    
    // 법령 편집 패널 단계 이동
    navigateLawPanel(step) {
        // 모든 단계 숨김
        if (this.guidelineStep) this.guidelineStep.style.display = 'none';
        if (this.articleStep) this.articleStep.style.display = 'none';
        if (this.clauseStep) this.clauseStep.style.display = 'none';
        
        // 현재 단계 표시
        this.currentLawEditStep = step;
        
        switch(step) {
            case 1:
                if (this.guidelineStep) this.guidelineStep.style.display = 'flex';
                break;
            case 2:
                if (this.articleStep) this.articleStep.style.display = 'flex';
                break;
            case 3:
                if (this.clauseStep) this.clauseStep.style.display = 'flex';
                break;
        }
    }
    
    // 지침 데이터 로드 (더미 데이터)
    loadGuidelineData() {
        // TODO: DB에서 지침 데이터 가져오기
        const guidelines = [
            { id: 'aa', name: 'AA지침', description: '민원처리 기본 지침' },
            { id: 'bb', name: 'BB지침', description: '행정절차 관련 지침' },
            { id: 'cc', name: 'CC지침', description: '정보공개 처리 지침' },
            { id: 'dd', name: 'DD지침', description: '민원인 권리보호 지침' },
            { id: 'ee', name: 'EE지침', description: '전자민원 처리 지침' }
        ];
        
        this.renderGuidelineList(guidelines);
    }
    
    // 지침 목록 렌더링
    renderGuidelineList(guidelines) {
        if (!this.guidelineList) return;
        
        this.guidelineList.innerHTML = '';
        
        guidelines.forEach(guideline => {
            const button = document.createElement('button');
            button.className = 'guideline-btn';
            button.innerHTML = `
                <span class="guideline-name">${guideline.name}</span>
                <span class="guideline-desc">${guideline.description}</span>
            `;
            button.addEventListener('click', () => this.selectGuideline(guideline));
            this.guidelineList.appendChild(button);
        });
    }
    
    // 지침 선택
    selectGuideline(guideline) {
        if (this.selectedGuidelineTitle) {
            this.selectedGuidelineTitle.textContent = guideline.name;
        }
        this.currentSelectedGuideline = guideline; // 현재 선택된 지침 저장
        this.loadArticleData(guideline.id);
        this.navigateLawPanel(2);
    }
    
    // 조항 데이터 로드 (더미 데이터)
    loadArticleData(guidelineId) {
        // TODO: DB에서 선택된 지침의 조항 데이터 가져오기
        const articles = [
            { id: '1', name: '1조(목적)', description: '이 지침의 목적을 규정' },
            { id: '2', name: '2조(점검방법)', description: '민원처리 점검방법을 규정' },
            { id: '3', name: '3조(처리기한)', description: '민원처리 기한을 규정' },
            { id: '4', name: '4조(담당자)', description: '민원처리 담당자를 규정' },
            { id: '5', name: '5조(이의신청)', description: '민원처리 이의신청 절차를 규정' }
        ];
        
        this.renderArticleList(articles);
    }
    
    // 조항 목록 렌더링
    renderArticleList(articles) {
        if (!this.articleList) return;
        
        this.articleList.innerHTML = '';
        
        articles.forEach(article => {
            const button = document.createElement('button');
            button.className = 'article-btn';
            button.innerHTML = `
                <span class="article-name">${article.name}</span>
                <span class="article-desc">${article.description}</span>
            `;
            button.addEventListener('click', () => this.selectArticle(article));
            this.articleList.appendChild(button);
        });
    }
    
    // 조항 선택
    selectArticle(article) {
        if (this.selectedArticleTitle) {
            this.selectedArticleTitle.textContent = article.name;
        }
        this.currentSelectedArticle = article; // 현재 선택된 조항 저장
        this.loadClauseData(article.id);
        this.navigateLawPanel(3);
    }
    
    // 항 데이터 로드 (더미 데이터)
    loadClauseData(articleId) {
        // TODO: DB에서 선택된 조항의 항 데이터 가져오기
        const clauses = [
            { 
                id: '1-1', 
                title: '1항', 
                content: '민원사무의 처리에 관한 기본사항을 정함으로써 민원사무의 신속하고 공정한 처리와 국민의 권익보호를 도모함을 목적으로 한다.' 
            },
            { 
                id: '1-2', 
                title: '2항', 
                content: '이 법에서 정하지 아니한 사항에 대하여는 다른 법률이 정하는 바에 따른다.' 
            },
            { 
                id: '1-3', 
                title: '3항', 
                content: '민원처리기관은 민원인의 권익보호와 편의증진을 위하여 노력하여야 한다.' 
            },
            { 
                id: '1-4', 
                title: '4항', 
                content: '민원처리기관은 민원사무를 처리할 때 관련 법령과 기준에 따라 공정하고 투명하게 처리하여야 한다.' 
            }
        ];
        
        this.renderClauseList(clauses);
    }
    
    // 항 목록 렌더링 (복수선택 가능)
    renderClauseList(clauses) {
        if (!this.clauseList) return;
        
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
            button.addEventListener('click', () => this.toggleClauseSelection(clause, button));
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
        if (applyButton) {
            if (this.selectedClauses.length > 0) {
                applyButton.textContent = `선택된 항 적용 (${this.selectedClauses.length}개)`;
            } else {
                applyButton.textContent = '선택된 항 적용';
            }
        }
    }
    
    // 선택된 항들을 관련법령에 적용
    applySelectedClauses() {
        if (this.selectedClauses.length === 0) {
            alert('적용할 항을 선택해주세요.');
            return;
        }
        
        if (!this.lawContent) return;
        
        // 선택된 항들을 관련법령 패널에 추가 (지침, 조항, 항 정보 모두 포함)
        const selectedContent = this.selectedClauses.map(clause => `
            <div class="law-item" data-clause-id="${clause.id}">
                <button class="law-item-remove" onclick="chatbot.removeLawItem('${clause.id}')" title="이 항목 삭제">
                    <i class="fas fa-times"></i>
                </button>
                <div class="law-source">
                    <span class="law-guideline">📋 ${clause.guideline.name}</span>
                    <span class="law-article">📄 ${clause.article.name}</span>
                </div>
                <h4>${clause.title}</h4>
                <p>${clause.content}</p>
            </div>
        `).join('');
        
        // 기존 내용에 추가 (또는 교체)
        this.lawContent.innerHTML += selectedContent;
        
        // TODO: DB에 선택된 항들 저장
        console.log('선택된 항들이 적용되었습니다:', this.selectedClauses);
        
        // 패널 닫기
        this.hideLawEditPanel();
        
        // 성공 메시지 표시
        const detailMessage = this.selectedClauses.map(clause => 
            `${clause.guideline.name} ${clause.article.name} ${clause.title}`
        ).join(', ');
        this.showSuccessMessage(`${this.selectedClauses.length}개의 항이 추가되었습니다: ${detailMessage}`);
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
        if (!this.lawContent) return;
        
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

