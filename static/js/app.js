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
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const mainLayout = document.getElementById('mainLayout');
    
    // 사이드바 상태 복원
    const sidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
    const toggleIcon = sidebarToggle ? sidebarToggle.querySelector('i') : null;
    
    if (sidebarState && sidebar && mainLayout) {
        sidebar.classList.add('hidden');
        mainLayout.classList.remove('grid-cols-[280px_1fr]');
        mainLayout.classList.add('grid-cols-1');
        if (toggleIcon) {
            toggleIcon.classList.remove('fa-angle-double-left');
            toggleIcon.classList.add('fa-angle-double-right');
        }
        if (sidebarToggle) {
            sidebarToggle.style.left = '-1.25rem';  // -left-5 in rem
        }
    } else {
        // 기본 상태 (사이드바 열림)
        if (toggleIcon) {
            toggleIcon.classList.remove('fa-angle-double-right');
            toggleIcon.classList.add('fa-angle-double-left');
        }
    }
    
    // 사이드바 토글 기능
    if (sidebarToggle && sidebar && mainLayout) {
        sidebarToggle.addEventListener('click', function() {
            const isCollapsed = sidebar.classList.toggle('hidden');
            const icon = this.querySelector('i');
            
            if (isCollapsed) {
                // 사이드바 숨김
                mainLayout.classList.remove('grid-cols-[280px_1fr]');
                mainLayout.classList.add('grid-cols-1');
                if (icon) {
                    icon.classList.remove('fa-angle-double-left');
                    icon.classList.add('fa-angle-double-right');
                }
                this.style.left = '-1.25rem';  // -left-5 in rem
                localStorage.setItem('sidebarCollapsed', 'true');
            } else {
                // 사이드바 표시
                mainLayout.classList.remove('grid-cols-1');
                mainLayout.classList.add('grid-cols-[280px_1fr]');
                if (icon) {
                    icon.classList.remove('fa-angle-double-right');
                    icon.classList.add('fa-angle-double-left');
                }
                this.style.left = '-1.25rem';  // Keep same position
                localStorage.setItem('sidebarCollapsed', 'false');
            }
        });
    }
    
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
                    <div class="bg-primary text-primary-foreground rounded-2xl rounded-tr-none p-4 shadow-sm max-w-[80%] border border-primary/20">
                        <p>${escapeHtml(text)}</p>
                    </div>
                </div>
                <div class="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground flex-shrink-0 shadow-sm">
                    <i class="fas fa-user"></i>
                </div>
            `;
            chatMessages.appendChild(messageDiv);
        } else {
            // Assistant 메시지는 Markdown 렌더링
            const avatarHtml = `
                <div class="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground flex-shrink-0 shadow-sm">
                    <i class="fas fa-robot"></i>
                </div>
            `;
            
            const messageContent = `
                <div class="flex-1">
                    <div class="bg-card border border-border rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]">
                        <div class="text-card-foreground markdown-content"></div>
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
            
            // 채팅 영역 크기 조정
            const app = document.getElementById('app');
            if (app && !lawEditPanel.classList.contains('translate-x-0')) {
                app.style.width = 'calc(100% - 500px)';
                app.style.marginRight = '460px';
                app.style.marginLeft = '40px';
            }
        }
    }
    
    // 오른쪽 패널 숨기기
    function hideRightPanels() {
        if (rightPanels) {
            rightPanels.classList.remove('translate-x-0');
            rightPanels.classList.add('translate-x-full');
            
            // 채팅 영역 크기 복원
            const app = document.getElementById('app');
            if (app && !lawEditPanel.classList.contains('translate-x-0')) {
                app.style.width = 'calc(100% - 80px)';
                app.style.marginRight = 'auto';
                app.style.marginLeft = 'auto';
            }
        }
    }
    
    // 답변 패널 업데이트 (Markdown 렌더링)
    function updateAnswerPanel(answer) {
        if (!answerContent) return;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'text-card-foreground markdown-content';
        answerContent.innerHTML = '';
        answerContent.appendChild(contentDiv);
        
        // Markdown 렌더링
        const htmlContent = marked.parse(answer);
        contentDiv.innerHTML = htmlContent;
        
        // 패널에서의 스타일 조정 - 디자인 시스템 클래스 적용
        contentDiv.querySelectorAll('pre').forEach((block) => {
            block.className = 'bg-muted/50 rounded-lg p-3 overflow-x-auto';
        });
        
        contentDiv.querySelectorAll('code:not([class*="language-"])').forEach((code) => {
            code.className = 'bg-muted/30 text-accent-foreground px-1 py-0.5 rounded';
        });
        
        contentDiv.querySelectorAll('blockquote').forEach((quote) => {
            quote.className = 'border-l-4 border-accent bg-accent/10 text-card-foreground pl-4 py-2 my-2';
        });
        
        contentDiv.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((heading) => {
            heading.className = 'text-card-foreground font-bold mb-2 mt-3';
        });
        
        contentDiv.querySelectorAll('p').forEach((paragraph) => {
            paragraph.className = 'text-card-foreground mb-2';
        });
        
        contentDiv.querySelectorAll('ul, ol').forEach((list) => {
            list.className = 'text-card-foreground ml-4 mb-2';
        });
        
        contentDiv.querySelectorAll('a').forEach((link) => {
            link.className = 'text-accent hover:text-accent-foreground underline';
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
            <div class="bg-muted/50 rounded-lg p-4 border border-muted hover:bg-muted/70 transition-colors">
                <h4 class="font-semibold mb-2 text-card-foreground">${escapeHtml(law.title)}</h4>
                <p class="text-sm text-muted-foreground leading-relaxed">${escapeHtml(law.content)}</p>
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
                        <div class="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground flex-shrink-0 shadow-sm">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="flex-1">
                            <div class="bg-card border border-border rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]">
                                <div class="text-card-foreground markdown-content">안녕하세요! 민원처리 도우미입니다. 어떤 도움이 필요하신가요?</div>
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
    
    // 답변 복사 버튼 기능
    const copyAnswerBtn = document.getElementById('copyAnswerBtn');
    if (copyAnswerBtn) {
        copyAnswerBtn.addEventListener('click', function() {
            const contentDiv = document.getElementById('answerContent');
            if (contentDiv) {
                const text = contentDiv.innerText;
                navigator.clipboard.writeText(text).then(() => {
                    const originalHTML = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> <span>복사됨!</span>';
                    setTimeout(() => {
                        this.innerHTML = originalHTML;
                    }, 2000);
                }).catch(err => {
                    console.error('답변 복사 실패:', err);
                });
            }
        });
    }
    
    // 법령 복사 버튼 기능
    const copyLawBtn = document.getElementById('copyLawBtn');
    if (copyLawBtn) {
        copyLawBtn.addEventListener('click', function() {
            const contentDiv = document.getElementById('lawContent');
            if (contentDiv) {
                const text = contentDiv.innerText;
                navigator.clipboard.writeText(text).then(() => {
                    const originalHTML = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> <span>복사됨!</span>';
                    setTimeout(() => {
                        this.innerHTML = originalHTML;
                    }, 2000);
                }).catch(err => {
                    console.error('법령 복사 실패:', err);
                });
            }
        });
    }
    
    // 초기 웰컴 메시지
    if (chatMessages && chatMessages.children.length === 0) {
        chatMessages.innerHTML = `
            <div class="message flex gap-3 animate-slide-in">
                <div class="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground flex-shrink-0 shadow-sm">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="flex-1">
                    <div class="bg-card border border-border rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]">
                        <div class="text-card-foreground markdown-content">안녕하세요! 민원처리 도우미입니다. 어떤 도움이 필요하신가요?</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 법령 편집 패널 관련 기능
    const lawEditPanel = document.getElementById('lawEditPanel');
    const guidelineStep = document.getElementById('guidelineStep');
    const articleStep = document.getElementById('articleStep');
    const clauseStep = document.getElementById('clauseStep');
    
    // 법령 패널의 수정 버튼
    const editLawBtn = document.getElementById('editLawBtn');
    if (editLawBtn) {
        editLawBtn.addEventListener('click', function() {
            showLawEditPanel();
        });
    }
    
    // 법령 편집 패널 표시
    function showLawEditPanel() {
        if (lawEditPanel) {
            // 패널 표시
            lawEditPanel.style.transform = 'translateX(0)';
            // 첫 번째 단계 표시
            showStep('guideline');
            
            // 메인 앱 크기 조정 (양쪽 패널 공간 확보)
            const app = document.getElementById('app');
            
            if (app) {
                // 앱 영역을 축소 (왼쪽 정렬)
                app.style.width = 'calc(100% - 900px)'; // 420px + 360px + 120px gap
                app.style.marginLeft = '40px';
                app.style.marginRight = '860px';
                app.style.maxWidth = 'none';
                app.style.transition = 'all 0.3s ease';
            }
        }
    }
    
    // 법령 편집 패널 숨기기
    function hideLawEditPanel() {
        if (lawEditPanel) {
            // 패널 숨기기
            lawEditPanel.style.transform = 'translateX(calc(100% + 460px))';
            
            // 메인 앱 영역 크기 복원 (오른쪽 패널만 있을 때)
            const app = document.getElementById('app');
            if (app) {
                if (rightPanels && rightPanels.classList.contains('translate-x-0')) {
                    // 오른쪽 패널만 열려있는 경우
                    app.style.width = 'calc(100% - 500px)';
                    app.style.marginRight = '460px';
                    app.style.marginLeft = '40px';
                } else {
                    // 모든 패널이 닫힌 경우
                    app.style.width = 'calc(100% - 80px)';
                    app.style.marginRight = 'auto';
                    app.style.marginLeft = 'auto';
                    app.style.maxWidth = '1400px';
                }
            }
        }
    }
    
    // 단계 전환 함수
    function showStep(step) {
        // 모든 단계 숨기기
        if (guidelineStep) guidelineStep.classList.add('hidden');
        if (articleStep) articleStep.classList.add('hidden');
        if (clauseStep) clauseStep.classList.add('hidden');
        
        // 선택된 단계 표시
        switch(step) {
            case 'guideline':
                if (guidelineStep) {
                    guidelineStep.classList.remove('hidden');
                    guidelineStep.classList.add('flex');
                }
                break;
            case 'article':
                if (articleStep) {
                    articleStep.classList.remove('hidden');
                    articleStep.classList.add('flex');
                }
                break;
            case 'clause':
                if (clauseStep) {
                    clauseStep.classList.remove('hidden');
                    clauseStep.classList.add('flex');
                }
                break;
        }
    }
    
    // 지침 선택 (1단계)
    const guidelineList = document.getElementById('guidelineList');
    if (guidelineList) {
        guidelineList.addEventListener('click', function(e) {
            const button = e.target.closest('button');
            if (button) {
                const guidelineTitle = button.querySelector('.font-semibold').textContent;
                const selectedTitle = document.getElementById('selectedGuidelineTitle');
                if (selectedTitle) {
                    selectedTitle.textContent = guidelineTitle;
                }
                showStep('article');
                loadArticles(guidelineTitle);
            }
        });
    }
    
    // 조항 로드 함수 (예시)
    function loadArticles(guideline) {
        const articleList = document.getElementById('articleList');
        if (articleList) {
            // 예시 데이터
            const articles = [
                '제1조 (목적)',
                '제2조 (정의)',
                '제3조 (적용범위)',
                '제4조 (처리절차)',
                '제5조 (처리기한)'
            ];
            
            articleList.innerHTML = articles.map(article => `
                <button class="w-full p-3 bg-muted hover:bg-accent hover:text-accent-foreground rounded-lg text-left transition-colors">
                    <div class="font-semibold">${article}</div>
                </button>
            `).join('');
        }
    }
    
    // 조항 선택 (2단계)
    const articleList = document.getElementById('articleList');
    if (articleList) {
        articleList.addEventListener('click', function(e) {
            const button = e.target.closest('button');
            if (button) {
                const articleTitle = button.querySelector('.font-semibold').textContent;
                const selectedTitle = document.getElementById('selectedArticleTitle');
                if (selectedTitle) {
                    selectedTitle.textContent = articleTitle;
                }
                showStep('clause');
                loadClauses(articleTitle);
            }
        });
    }
    
    // 항 로드 함수 (예시)
    function loadClauses(article) {
        const clauseList = document.getElementById('clauseList');
        if (clauseList) {
            // 예시 데이터
            const clauses = [
                '① 민원사무는 신속하고 공정하게 처리되어야 한다.',
                '② 민원인의 권익을 보호하고 편의를 도모하여야 한다.',
                '③ 처리과정은 투명하게 공개되어야 한다.',
                '④ 관련 법령을 준수하여 처리하여야 한다.'
            ];
            
            clauseList.innerHTML = clauses.map((clause, index) => `
                <label class="flex items-start p-3 bg-muted hover:bg-accent/20 rounded-lg cursor-pointer transition-colors">
                    <input type="checkbox" class="mt-1 mr-3 w-4 h-4 text-accent border-2 border-muted-foreground rounded focus:ring-accent focus:ring-2" value="${index}">
                    <span class="text-sm text-card-foreground">${clause}</span>
                </label>
            `).join('');
        }
    }
    
    // 선택된 항 적용
    const applySelectedBtn = document.getElementById('applySelected');
    if (applySelectedBtn) {
        applySelectedBtn.addEventListener('click', function() {
            const selectedClauses = document.querySelectorAll('#clauseList input[type="checkbox"]:checked');
            const selectedTexts = Array.from(selectedClauses).map(cb => 
                cb.parentElement.querySelector('span').textContent
            );
            
            if (selectedTexts.length > 0) {
                // 선택된 항목을 법령 패널에 추가
                updateLawPanel([{
                    title: document.getElementById('selectedGuidelineTitle').textContent,
                    content: selectedTexts.join('\n')
                }]);
                
                // 패널 닫기
                hideLawEditPanel();
                
                // 알림 표시 (옵션)
                console.log('선택된 항목이 적용되었습니다:', selectedTexts);
            }
        });
    }
    
    // 뒤로가기 버튼들
    const backToGuidelineBtn = document.getElementById('backToGuideline');
    if (backToGuidelineBtn) {
        backToGuidelineBtn.addEventListener('click', () => showStep('guideline'));
    }
    
    const backToArticleBtn = document.getElementById('backToArticle');
    if (backToArticleBtn) {
        backToArticleBtn.addEventListener('click', () => showStep('article'));
    }
    
    // 닫기 버튼들
    const closeButtons = [
        document.getElementById('closeFromGuideline'),
        document.getElementById('closeFromArticle'),
        document.getElementById('closeFromClause')
    ];
    
    closeButtons.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', hideLawEditPanel);
        }
    });
});