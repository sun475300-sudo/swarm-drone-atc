"""
통합 스케줄러 — 네이버 블로그 + 인스타그램 동시 자동 포스팅
"""
import schedule
import time
import threading
import asyncio
import random
import subprocess
import json
import os
from datetime import datetime
import config_manager
from content_generator import generate_post_content
from posts_data import POSTS
from blog_poster import run_auto_post
from instagram_poster import prepare_instagram_post


class BlogScheduler:
    def __init__(self, log_callback=None):
        self.running = False
        self.thread = None
        self.log_callback = log_callback

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        if self.log_callback:
            self.log_callback(formatted)

    def job(self):
        self.log("=" * 50)
        self.log("자동 포스팅 작업 시작!")
        config = config_manager.load_config()

        if not config.get("naver_id") or not config.get("naver_pw") or not config.get("blog_id"):
            self.log("❌ 네이버 계정 정보가 없습니다. 설정을 확인하세요.")
            return

        # ── 1. 콘텐츠 준비 ──────────────────────────────────
        api_key = config.get("gemini_api_key", "").strip()
        if api_key:
            self.log("🤖 Gemini AI로 새 콘텐츠 생성 중...")
            try:
                post_data = generate_post_content(api_key)
            except Exception as e:
                self.log(f"⚠️  AI 생성 실패, 기본 원고 사용: {e}")
                post_data = self._pick_random_post()
        else:
            self.log("📝 기본 원고 중 하나를 무작위로 선택합니다.")
            post_data = self._pick_random_post()

        self.log(f"📌 주제: {post_data.get('topic', '-')}")
        self.log(f"📰 제목: {post_data.get('title', '-')[:50]}...")

        image_dir = os.path.join(os.path.dirname(__file__), "images")

        # ── 2. 네이버 블로그 포스팅 ─────────────────────────
        naver_enabled = config.get("post_naver", True)
        if naver_enabled:
            self.log("─" * 40)
            self.log("🌐 [네이버 블로그] 포스팅 시작...")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                naver_ok = loop.run_until_complete(
                    run_auto_post(
                        config["naver_id"],
                        config["naver_pw"],
                        config["blog_id"],
                        post_data,
                        image_dir,
                        config.get("headless_mode", False)
                    )
                )
                loop.close()
                if naver_ok:
                    self.log("✅ [네이버 블로그] 포스팅 성공!")
                else:
                    self.log("❌ [네이버 블로그] 포스팅 실패")
            except Exception as e:
                self.log(f"❌ [네이버 블로그] 오류: {e}")
        else:
            self.log("⏭️  네이버 블로그 포스팅 건너뜀 (비활성화)")

        # ── 3. 인스타그램 포스팅 ────────────────────────────
        insta_enabled = config.get("post_instagram", True)
        if insta_enabled:
            self.log("─" * 40)
            self.log("📸 [인스타그램] 포스팅 준비 중...")
            try:
                insta_data = prepare_instagram_post(post_data, image_dir, self.log)
                if insta_data.get("ready"):
                    self.log("📤 [인스타그램] MCP를 통해 포스팅 중...")
                    result = self._post_instagram_mcp(
                        insta_data["caption"],
                        insta_data["image_url"]
                    )
                    if result:
                        self.log("✅ [인스타그램] 포스팅 성공!")
                    else:
                        self.log("❌ [인스타그램] 포스팅 실패")
                else:
                    self.log("❌ [인스타그램] 이미지 준비 실패")
            except Exception as e:
                self.log(f"❌ [인스타그램] 오류: {e}")
        else:
            self.log("⏭️  인스타그램 포스팅 건너뜀 (비활성화)")

        self.log("=" * 50)
        self.log(f"✅ 모든 포스팅 작업 완료! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

    def _pick_random_post(self) -> dict:
        """기본 원고 중 랜덤 선택"""
        key = random.choice(list(POSTS.keys()))
        data = dict(POSTS[key])
        data["topic"] = f"시리즈 {key}"
        return data

    def _post_instagram_mcp(self, caption: str, image_url: str) -> bool:
        """
        manus-mcp-cli를 통해 인스타그램에 포스팅합니다.
        """
        try:
            payload = json.dumps({
                "type": "post",
                "caption": caption,
                "media": [{"type": "image", "media_url": image_url}]
            })
            result = subprocess.run(
                ["manus-mcp-cli", "tool", "call", "instagram", "create_instagram",
                 "--arguments", payload],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                return True
            else:
                self.log(f"MCP 오류: {result.stderr[:200]}")
                return False
        except FileNotFoundError:
            # manus-mcp-cli가 없는 환경 (로컬 PC)에서는 별도 처리
            self.log("⚠️  인스타그램 MCP는 Manus 환경에서만 자동 실행됩니다.")
            self.log("   로컬 PC에서는 앱의 '인스타 즉시 포스팅' 버튼을 사용하세요.")
            return False
        except Exception as e:
            self.log(f"MCP 호출 오류: {e}")
            return False

    def _run_pending(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        if self.running:
            return
        config = config_manager.load_config()
        target_time = config.get("schedule_time", "10:00")
        schedule.clear()
        schedule.every().day.at(target_time).do(self.job)
        self.running = True
        self.thread = threading.Thread(target=self._run_pending, daemon=True)
        self.thread.start()
        self.log(f"▶️  스케줄러 시작 — 매일 {target_time} 자동 포스팅 예정")

    def stop(self):
        self.running = False
        schedule.clear()
        self.log("⏹️  스케줄러가 중지되었습니다.")

    def run_now(self):
        """즉시 실행 (GUI 블로킹 방지)"""
        threading.Thread(target=self.job, daemon=True).start()
