import os
import random
import json
from google import genai
from google.genai import types

# 드론 축구 세부 주제 카테고리
TOPICS = [
    "경기 규칙 및 기본 개념 (포지션, 경기장 규격, 득점 방식)",
    "드론 장비 소개 (드론 기체, 배터리, 조종기, 가드)",
    "기술 훈련법 (비행 기술, 공격/수비 전략, 훈련 드릴)",
    "드론 축구 대회 및 이벤트 (국내외 대회, 경기 분석)",
    "드론 축구 역사 및 발전 (한국 발원, 국제화)",
    "입문 가이드 (시작하는 법, 동호회 가입, 필요 예산)",
    "드론 유지보수 및 정비 (기체 수리, 배터리 관리, 모터 교체)",
    "드론 축구 동호회 활동 후기 (연습, 친선경기, 팀워크)"
]

def generate_post_content(api_key):
    """Gemini API를 사용하여 드론 축구 주제의 블로그 글을 생성합니다."""
    if not api_key or len(api_key) < 10:
        return None

    # 랜덤 주제 선택
    topic = random.choice(TOPICS)
    
    # 프롬프트 생성
    prompt = f"""
당신은 '광주 임페리얼 윙스(Imperial Wings)'라는 드론 축구 팀의 블로그 운영자입니다.
오늘 작성할 네이버 블로그 포스팅의 주제는 다음과 같습니다:
주제: {topic}

다음 조건에 맞게 네이버 블로그에 올릴 글을 작성해주세요:
1. 제목: 클릭을 유도하는 매력적인 제목 (단, 낚시성 금지)
2. 본문:
   - 친근하고 전문적인 블로그 어투(~해요, ~습니다) 사용
   - 가독성을 위해 문단을 짧게 나누고 소제목을 적절히 배치
   - 드론 축구 초보자도 이해할 수 있도록 쉽게 설명
   - 글의 마지막에는 항상 광주/전남 드론축구 팀 '임페리얼 윙스'와 함께하자는 메시지와 함께 회원 모집 안내 포함
   - 분량은 1000자 내외
3. 해시태그: 글 내용과 관련된 해시태그 7~10개 (예: #광주드론축구 #임페리얼윙스 ...)

결과는 반드시 다음 JSON 형식으로만 출력해주세요. 다른 텍스트는 포함하지 마세요.
{{
    "title": "블로그 글 제목",
    "body": "블로그 글 본문 (줄바꿈은 \\n 사용)",
    "hashtags": "#해시태그1 #해시태그2 #해시태그3"
}}
"""
    
    try:
        # Gemini API 호출
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        # JSON 결과 파싱
        result = json.loads(response.text)
        result["topic"] = topic
        return result
        
    except Exception as e:
        print(f"❌ AI 콘텐츠 생성 실패: {e}")
        return None

if __name__ == "__main__":
    # 테스트용
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("AI 글 생성 테스트 중...")
        content = generate_post_content(api_key)
        if content:
            print(f"선택된 주제: {content.get('topic')}")
            print(f"제목: {content.get('title')}")
    else:
        print("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
