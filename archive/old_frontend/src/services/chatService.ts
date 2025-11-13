import { supabase, ChatSession, ChatMessage } from '../lib/supabase';

export class ChatService {
  // 새로운 채팅 세션 생성
  static async createSession(userId: string, sessionName?: string): Promise<ChatSession> {
    const { data, error } = await supabase
      .from('chat_sessions')
      .insert({
        user_id: userId,
        session_name: sessionName || '새로운 대화'
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  // 사용자의 모든 채팅 세션 조회
  static async getSessions(userId: string): Promise<ChatSession[]> {
    const { data, error } = await supabase
      .from('chat_sessions')
      .select('*')
      .eq('user_id', userId)
      .order('updated_at', { ascending: false });

    if (error) throw error;
    return data || [];
  }

  // 특정 세션의 메시지 조회
  static async getMessages(sessionId: string): Promise<ChatMessage[]> {
    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return data || [];
  }

  // 메시지 저장
  static async saveMessage(sessionId: string, content: string, sender: 'user' | 'bot'): Promise<ChatMessage> {
    const { data, error } = await supabase
      .from('chat_messages')
      .insert({
        session_id: sessionId,
        content,
        sender
      })
      .select()
      .single();

    if (error) throw error;

    // 세션 업데이트 시간 갱신
    await supabase
      .from('chat_sessions')
      .update({ updated_at: new Date().toISOString() })
      .eq('id', sessionId);

    return data;
  }

  // 세션 삭제
  static async deleteSession(sessionId: string): Promise<void> {
    const { error } = await supabase
      .from('chat_sessions')
      .delete()
      .eq('id', sessionId);

    if (error) throw error;
  }

  // 세션 이름 업데이트
  static async updateSessionName(sessionId: string, sessionName: string): Promise<void> {
    const { error } = await supabase
      .from('chat_sessions')
      .update({ session_name: sessionName })
      .eq('id', sessionId);

    if (error) throw error;
  }
}


