"""
인스타그램 자동 포스팅 모듈
Manus Instagram MCP를 통해 @giw2.025 계정에 포스팅합니다.
"""

import os
import random
import subprocess
import json
import glob
from datetime import datetime


# 포스팅별 인스타그램 캡션 데이터
INSTA_CAPTIONS = {
    "16": """드론축구 멤버 모집 중! 🚁✨

광주·전남에서 드론을 좋아하시는 분들 모두 환영합니다!
조종 경험이 없어도, 장비가 없어도 괜찮아요.
중요한 건 함께 날고 싶은 마음 하나면 충분합니다 😊

📍 매주 금요일 오후 2시 | 광주드론공원
💬 오픈채팅으로 문의해 주세요!

#드론축구 #광주드론축구 #전남드론축구 #광주동호회 #드론동호회
#광주임페리얼윙스 #ImperialWings #드론취미 #광주취미 #드론스포츠""",

    "17": """드론축구 처음인데 민폐 아닐까요? 🤔

절대 아닙니다! 초보자분들이 가장 많이 하시는 질문 TOP 10을 정리했어요.
'장비 없어도 되나요?', '자격증 필요한가요?' 등
모든 궁금증을 블로그에서 확인해 보세요 👆

#드론축구초보 #드론입문 #광주드론체험 #드론FAQ
#광주임페리얼윙스 #ImperialWings #드론축구동호회""",

    "18": """장비부터 사면 후회합니다 ⚠️

드론축구 입문 시 가장 흔한 실수!
현명한 3단계 입문법을 블로그에서 공개했어요.
체험 → 조종기 이해 → 기체 구매 순서로 가야 합니다 💡

#드론축구장비 #드론입문 #드론조종기 #광주드론축구
#광주임페리얼윙스 #ImperialWings #드론취미""",

    "19": """퇴근 후 짜릿한 취미를 찾고 계신가요? ⚡

광주 직장인·대학생 여러분께 드론축구를 강력 추천합니다!
운동과 기술이 결합된 스포츠, 팀원들과의 끈끈한 유대감 🤝
이번 주말, 직접 체험해 보세요!

#광주직장인취미 #광주대학생취미 #광주이색취미 #드론축구
#광주임페리얼윙스 #ImperialWings #광주동호회""",

    "20": """OPEN DAY 90분 체험 🎉

드론축구가 궁금하다면 몸만 오세요!
이륙부터 링 통과, 미니게임까지 90분 안에 다 경험할 수 있어요.
가입 전 부담 없이 먼저 체험해 보세요 😊

📍 매주 금요일 오후 2시 | 광주드론공원
💬 오픈채팅 문의 환영!

#광주드론체험 #드론축구체험 #광주원데이클래스
#광주임페리얼윙스 #ImperialWings #드론체험""",

    "21": """첫 방문 전 이것만 확인하세요! ✅

복장, 준비물, 동호회 예절까지
드론축구 첫 방문 완벽 체크리스트를 공개합니다.
편한 복장 + 물 + 배우려는 열정만 있으면 OK! 🙌

#드론축구준비물 #드론동호회 #광주드론축구
#광주임페리얼윙스 #ImperialWings #드론체험준비""",

    "22": """초보 4주 훈련 로드맵 공개! 🗺️

호버링 → 직선 이동 → 링 통과 → 첫 미니게임
단계별로 차근차근 익히면 누구나 팀 훈련에 참여할 수 있어요!
서두르지 말고 기본기부터 탄탄하게 💪

#드론축구훈련 #드론호버링 #드론조종연습 #드론축구초보
#광주임페리얼윙스 #ImperialWings #드론연습""",

    "23": """조종 못해도 팀의 핵심 멤버가 될 수 있어요! 🌟

파일럿, 정비, 배터리 관리, 촬영, 기록, 운영, 멘토...
드론축구팀에는 정말 다양한 역할이 있습니다.
여러분의 능력이 팀에 꼭 필요한 조각일 수 있어요 🧩

#드론축구팀 #드론동호회운영 #드론정비 #드론영상
#광주임페리얼윙스 #ImperialWings #광주드론동호회""",

    "24": """좋은 팀은 실력이 아니라 '이것'으로 만들어집니다 💙

임페리얼 윙스가 오래가는 팀이 되기 위해 지키는 8가지 원칙!
안전, 배려, 공유, 존중... 팀 문화가 팀을 지속시킵니다.
블로그에서 전문 확인해 보세요 👆

#드론축구팀워크 #동호회문화 #드론동호회 #팀워크
#광주임페리얼윙스 #ImperialWings #광주드론동호회""",

    "25": """정기연습 2시간, 실제로 어떻게 진행될까요? ⏱️

장비 점검 → 개인 기본기 → 포지션 훈련 → 세트 경기 → 피드백
체계적인 훈련 루틴이 팀의 실력을 안정시킵니다!
자세한 내용은 블로그에서 확인하세요 📖

#드론축구연습 #정기연습 #드론축구훈련 #팀훈련
#광주임페리얼윙스 #ImperialWings #광주드론축구""",

    "26": """실력 빨리 느는 파일럿의 비밀? 📓

바로 '연습일지'입니다!
오늘의 목표, 성공률, 기체 상태, 경기 분석...
30초 템플릿으로 매 연습을 기록해 보세요.
기록은 가장 값싼 튜닝입니다 ✍️

#드론축구연습일지 #드론훈련 #드론조종실력
#광주임페리얼윙스 #ImperialWings #드론축구훈련""",

    "27": """광주만 아닙니다! 담양·나주·화순도 환영 🗺️

드론 취미의 가장 큰 어려움은 '함께할 사람'을 찾는 것!
광주·전남 전체에 드론 네트워크를 만들어 갑니다.
여러분이 어디에 계시든 임페리얼 윙스가 연결해 드릴게요 🤝

#광주드론동호회 #담양드론 #나주드론 #화순드론 #전남드론동호회
#광주임페리얼윙스 #ImperialWings #드론커뮤니티""",

    "28": """첫 친선경기, 이렇게 준비하면 완벽합니다! 🏆

목적 합의 → 규칙 정하기 → 장비 점검 → 심판 지정 → 피드백
친선전은 승패보다 서로 배우는 날입니다.
안전하고 다시 만나고 싶은 경기를 만들어 보세요 ✊

#드론축구친선경기 #드론축구교류전 #드론동호회교류
#광주임페리얼윙스 #ImperialWings #광주드론축구""",

    "29": """임페리얼 윙스가 꿈꾸는 팀의 모습 🌟

드론축구 · 정비와 기술 · FPV 교류 · 교육 · 콘텐츠
5가지 날개로 광주·전남 드론스포츠 커뮤니티를 만들어 갑니다.
함께 만들어 갈 분들을 기다립니다 💙

#ImperialWings #광주드론스포츠 #광주드론축구 #전남드론
#광주임페리얼윙스 #드론커뮤니티 #드론동호회""",

    "30": """[상시모집] 지금 바로 합류하세요! 🚁

광주·전남 드론축구 동호회 Imperial Wings
초보 환영 · 조립부터 대회까지 · 매주 금 2PM
댓글이나 오픈채팅으로 문의해 주세요!

📍 광주드론공원 | 💬 오픈채팅 문의
🔗 링크 인 바이오

#광주드론축구모집 #전남드론축구모집 #드론동호회회원모집
#광주드론동호회 #ImperialWings #광주임페리얼윙스 #드론축구""",
}


