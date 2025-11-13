"""
FAQ Excel 파일을 Dify Knowledge에 업로드하기 좋은 Markdown 형식으로 변환

사용법:
    python scripts/convert_faq_for_dify.py
"""

import pandas as pd
import os

def convert_faq_to_markdown(input_file, output_dir):
    """
    FAQ Excel을 개별 Markdown 파일로 변환

    각 FAQ를 별도 파일로 저장하여 Dify가 개별 chunk로 인식하도록 함
    """
    # FAQ 데이터 로드
    df = pd.read_excel(input_file)

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    print(f"총 {len(df)}개의 FAQ를 변환합니다...\n")

    # 각 FAQ를 개별 파일로 저장
    for idx, row in df.iterrows():
        faq_id = row['faq_id']
        question = row['question']
        answer = row['answer_text']
        tags = row['tag']
        policy_anchor = row['policy_anchor']

        # Markdown 형식으로 작성 (구조화)
        markdown_content = f"""---
faq_id: {faq_id}
tags: {tags}
policy_anchor: {policy_anchor}
---

# {question}

## 답변

{answer}

## 관련 법령

{policy_anchor}

## 태그

{tags}
"""

        # 파일명 생성 (안전한 파일명)
        safe_filename = faq_id.replace('/', '-').replace('\\', '-')
        output_file = os.path.join(output_dir, f"{safe_filename}.md")

        # 파일 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        if (idx + 1) % 10 == 0:
            print(f"진행: {idx + 1}/{len(df)} 완료")

    print(f"\n✅ 변환 완료! {len(df)}개 파일이 생성되었습니다.")
    print(f"📁 위치: {output_dir}")
    return len(df)


def convert_faq_to_single_file(input_file, output_file):
    """
    FAQ Excel을 하나의 큰 Markdown 파일로 변환

    Dify가 자동으로 chunking하도록 함
    """
    df = pd.read_excel(input_file)

    print(f"총 {len(df)}개의 FAQ를 하나의 파일로 변환합니다...\n")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ICT 기금사업 FAQ (100문100답)\n\n")
        f.write("---\n\n")

        for idx, row in df.iterrows():
            faq_id = row['faq_id']
            question = row['question']
            answer = row['answer_text']
            tags = row['tag']
            policy_anchor = row['policy_anchor']

            # 각 FAQ를 섹션으로 구분
            f.write(f"## FAQ {idx + 1}: {question}\n\n")
            f.write(f"**FAQ ID**: {faq_id}  \n")
            f.write(f"**태그**: {tags}  \n")
            f.write(f"**관련 법령**: {policy_anchor}  \n\n")
            f.write(f"### 답변\n\n")
            f.write(f"{answer}\n\n")
            f.write("---\n\n")

            if (idx + 1) % 10 == 0:
                print(f"진행: {idx + 1}/{len(df)} 완료")

    print(f"\n✅ 변환 완료!")
    print(f"📁 위치: {output_file}")
    return len(df)


def convert_faq_to_jsonl(input_file, output_file):
    """
    FAQ Excel을 JSONL 형식으로 변환

    Dify가 구조화된 데이터로 인식하도록 함
    """
    import json

    df = pd.read_excel(input_file)

    print(f"총 {len(df)}개의 FAQ를 JSONL로 변환합니다...\n")

    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            faq_obj = {
                "faq_id": row['faq_id'],
                "question": row['question'],
                "answer": row['answer_text'],
                "tags": row['tag'].split(','),
                "policy_anchor": row['policy_anchor'],
                "text": f"질문: {row['question']}\n\n답변: {row['answer_text']}\n\n관련법령: {row['policy_anchor']}\n\n태그: {row['tag']}"
            }

            f.write(json.dumps(faq_obj, ensure_ascii=False) + '\n')

            if (idx + 1) % 10 == 0:
                print(f"진행: {idx + 1}/{len(df)} 완료")

    print(f"\n✅ 변환 완료!")
    print(f"📁 위치: {output_file}")
    return len(df)


if __name__ == "__main__":
    input_file = "data/faq_topic.xlsx"

    print("=" * 60)
    print("FAQ 변환 스크립트")
    print("=" * 60)
    print()

    # 방법 선택
    print("변환 방식을 선택하세요:")
    print("1. 개별 Markdown 파일 (추천 - Dify chunking 최적)")
    print("2. 단일 Markdown 파일 (간단)")
    print("3. JSONL 형식 (구조화)")
    print()

    choice = input("선택 (1-3): ").strip()

    if choice == "1":
        output_dir = "data/faq_markdown"
        count = convert_faq_to_markdown(input_file, output_dir)
        print(f"\n다음 단계: {output_dir} 폴더를 Dify에 업로드하세요!")

    elif choice == "2":
        output_file = "data/faq_all.md"
        count = convert_faq_to_single_file(input_file, output_file)
        print(f"\n다음 단계: {output_file} 파일을 Dify에 업로드하세요!")

    elif choice == "3":
        output_file = "data/faq_all.jsonl"
        count = convert_faq_to_jsonl(input_file, output_file)
        print(f"\n다음 단계: {output_file} 파일을 Dify에 업로드하세요!")

    else:
        print("잘못된 선택입니다.")
        exit(1)

    print()
    print("=" * 60)
    print("Dify 업로드 가이드:")
    print("=" * 60)
    print("1. Dify 웹 인터페이스 접속")
    print("2. Knowledge → 기존 Dataset 선택")
    print("3. 'Add Document' 클릭")
    print("4. 변환된 파일/폴더 업로드")
    print("5. Chunking 설정:")
    print("   - Chunk Size: 500-800 (권장: 600)")
    print("   - Overlap: 50-100 (권장: 80)")
    print("6. 'Save and Process' 클릭")
    print("=" * 60)
