import React, { useState, useEffect } from 'react';
import { ChatSession } from '../lib/supabase';
import { ChatService } from '../services/chatService';
import './ChatSidebar.css';

interface ChatSidebarProps {
  userId: string;
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  userId,
  currentSessionId,
  onSessionSelect,
  onNewSession
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, [userId]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await ChatService.getSessions(userId);
      setSessions(data);
    } catch (error) {
      console.error('세션 로드 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('이 대화를 삭제하시겠습니까?')) {
      try {
        await ChatService.deleteSession(sessionId);
        await loadSessions();
        if (currentSessionId === sessionId) {
          onNewSession();
        }
      } catch (error) {
        console.error('세션 삭제 오류:', error);
      }
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
      return '어제';
    } else if (diffDays < 7) {
      return `${diffDays}일 전`;
    } else {
      return date.toLocaleDateString('ko-KR');
    }
  };

  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <h2>대화 목록</h2>
        <button className="new-chat-btn" onClick={onNewSession}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 5V19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          새 대화
        </button>
      </div>

      <div className="sessions-list">
        {loading ? (
          <div className="loading">로딩 중...</div>
        ) : sessions.length === 0 ? (
          <div className="empty-state">
            <p>아직 대화가 없습니다</p>
            <button onClick={onNewSession}>새 대화 시작하기</button>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`session-item ${currentSessionId === session.id ? 'active' : ''}`}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="session-info">
                <h3>{session.session_name}</h3>
                <p>{formatDate(session.updated_at)}</p>
              </div>
              <button
                className="delete-btn"
                onClick={(e) => handleDeleteSession(session.id, e)}
                title="삭제"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 6H5H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;


