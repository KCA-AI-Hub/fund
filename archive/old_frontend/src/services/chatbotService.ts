import { ChatbotResponse } from '../types';

// TODO: LLM API 연동
// import { OpenAI } from 'openai';
// const openai = new OpenAI({
//   apiKey: process.env.REACT_APP_OPENAI_API_KEY,
// });

// TODO: DB 연동
// import { initializeApp } from 'firebase/app';
// import { getFirestore, collection, addDoc, query, orderBy, limit } from 'firebase/firestore';

// 임시 응답 데이터 (추후 LLM API로 대체 예정)
const mockResponses: { [key: string]: string } = {
  '안녕': '안녕하세요! 민원처리 챗봇입니다. 무엇을 도와드릴까요?',
  '민원': '민원 접수에 대해 안내해드리겠습니다. 어떤 종류의 민원인지 알려주세요.',
  '신고': '신고 접수 서비스입니다. 신고 내용을 자세히 설명해주세요.',
  '문의': '문의사항이 있으시면 말씀해주세요. 최대한 빠르게 답변드리겠습니다.',
  '도움': '도움이 필요하시군요. 구체적으로 어떤 도움이 필요한지 알려주세요.',
  '접수': '민원 접수 절차를 안내해드리겠습니다. 1. 민원 내용 작성 2. 증빙서류 첨부 3. 접수 완료',
  '처리': '민원 처리 현황을 확인하시려면 접수번호를 알려주세요.',
  '기간': '일반적인 민원 처리 기간은 7-14일입니다. 긴급한 경우 별도 안내드립니다.',
  '상담': '상담 서비스를 이용하시려면 전화 또는 방문 상담을 이용해주세요.',
  '불만': '불만사항이 있으시면 구체적인 내용을 말씀해주세요. 신속히 처리하겠습니다.'
};

export class ChatbotService {
  // TODO: LLM API 연동
  // async getLLMResponse(userMessage: string): Promise<ChatbotResponse> {
  //   try {
  //     const completion = await openai.chat.completions.create({
  //       model: "gpt-3.5-turbo",
  //       messages: [
  //         {
  //           role: "system",
  //           content: "당신은 친절하고 전문적인 민원처리 상담원입니다. 민원인의 질문에 정확하고 도움이 되는 답변을 제공하세요."
  //         },
  //         {
  //           role: "user",
  //           content: userMessage
  //         }
  //       ],
  //       max_tokens: 500,
  //       temperature: 0.7,
  //     });
  //     
  //     return {
  //       message: completion.choices[0].message.content || "죄송합니다. 답변을 생성할 수 없습니다.",
  //       confidence: 0.9,
  //       category: "general"
  //     };
  //   } catch (error) {
  //     console.error('LLM API 호출 오류:', error);
  //     return this.getMockResponse(userMessage);
  //   }
  // }

  // 임시 응답 생성 (LLM API 연동 전까지 사용)
  async getMockResponse(userMessage: string): Promise<ChatbotResponse> {
    // 키워드 매칭을 통한 임시 응답
    const matchedKey = Object.keys(mockResponses).find(key => 
      userMessage.includes(key)
    );
    
    if (matchedKey) {
      return {
        message: mockResponses[matchedKey],
        confidence: 0.8,
        category: "matched"
      };
    }

    // 기본 응답
    const defaultResponses = [
      "죄송합니다. 질문을 정확히 이해하지 못했습니다. 다시 한 번 말씀해주시거나 다른 표현으로 질문해주세요.",
      "민원 관련 질문이시군요. 좀 더 구체적으로 말씀해주시면 더 정확한 답변을 드릴 수 있습니다.",
      "현재 시스템에서 해당 질문에 대한 답변을 찾을 수 없습니다. 상담원 연결을 원하시면 말씀해주세요.",
      "민원 접수나 문의사항에 대해 도움이 필요하시면 구체적으로 말씀해주세요."
    ];

    const randomResponse = defaultResponses[Math.floor(Math.random() * defaultResponses.length)];
    
    return {
      message: randomResponse,
      confidence: 0.3,
      category: "default"
    };
  }

  // TODO: DB에 대화 기록 저장
  // async saveConversation(userId: string, userMessage: string, botResponse: string): Promise<void> {
  //   try {
  //     const docRef = await addDoc(collection(db, "conversations"), {
  //       userId,
  //       userMessage,
  //       botResponse,
  //       timestamp: new Date(),
  //       category: "civil_complaint"
  //     });
  //     console.log("대화 기록이 저장되었습니다. ID: ", docRef.id);
  //   } catch (error) {
  //     console.error("대화 기록 저장 오류: ", error);
  //   }
  // }

  // TODO: DB에서 대화 기록 조회
  // async getConversationHistory(userId: string, limit: number = 10): Promise<any[]> {
  //   try {
  //     const q = query(
  //       collection(db, "conversations"),
  //       where("userId", "==", userId),
  //       orderBy("timestamp", "desc"),
  //       limit(limit)
  //     );
  //     const querySnapshot = await getDocs(q);
  //     return querySnapshot.docs.map(doc => doc.data());
  //   } catch (error) {
  //     console.error("대화 기록 조회 오류: ", error);
  //     return [];
  //   }
  // }

  // 현재는 임시 응답만 사용
  async processMessage(userMessage: string): Promise<ChatbotResponse> {
    // TODO: LLM API 연동 후 아래 주석 해제
    // return await this.getLLMResponse(userMessage);
    
    // 임시 응답 사용
    return await this.getMockResponse(userMessage);
  }
}

export default new ChatbotService();






