// Session ID 관리
let sessionId = localStorage.getItem('sessionId') || null;

// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');
    const chatHistory = document.getElementById('chatHistory');
    const newChatBtn = document.getElementById('newChatBtn');
    const answerContent = document.getElementById('answerContent');
    const lawContent = document.getElementById('lawContent');
    const rightPanels = document.getElementById('rightPanels');
    const closePanelBtn = document.getElementById('closePanelBtn');
    
    // 메시지 입력 자동 크기 조절
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
        
        // 엔터키로 전송
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // 예시 버튼 클릭 처리
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const example = this.getAttribute('data-example');
            if (messageInput) {
                messageInput.value = example;
                messageInput.focus();
                messageInput.dispatchEvent(new Event('input'));
            }
        });
    });
    
    // 메시지 전송 함수
    async function sendMessage() {
        if (!messageInput) return;
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // 버튼 비활성화
        if (sendButton) {
            sendButton.disabled = true;
        }
        
        // 사용자 메시지 추가
        addMessage(message, 'user');
        
        // 입력창 초기화
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // 타이핑 인디케이터 표시
        showTypingIndicator();
        
        try {
            // API 호출
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 세션 ID 저장
                if (data.session_id) {
                    sessionId = data.session_id;
                    localStorage.setItem('sessionId', sessionId);
                }
                
                // 타이핑 인디케이터 제거
                hideTypingIndicator();
                
                // AI 응답 추가 (타이핑 효과와 함께)
                addMessage(data.message, 'assistant', true);
                
                // 오른쪽 패널 표시 및 업데이트
                showRightPanels();
                
                if (data.suggested_answer) {
                    updateAnswerPanel(data.suggested_answer);
                }
                
                if (data.related_laws) {
                    updateLawPanel(data.related_laws);
                }
            } else {
                hideTypingIndicator();
                addMessage('죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.', 'assistant');
            }
        } catch (error) {
            console.error('Error:', error);
            hideTypingIndicator();
            addMessage('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'assistant');
        } finally {
            if (sendButton) {
                sendButton.disabled = false;
            }
        }
    }
    
    // Markdown 렌더링 설정
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            if (Prism.languages[lang]) {
                return Prism.highlight(code, Prism.languages[lang], lang);
            }
            return code;
        }
    });
    
    // 메시지 추가 함수 (타이핑 효과 포함)
    function addMessage(text, sender, useTypingEffect = false) {
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message flex gap-3 animate-slide-in';
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="flex-1 flex justify-end">
                    <div class="bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-2xl rounded-tr-none p-4 shadow-md max-w-[80%]">
                        <p>${escapeHtml(text)}</p>
                    </div>
                </div>
                <div class="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 flex-shrink-0">
                    <i class="fas fa-user"></i>
                </div>
            `;
            chatMessages.appendChild(messageDiv);
        } else {
            // Assistant 메시지는 Markdown 렌더링
            const avatarHtml = `
                <div class="w-10 h-10 rounded-full gradient-secondary flex items-center justify-center text-white flex-shrink-0">
                    <i class="fas fa-robot"></i>
                </div>
            `;
            
            const messageContent = `
                <div class="flex-1">
                    <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-md max-w-[80%]">
                        <div class="text-gray-800 markdown-content"></div>
                    </div>
                </div>
            `;
            
            messageDiv.innerHTML = avatarHtml + messageContent;
            chatMessages.appendChild(messageDiv);
            
            const contentDiv = messageDiv.querySelector('.markdown-content');
            
            if (useTypingEffect) {
                // 타이핑 효과로 렌더링
                typewriterEffect(text, contentDiv);
            } else {
                // 즉시 렌더링
                renderMarkdown(text, contentDiv);
            }
        }
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Markdown 렌더링 함수
    function renderMarkdown(text, element) {
        const htmlContent = marked.parse(text);
        element.innerHTML = htmlContent;
        
        // 코드 하이라이팅 적용
        element.querySelectorAll('pre code').forEach((block) => {
            Prism.highlightElement(block);
        });
        
        // 링크를 새 탭에서 열도록 설정
        element.querySelectorAll('a').forEach((link) => {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
        });
    }
    
    // 타이핑 효과 함수
    function typewriterEffect(text, element, speed = 10) {
        let index = 0;
        let currentText = '';
        const words = text.split(' ');
        let wordIndex = 0;
        
        // 빠른 타이핑 효과 (단어 단위)
        const typeInterval = setInterval(() => {
            if (wordIndex < words.length) {
                currentText += (wordIndex > 0 ? ' ' : '') + words[wordIndex];
                renderMarkdown(currentText, element);
                wordIndex++;
                
                // 스크롤 유지
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                clearInterval(typeInterval);
                // 최종 렌더링
                renderMarkdown(text, element);
            }
        }, speed);
    }
    
    // HTML 이스케이프 함수
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 타이핑 인디케이터 표시
    function showTypingIndicator() {
        if (!chatMessages) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message flex gap-3';
        typingDiv.innerHTML = `
            <div class="w-10 h-10 rounded-full gradient-secondary flex items-center justify-center text-white flex-shrink-0">
                <i class="fas fa-robot"></i>
            </div>
            <div class="flex-1">
                <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-md w-20">
                    <div class="flex gap-1">
                        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 타이핑 인디케이터 제거
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // 오른쪽 패널 표시
    function showRightPanels() {
        if (rightPanels) {
            rightPanels.classList.remove('translate-x-full');
            rightPanels.classList.add('translate-x-0');
        }
    }
    
    // 오른쪽 패널 숨기기
    function hideRightPanels() {
        if (rightPanels) {
            rightPanels.classList.remove('translate-x-0');
            rightPanels.classList.add('translate-x-full');
        }
    }
    
    // 답변 패널 업데이트 (Markdown 렌더링)
    function updateAnswerPanel(answer) {
        if (!answerContent) return;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'text-white/90 markdown-content';
        answerContent.innerHTML = '';
        answerContent.appendChild(contentDiv);
        
        // Markdown 렌더링 (패널용 스타일 조정)
        const htmlContent = marked.parse(answer);
        contentDiv.innerHTML = htmlContent;
        
        // 패널에서의 스타일 조정
        contentDiv.querySelectorAll('pre').forEach((block) => {
            block.style.background = 'rgba(0, 0, 0, 0.3)';
        });
        
        contentDiv.querySelectorAll('code:not([class*="language-"])').forEach((code) => {
            code.style.background = 'rgba(255, 255, 255, 0.2)';
            code.style.color = '#fff';
        });
        
        contentDiv.querySelectorAll('blockquote').forEach((quote) => {
            quote.style.borderLeftColor = '#fbbf24';
            quote.style.background = 'rgba(251, 191, 36, 0.1)';
            quote.style.color = 'rgba(255, 255, 255, 0.9)';
        });
        
        // 코드 하이라이팅
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            Prism.highlightElement(block);
        });
    }
    
    // 법령 패널 업데이트
    function updateLawPanel(laws) {
        if (!lawContent) return;
        
        lawContent.innerHTML = laws.map(law => `
            <div class="bg-white/10 rounded-lg p-3">
                <h4 class="font-semibold mb-2">${escapeHtml(law.title)}</h4>
                <p class="text-sm text-white/80">${escapeHtml(law.content)}</p>
            </div>
        `).join('');
    }
    
    // 채팅 히스토리에 아이템 추가
    function addChatHistoryItem(title) {
        if (!chatHistory) return;
        
        const historyItem = document.createElement('div');
        historyItem.className = 'chat-item px-4 py-3 bg-white/10 rounded-xl text-white cursor-pointer hover:bg-white/20 hover:translate-x-1 transition-all duration-300 flex items-center gap-2';
        historyItem.innerHTML = `
            <i class="fas fa-comment text-yellow-400"></i>
            <span class="text-sm truncate">${escapeHtml(title)}</span>
        `;
        
        historyItem.addEventListener('click', function() {
            // 채팅 히스토리 클릭 시 해당 채팅 로드 (추후 구현)
            console.log('Load chat:', title);
        });
        
        chatHistory.appendChild(historyItem);
    }
    
    // 전송 버튼 클릭
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    // 새 채팅 버튼
    if (newChatBtn) {
        newChatBtn.addEventListener('click', async function() {
            // 세션 초기화
            sessionId = null;
            localStorage.removeItem('sessionId');
            
            // 메시지 초기화
            if (chatMessages) {
                chatMessages.innerHTML = `
                    <div class="message flex gap-3 animate-slide-in">
                        <div class="w-10 h-10 rounded-full gradient-secondary flex items-center justify-center text-white flex-shrink-0">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="flex-1">
                            <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-md max-w-[80%]">
                                <div class="text-gray-800 markdown-content">안녕하세요! 민원처리 도우미입니다. 어떤 도움이 필요하신가요?</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // 오른쪽 패널 숨기기
            hideRightPanels();
            
            // 새 세션 생성
            try {
                const response = await fetch('/api/new-session', {
                    method: 'POST'
                });
                const data = await response.json();
                sessionId = data.session_id;
                localStorage.setItem('sessionId', sessionId);
                
                // 채팅 히스토리에 추가
                const chatCount = chatHistory ? chatHistory.children.length + 1 : 1;
                addChatHistoryItem(`새 채팅 ${chatCount}`);
            } catch (error) {
                console.error('Error creating new session:', error);
            }
        });
    }
    
    // 패널 닫기 버튼
    if (closePanelBtn) {
        closePanelBtn.addEventListener('click', hideRightPanels);
    }
    
    // 복사 버튼 기능
    document.querySelectorAll('button').forEach(btn => {
        if (btn.innerHTML.includes('복사')) {
            btn.addEventListener('click', function() {
                const panel = this.closest('.glass-dark');
                const contentDiv = panel.querySelector('.overflow-y-auto');
                if (contentDiv) {
                    const text = contentDiv.innerText;
                    navigator.clipboard.writeText(text).then(() => {
                        const originalHTML = this.innerHTML;
                        this.innerHTML = '<i class="fas fa-check"></i> <span>복사됨!</span>';
                        setTimeout(() => {
                            this.innerHTML = originalHTML;
                        }, 2000);
                    });
                }
            });
        }
    });
    
    // 초기 웰컴 메시지
    if (chatMessages && chatMessages.children.length === 0) {
        chatMessages.innerHTML = `
            <div class="message flex gap-3 animate-slide-in">
                <div class="w-10 h-10 rounded-full gradient-secondary flex items-center justify-center text-white flex-shrink-0">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="flex-1">
                    <div class="bg-white rounded-2xl rounded-tl-none p-4 shadow-md max-w-[80%]">
                        <div class="text-gray-800 markdown-content">안녕하세요! 민원처리 도우미입니다. 어떤 도움이 필요하신가요?</div>
                    </div>
                </div>
            </div>
        `;
    }
});