def get_insta_caption(post_data: dict, image_dir: str) -> tuple:
    """
    포스팅 데이터에서 인스타그램 캡션과 이미지 경로를 반환합니다.
    
    Returns:
        (caption: str, image_path: str)
    """
    # 시리즈 번호 추출
    topic = post_data.get("topic", "")
    series_num = None
    for num in INSTA_CAPTIONS.keys():
        if num in topic:
            series_num = num
            break

    # 캡션 선택
    if series_num and series_num in INSTA_CAPTIONS:
        caption = INSTA_CAPTIONS[series_num]
        image_name = f"insta_{series_num}.jpg"
    else:
        # 랜덤 선택
        series_num = random.choice(list(INSTA_CAPTIONS.keys()))
        caption = INSTA_CAPTIONS[series_num]
        image_name = f"insta_{series_num}.jpg"

    # 이미지 경로
    image_path = os.path.join(image_dir, image_name)
    if not os.path.exists(image_path):
        # 폴백: 아무 insta 이미지나 선택
        insta_images = glob.glob(os.path.join(image_dir, "insta_*.jpg"))
        if insta_images:
            image_path = random.choice(insta_images)
        else:
            image_path = None

    return caption, image_path


def upload_image_to_public_url(image_path: str) -> str:
    """
    이미지를 공개 URL로 업로드합니다.
    manus-upload-file 유틸리티를 사용합니다.
    
    Returns:
        공개 URL 문자열
    """
    try:
        result = subprocess.run(
            ["manus-upload-file", image_path],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        # URL 추출 (마지막 줄이 URL)
        lines = [l.strip() for l in output.split("\n") if l.strip()]
        for line in reversed(lines):
            if line.startswith("http"):
                return line
        print(f"[인스타] 업로드 출력: {output}")
        return None
    except Exception as e:
        print(f"[인스타] 이미지 업로드 오류: {e}")
        return None


def post_to_instagram_via_mcp(caption: str, image_url: str, log_fn=None) -> bool:
    """
    Manus MCP를 통해 인스타그램에 포스팅합니다.
    이 함수는 MCP 도구를 직접 호출하는 대신,
    스케줄러에서 MCP 호출 정보를 반환하여 처리합니다.
    
    Returns:
        dict with posting info for MCP call
    """
    return {
        "type": "post",
        "caption": caption,
        "media": [{"type": "image", "media_url": image_url}]
    }


def prepare_instagram_post(post_data: dict, image_dir: str, log_fn=None) -> dict:
    """
    인스타그램 포스팅을 위한 데이터를 준비합니다.
    
    Returns:
        {
            "caption": str,
            "image_path": str,
            "image_url": str (업로드 후),
            "ready": bool
        }
    """
    def log(msg):
        print(f"[인스타] {msg}")
        if log_fn:
            log_fn(f"[인스타] {msg}")

    log("인스타그램 포스팅 준비 중...")

    # 캡션 및 이미지 선택
    caption, image_path = get_insta_caption(post_data, image_dir)

    if not image_path or not os.path.exists(image_path):
        log("❌ 이미지 파일을 찾을 수 없습니다.")
        return {"ready": False}

    log(f"이미지 선택: {os.path.basename(image_path)}")
    log("이미지 공개 URL 업로드 중...")

    # 이미지 업로드
    image_url = upload_image_to_public_url(image_path)
    if not image_url:
        log("❌ 이미지 업로드 실패")
        return {"ready": False}

    log(f"✅ 이미지 업로드 완료: {image_url[:60]}...")

    return {
        "ready": True,
        "caption": caption,
        "image_path": image_path,
        "image_url": image_url,
    }
