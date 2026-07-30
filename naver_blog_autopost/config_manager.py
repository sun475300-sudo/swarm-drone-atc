import json
import base64
import os
from pathlib import Path

CONFIG_FILE = "config.json"

def get_config_path():
    return Path(__file__).parent / CONFIG_FILE

def _encode(text):
    """간단한 Base64 인코딩 (평문 저장 방지)"""
    if not text:
        return ""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")

def _decode(text):
    """Base64 디코딩"""
    if not text:
        return ""
    try:
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")
    except Exception:
        return text  # 이미 평문인 경우 그대로 반환

def load_config():
    """설정 파일을 불러옵니다. 비밀번호는 자동 디코딩."""
    config_path = get_config_path()
    default_config = {
        "naver_id": "",
        "naver_pw": "",
        "blog_id": "",
        "gemini_api_key": "",
        "schedule_time": "10:00",
        "is_active": False,
        "headless_mode": False
    }
    if not config_path.exists():
        save_config(default_config)
        return default_config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        # 비밀번호 디코딩
        if config.get("naver_pw"):
            config["naver_pw"] = _decode(config["naver_pw"])
        if config.get("gemini_api_key"):
            config["gemini_api_key"] = _decode(config["gemini_api_key"])
        return config
    except Exception as e:
        print(f"설정 로드 오류: {e}")
        return default_config

def save_config(config_data):
    """설정 파일을 저장합니다. 비밀번호는 자동 인코딩."""
    config_path = get_config_path()
    try:
        save_data = config_data.copy()
        # 비밀번호 인코딩 후 저장
        if save_data.get("naver_pw"):
            save_data["naver_pw"] = _encode(save_data["naver_pw"])
        if save_data.get("gemini_api_key"):
            save_data["gemini_api_key"] = _encode(save_data["gemini_api_key"])
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"설정 저장 오류: {e}")
        return False
