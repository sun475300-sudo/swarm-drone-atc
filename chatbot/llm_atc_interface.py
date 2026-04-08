"""
LLM ATC Interface (Phase 665)

이 모듈은 대형 언어 모델(LLM)을 활용하여 자연어 형태의 관제 명령을
시스템이 이해할 수 있는 내부 프로토콜(ClearanceRequest, ResolutionAdvisory 등)로
변환하는 인터페이스 역할을 합니다.
"""
import re

class LlmAtcInterface:
    def __init__(self, backend="vllm", model_name="k-utm-instruct-7b"):
        self.backend = backend
        self.model_name = model_name
        self._intents = ["CLIMB", "DESCEND", "TURN", "HOLD", "RTL", "EVADE"]

    def parse_natural_language_command(self, text: str) -> dict:
        """
        자연어 텍스트를 파싱하여 관제 명령 딕셔너리로 반환합니다.
        실제 LLM 백엔드 대신, 가벼운 정규식/규칙 시스템 폴백 또는 Mock 버전을 제공합니다.
        
        Args:
            text: 예) "모든 상업용 드론은 80m로 즉시 상승하라"
        Returns:
            명령 구조 딕셔너리
        """
        # 간단한 룰 기반 폴백 매칭 (LLM 서버 장애 시 동작)
        action = "HOLD"
        target_group = "ALL"
        value = None

        if "상업용" in text:
            target_group = "COMMERCIAL_DELIVERY"
        elif "미등록" in text or "침입" in text:
            target_group = "ROGUE"
            
        if "상승" in text:
            action = "CLIMB"
        elif "하강" in text:
            action = "DESCEND"
        elif "회피" in text:
            action = "EVADE_APF"
        elif "복귀" in text or "돌아가" in text:
            action = "RTL"
            
        # 숫자 추출 (예: 80m -> 80.0)
        nums = re.findall(r'\d+', text)
        if nums:
            value = float(nums[0])
            
        return {
            "source": "llm_atc",
            "target_profile": target_group,
            "action": action,
            "parameter": value,
            "raw_text": text
        }

    def trigger_action(self, controller, command: dict):
        """
        AirspaceController 객체의 상태를 직접 변경하거나 어드바이저리를 발행합니다.
        """
        print(f"[LLM-ATC] Dispatching Intent: {command['action']} to {command['target_profile']}")
        # 실제 컨트롤러 연동 시:
        # controller.broadcast_advisory(target=command['target_profile'], type=command['action'])
        return True

if __name__ == "__main__":
    llm_interface = LlmAtcInterface()
    cmd = llm_interface.parse_natural_language_command("긴급상황. 모든 상업용 드론 80m로 상승 대기하라.")
    print("Parsed Intent:", cmd)
