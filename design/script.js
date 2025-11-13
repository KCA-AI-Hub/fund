class ComplaintChatbot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.answerPanel = document.getElementById('answerPanel');
        this.answerContent = document.getElementById('answerContent');
        this.lawContent = document.getElementById('lawContent');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.chatHistory = document.getElementById('chatHistory');
        
        // 액션 버튼들
        this.editAnswerBtn = document.getElementById('editAnswerBtn');
        this.copyAnswerBtn = document.getElementById('copyAnswerBtn');
        this.editLawBtn = document.getElementById('editLawBtn');
        this.copyLawBtn = document.getElementById('copyLawBtn');
        
        this.messages = [];
        this.chatSessions = [];
        this.currentSessionId = null;
        this.isAnswerPanelActive = false;
        this.generateAnswerBtn = null; // 동적으로 생성할 버튼
        this.isEditMode = false; // 수정 모드 상태

        // 2단계 플로우를 위한 상태
        this.awaitingConfirmation = false;  // 확인 대기 중
        this.pendingQuestion = null;        // 대기 중인 질문
        this.lastBotResponse = null;        // API 응답 저장 (suggested_answer, related_laws)

        this.initializeEventListeners();
        this.createNewChat();
    }
    
    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
        
        this.newChatBtn.addEventListener('click', () => this.createNewChat());
        
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const example = btn.getAttribute('data-example');
                this.messageInput.value = example;
                this.messageInput.focus();
            });
        });
        
        // 액션 버튼 이벤트 리스너
        this.editAnswerBtn.addEventListener('click', () => this.toggleEditMode('answer'));
        this.copyAnswerBtn.addEventListener('click', () => this.copyContent('answer'));
        this.editLawBtn.addEventListener('click', () => this.toggleEditMode('law'));
        this.copyLawBtn.addEventListener('click', () => this.copyContent('law'));
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
        
        // 답변 패널 닫기 when new chat is created
        if (this.isAnswerPanelActive) {
            this.hideAnswerPanel();
        }
        
        // 컨테이너에서 answer-active 클래스 제거 (새 채팅 시 원래 레이아웃으로 복원)
        document.querySelector('.chatbot-container').classList.remove('answer-active');
        
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

        // 2단계 플로우 처리
        if (this.awaitingConfirmation) {
            // 확인 대기 중: 사용자 응답이 확인인지 체크
            const isConfirmation = this.isConfirmationResponse(message);

            if (isConfirmation) {
                // 확인됨: 실제 FAQ RAG 답변 생성
                setTimeout(() => {
                    this.generateActualAnswer(this.pendingQuestion);
                }, 500);
            } else {
                // 확인되지 않음: 상태 리셋 및 안내
                this.awaitingConfirmation = false;
                this.pendingQuestion = null;

                const resetMessage = {
                    type: 'bot',
                    content: '알겠습니다. 다시 질문해주시면 도와드리겠습니다.',
                    timestamp: new Date()
                };
                setTimeout(() => {
                    this.addMessage(resetMessage);
                }, 500);
            }
        } else {
            // 일반 플로우: 1단계 확인 질문 생성
            setTimeout(() => {
                this.confirmQuestion(message);
            }, 500);
        }
    }

    // 사용자 응답이 확인(긍정)인지 판단
    isConfirmationResponse(message) {
        const confirmWords = ['네', '맞아요', '맞습니다', '예', 'yes', 'ok', '응', '맞음', '맞', '그래'];
        const lowerMessage = message.toLowerCase().trim();

        return confirmWords.some(word => lowerMessage.includes(word));
    }

    // 1단계: 질문 확인 (API 호출)
    async confirmQuestion(question) {
        try {
            const response = await fetch('/api/chat/confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: question,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                throw new Error(`API 호출 실패: ${response.status}`);
            }

            const data = await response.json();

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
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: question,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                throw new Error(`API 호출 실패: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
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
        buttonContainer.style.cssText = 'text-align: center; padding: 20px; border-top: 1px solid #4a4b53;';
        buttonContainer.appendChild(this.generateAnswerBtn);
        
        this.chatMessages.appendChild(buttonContainer);
        
        // 이벤트 리스너 추가
        this.generateAnswerBtn.addEventListener('click', () => this.toggleAnswerPanel());
        
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
    
    toggleAnswerPanel() {
        if (this.isAnswerPanelActive) {
            this.hideAnswerPanel();
        } else {
            this.showAnswerPanel();
        }
    }
    
    showAnswerPanel() {
        this.isAnswerPanelActive = true;
        this.answerPanel.classList.add('active');
        
        // 컨테이너에 answer-active 클래스 추가 (반응형 레이아웃)
        document.querySelector('.chatbot-container').classList.add('answer-active');
        
        this.generateAnswer();
        this.updateLawContent();
        
        // 버튼 텍스트 변경
        if (this.generateAnswerBtn) {
            this.generateAnswerBtn.innerHTML = '<i class="fas fa-times"></i> 패널 닫기';
            this.generateAnswerBtn.style.background = '#565869';
        }
    }
    
    hideAnswerPanel() {
        this.isAnswerPanelActive = false;
        this.answerPanel.classList.remove('active');
        
        // 컨테이너에서 answer-active 클래스 제거 (원래 레이아웃으로 복원)
        document.querySelector('.chatbot-container').classList.remove('answer-active');
        
        // 버튼 텍스트 원복
        if (this.generateAnswerBtn) {
            this.generateAnswerBtn.innerHTML = '<i class="fas fa-magic"></i> 답변생성';
            this.generateAnswerBtn.style.background = '#8e8ea0';
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
    
    // 수정 모드 진입 (contenteditable 사용)
    enterEditMode(section) {
        this.isEditMode = true;
        this.answerPanel.classList.add('edit-mode');
        
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
        this.answerPanel.classList.remove('edit-mode');
        
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
            // contenteditable 내용을 그대로 유지 (이미 DOM에 반영됨)
            console.log('답변추천 내용 저장됨');
        } else if (section === 'law') {
            // contenteditable 내용을 그대로 유지 (이미 DOM에 반영됨)
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
                // 복사 성공 피드백
                this.showCopyFeedback(section);
            }).catch(err => {
                // 클립보드 API 실패 시 fallback
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
            this.showCopyFeedback('answer'); // 기본값으로 설정
        } catch (err) {
            console.error('복사 실패:', err);
        }
        
        document.body.removeChild(textArea);
    }
    
    generateAnswer() {
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
        // ========================================
        // 🔗 관련법령 데이터 연결 (FAQ RAG 기반)
        // ========================================

        // FAQ RAG 데이터가 있으면 사용, 없으면 fallback
        if (this.lastBotResponse && this.lastBotResponse.related_laws && this.lastBotResponse.related_laws.length > 0) {
            const laws = this.lastBotResponse.related_laws;

            this.lawContent.innerHTML = laws.map(law => `
                <div class="law-item">
                    <h4>${law.title || 'N/A'}</h4>
                    <p>${law.content || law.summary || 'N/A'}</p>
                    ${law.source ? `<p><small>출처: ${law.source}</small></p>` : ''}
                    ${law.faq_id ? `<p><small>FAQ ID: ${law.faq_id}</small></p>` : ''}
                </div>
            `).join('');
        } else {
            // Fallback: 더미 법령 데이터
            const laws = [
                {
                    title: '민원사무처리에 관한 법률',
                    content: '제1조 (목적) 이 법은 민원사무의 처리에 관한 기본사항을 정함으로써 민원사무의 신속하고 공정한 처리와 국민의 권익보호를 도모함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                },
                {
                    title: '행정절차법',
                    content: '제1조 (목적) 이 법은 행정청의 처리가 국민의 권리와 의무에 직접적인 영향을 미치는 행정절차에 대하여 공통적으로 적용될 사항을 규정함으로써 행정의 공정성과 투명성을 확보하고 국민의 권익을 보호함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                },
                {
                    title: '정보공개법',
                    content: '제1조 (목적) 이 법은 공공기관이 보유·관리하는 정보를 국민의 알권리 보장과 국정에 대한 국민의 참여와 국정에 대한 국민의 감시를 위하여 국민에게 공개하도록 함을 목적으로 한다.',
                    articles: ['제1조', '제2조', '제3조']
                }
            ];

            this.lawContent.innerHTML = laws.map(law => `
                <div class="law-item">
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
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.innerHTML = `
            <i class="fas fa-comment"></i>
            <span>${title}</span>
        `;
        this.chatHistory.appendChild(chatItem);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ComplaintChatbot();
});
