"""
광주 임페리얼 윙스 — 네이버 블로그 + 인스타그램 자동 포스팅 시스템
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os
import sys
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import config_manager
from scheduler import BlogScheduler

# ── 브랜드 컬러 ──────────────────────────────────────────────
C_BG      = "#0A1940"
C_PANEL   = "#0D2260"
C_CARD    = "#112B75"
C_CYAN    = "#00B4DC"
C_GOLD    = "#FFC832"
C_WHITE   = "#FFFFFF"
C_LGRAY   = "#B0C4DE"
C_DGRAY   = "#6B7FA3"
C_SUCCESS = "#2ECC71"
C_DANGER  = "#E74C3C"
C_WARN    = "#F39C12"

FONT_TITLE = ("Malgun Gothic", 18, "bold")
FONT_HEAD  = ("Malgun Gothic", 11, "bold")
FONT_BODY  = ("Malgun Gothic", 10)
FONT_SMALL = ("Malgun Gothic",  9)
FONT_LOG   = ("Consolas",       9)


class ImperialWingsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚁 Imperial Wings — 자동 포스팅 시스템")
        self.geometry("920x720")
        self.resizable(False, False)
        self.configure(bg=C_BG)

        self.scheduler = BlogScheduler(log_callback=self._append_log)
        self._scheduler_running = False

        # 설정 로드 및 기본값 설정
        self.config_data = config_manager.load_config()
        if not self.config_data.get("naver_id"):
            self.config_data["naver_id"] = "sun475300"
        if not self.config_data.get("naver_pw"):
            self.config_data["naver_pw"] = "Wkdtjsdn01!"
        if not self.config_data.get("blog_id"):
            self.config_data["blog_id"] = "sun475300"
        if "post_naver" not in self.config_data:
            self.config_data["post_naver"] = True
        if "post_instagram" not in self.config_data:
            self.config_data["post_instagram"] = True
        config_manager.save_config(self.config_data)

        self._build_ui()
        self._load_config_to_ui()

    # ── UI 구성 ──────────────────────────────────────────────

    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=C_PANEL, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🚁  IMPERIAL WINGS",
                 font=("Malgun Gothic", 20, "bold"),
                 bg=C_PANEL, fg=C_CYAN).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="네이버 블로그 + 인스타그램 자동 포스팅",
                 font=FONT_BODY, bg=C_PANEL, fg=C_LGRAY).pack(side="left", pady=14)
        self.status_dot   = tk.Label(hdr, text="●", font=("Arial", 16),
                                     bg=C_PANEL, fg=C_DGRAY)
        self.status_label = tk.Label(hdr, text="대기 중",
                                     font=FONT_SMALL, bg=C_PANEL, fg=C_DGRAY)
        self.status_dot.pack(side="right", padx=6)
        self.status_label.pack(side="right", padx=2)

        tk.Frame(self, bg=C_CYAN, height=2).pack(fill="x")

        # 메인 영역
        main = tk.Frame(self, bg=C_BG)
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # 좌측 설정
        left = tk.Frame(main, bg=C_BG, width=400)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        # 탭 노트북
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_CARD, foreground=C_LGRAY,
                        font=FONT_BODY, padding=[10, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", C_CYAN)],
                  foreground=[("selected", C_BG)])

        nb = ttk.Notebook(left)
        nb.pack(fill="both", expand=True)

        # 탭 1: 계정 설정
        tab1 = tk.Frame(nb, bg=C_BG)
        nb.add(tab1, text="  계정 설정  ")
        self._build_account_tab(tab1)

        # 탭 2: 포스팅 설정
        tab2 = tk.Frame(nb, bg=C_BG)
        nb.add(tab2, text="  포스팅 설정  ")
        self._build_posting_tab(tab2)

        # 우측 로그
        right = tk.Frame(main, bg=C_BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_log(right)

        # 하단 버튼
        self._build_buttons()

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=C_CARD, bd=0)
        f.pack(fill="x", pady=(0, 10))
        tk.Label(f, text=title, font=FONT_HEAD,
                 bg=C_CARD, fg=C_CYAN).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Frame(f, bg=C_CYAN, height=1).pack(fill="x", padx=12)
        inner = tk.Frame(f, bg=C_CARD)
        inner.pack(fill="x", padx=12, pady=8)
        return inner

    def _row(self, parent, label, var, show="", width=24):
        row = tk.Frame(parent, bg=C_CARD)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=FONT_BODY, bg=C_CARD,
                 fg=C_LGRAY, width=14, anchor="w").pack(side="left")
        e = tk.Entry(row, textvariable=var, show=show,
                     font=FONT_BODY, bg="#1A3580", fg=C_WHITE,
                     insertbackground=C_WHITE, relief="flat", width=width, bd=4)
        e.pack(side="left", fill="x", expand=True)
        return e

    def _build_account_tab(self, parent):
        # 네이버 계정
        c1 = self._card(parent, "  🔐  네이버 계정")
        self.var_id  = tk.StringVar()
        self.var_pw  = tk.StringVar()
        self.var_bid = tk.StringVar()
        self._row(c1, "아이디",    self.var_id)
        self._row(c1, "비밀번호",  self.var_pw, show="●")
        self._row(c1, "블로그 ID", self.var_bid)

        # 인스타그램 계정
        c2 = self._card(parent, "  📸  인스타그램 계정")
        tk.Label(c2, text="연결된 계정: @giw2.025\n(광주·전남 드론축구 동호회 Imperial Wings)",
                 font=FONT_SMALL, bg=C_CARD, fg=C_SUCCESS,
                 justify="left").pack(anchor="w", pady=4)
        tk.Label(c2, text="※ 인스타그램은 Manus MCP를 통해 자동 연결됩니다.",
                 font=FONT_SMALL, bg=C_CARD, fg=C_DGRAY).pack(anchor="w")

        # AI 설정
        c3 = self._card(parent, "  🤖  AI 콘텐츠 생성 (선택)")
        self.var_api = tk.StringVar()
        self._row(c3, "Gemini API Key", self.var_api, show="●", width=20)
        tk.Label(c3, text="※ 비워두면 기본 원고(15종) 자동 선택",
                 font=FONT_SMALL, bg=C_CARD, fg=C_DGRAY).pack(anchor="w", pady=(2,0))

        # 저장 버튼
        tk.Button(parent, text="💾  설정 저장", font=FONT_HEAD,
                  bg=C_CYAN, fg=C_BG, relief="flat", bd=0,
                  cursor="hand2", command=self._save_config
                  ).pack(fill="x", ipady=8, pady=(6, 0))

    def _build_posting_tab(self, parent):
        # 플랫폼 선택
        c1 = self._card(parent, "  📢  포스팅 플랫폼 선택")
        self.var_post_naver = tk.BooleanVar(value=True)
        self.var_post_insta = tk.BooleanVar(value=True)

        chk_style = dict(font=FONT_BODY, bg=C_CARD, fg=C_WHITE,
                         selectcolor=C_CARD, activebackground=C_CARD,
                         activeforeground=C_WHITE)
        tk.Checkbutton(c1, text="🌐  네이버 블로그 포스팅",
                       variable=self.var_post_naver, **chk_style).pack(anchor="w", pady=3)
        tk.Checkbutton(c1, text="📸  인스타그램 포스팅 (@giw2.025)",
                       variable=self.var_post_insta, **chk_style).pack(anchor="w", pady=3)

        # 스케줄 설정
        c2 = self._card(parent, "  ⏰  자동 포스팅 스케줄")
        row_t = tk.Frame(c2, bg=C_CARD)
        row_t.pack(fill="x", pady=3)
        tk.Label(row_t, text="매일 포스팅 시각", font=FONT_BODY,
                 bg=C_CARD, fg=C_LGRAY, width=14, anchor="w").pack(side="left")
        self.var_time = tk.StringVar()
        times = [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 30)]
        ttk.Combobox(row_t, textvariable=self.var_time, values=times,
                     font=FONT_BODY, width=8, state="readonly").pack(side="left")

        row_h = tk.Frame(c2, bg=C_CARD)
        row_h.pack(fill="x", pady=3)
        self.var_headless = tk.BooleanVar()
        tk.Checkbutton(row_h, text="백그라운드 실행 (브라우저 창 숨김)",
                       variable=self.var_headless,
                       font=FONT_SMALL, bg=C_CARD, fg=C_LGRAY,
                       selectcolor=C_CARD, activebackground=C_CARD,
                       activeforeground=C_WHITE).pack(anchor="w")

        # 인스타그램 즉시 포스팅 안내
        c3 = self._card(parent, "  📸  인스타그램 즉시 포스팅")
        tk.Label(c3,
                 text="'지금 바로 포스팅' 버튼을 누르면\n네이버 블로그와 인스타그램에 동시 포스팅됩니다.\n\n인스타그램은 확인 카드가 표시되면\n'게시' 버튼을 눌러 최종 확인해 주세요.",
                 font=FONT_SMALL, bg=C_CARD, fg=C_LGRAY,
                 justify="left").pack(anchor="w", pady=4)

        # 저장 버튼
        tk.Button(parent, text="💾  설정 저장", font=FONT_HEAD,
                  bg=C_CYAN, fg=C_BG, relief="flat", bd=0,
                  cursor="hand2", command=self._save_config
                  ).pack(fill="x", ipady=8, pady=(6, 0))

    def _build_log(self, parent):
        tk.Label(parent, text="  📋  실행 로그", font=FONT_HEAD,
                 bg=C_BG, fg=C_CYAN, anchor="w").pack(fill="x")
        tk.Frame(parent, bg=C_CYAN, height=1).pack(fill="x", pady=(2, 6))

        self.log_box = scrolledtext.ScrolledText(
            parent, font=FONT_LOG,
            bg="#060E26", fg="#A8D8EA",
            insertbackground=C_WHITE,
            relief="flat", bd=0,
            wrap="word", state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.tag_config("success", foreground=C_SUCCESS)
        self.log_box.tag_config("error",   foreground=C_DANGER)
        self.log_box.tag_config("info",    foreground=C_CYAN)
        self.log_box.tag_config("warn",    foreground=C_WARN)

        tk.Button(parent, text="🗑  로그 지우기", font=FONT_SMALL,
                  bg=C_PANEL, fg=C_LGRAY, relief="flat", bd=0,
                  cursor="hand2", command=self._clear_log
                  ).pack(anchor="e", pady=(4, 0))

    def _build_buttons(self):
        bar = tk.Frame(self, bg=C_PANEL, height=64)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C_CYAN, height=2).pack(fill="x")

        bf = tk.Frame(bar, bg=C_PANEL)
        bf.pack(expand=True)

        self.btn_start = tk.Button(
            bf, text="▶  스케줄러 시작", font=FONT_HEAD,
            bg=C_CYAN, fg=C_BG, relief="flat", bd=0,
            cursor="hand2", width=16, command=self._toggle_scheduler)
        self.btn_start.pack(side="left", padx=8, pady=10, ipady=6)

        tk.Button(
            bf, text="⚡  지금 바로 포스팅", font=FONT_HEAD,
            bg=C_GOLD, fg=C_BG, relief="flat", bd=0,
            cursor="hand2", width=18, command=self._run_now
        ).pack(side="left", padx=8, pady=10, ipady=6)

        tk.Button(
            bf, text="📸  인스타 즉시 포스팅", font=FONT_HEAD,
            bg="#E1306C", fg=C_WHITE, relief="flat", bd=0,
            cursor="hand2", width=18, command=self._run_insta_only
        ).pack(side="left", padx=8, pady=10, ipady=6)

        tk.Button(
            bf, text="✕  종료", font=FONT_HEAD,
            bg=C_PANEL, fg=C_LGRAY, relief="flat", bd=0,
            cursor="hand2", width=8, command=self._on_close
        ).pack(side="left", padx=8, pady=10, ipady=6)

    # ── 기능 메서드 ──────────────────────────────────────────

    def _load_config_to_ui(self):
        self.var_id.set(self.config_data.get("naver_id", ""))
        self.var_pw.set(self.config_data.get("naver_pw", ""))
        self.var_bid.set(self.config_data.get("blog_id", ""))
        self.var_api.set(self.config_data.get("gemini_api_key", ""))
        self.var_time.set(self.config_data.get("schedule_time", "10:00"))
        self.var_headless.set(self.config_data.get("headless_mode", False))
        self.var_post_naver.set(self.config_data.get("post_naver", True))
        self.var_post_insta.set(self.config_data.get("post_instagram", True))

    def _save_config(self):
        data = {
            "naver_id":       self.var_id.get().strip(),
            "naver_pw":       self.var_pw.get().strip(),
            "blog_id":        self.var_bid.get().strip(),
            "gemini_api_key": self.var_api.get().strip(),
            "schedule_time":  self.var_time.get(),
            "is_active":      self._scheduler_running,
            "headless_mode":  self.var_headless.get(),
            "post_naver":     self.var_post_naver.get(),
            "post_instagram": self.var_post_insta.get(),
        }
        if not data["naver_id"] or not data["naver_pw"] or not data["blog_id"]:
            messagebox.showwarning("입력 오류", "네이버 아이디, 비밀번호, 블로그 ID는 필수입니다.")
            return
        config_manager.save_config(data)
        self.config_data = data
        self._append_log("✅ 설정이 저장되었습니다.")
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")

    def _toggle_scheduler(self):
        if not self._scheduler_running:
            self._save_config()
            self.scheduler = BlogScheduler(log_callback=self._append_log)
            self.scheduler.start()
            self._scheduler_running = True
            self.btn_start.config(text="⏹  스케줄러 중지", bg=C_DANGER)
            self._set_status("실행 중", C_SUCCESS)
        else:
            self.scheduler.stop()
            self._scheduler_running = False
            self.btn_start.config(text="▶  스케줄러 시작", bg=C_CYAN)
            self._set_status("대기 중", C_DGRAY)

    def _run_now(self):
        platforms = []
        if self.var_post_naver.get():
            platforms.append("네이버 블로그")
        if self.var_post_insta.get():
            platforms.append("인스타그램 (@giw2.025)")
        if not platforms:
            messagebox.showwarning("설정 오류", "포스팅할 플랫폼을 하나 이상 선택하세요.")
            return
        msg = "다음 플랫폼에 지금 바로 포스팅하시겠습니까?\n\n" + "\n".join(f"• {p}" for p in platforms)
        if messagebox.askyesno("즉시 포스팅", msg):
            self._save_config()
            self.scheduler = BlogScheduler(log_callback=self._append_log)
            self.scheduler.run_now()
            self._set_status("포스팅 중...", C_WARN)

    def _run_insta_only(self):
        """인스타그램만 즉시 포스팅"""
        if messagebox.askyesno("인스타그램 포스팅",
                               "@giw2.025 계정에 지금 바로 포스팅하시겠습니까?\n"
                               "(확인 카드가 표시되면 '게시' 버튼을 눌러주세요)"):
            self._append_log("📸 [인스타그램] 즉시 포스팅 준비 중...")
            self._set_status("인스타 포스팅 중...", "#E1306C")
            threading.Thread(target=self._insta_only_job, daemon=True).start()

    def _insta_only_job(self):
        """인스타그램 단독 포스팅 작업"""
        try:
            import random
            from posts_data import POSTS
            from instagram_poster import prepare_instagram_post

            image_dir = os.path.join(BASE_DIR, "images")
            key = random.choice(list(POSTS.keys()))
            post_data = dict(POSTS[key])
            post_data["topic"] = f"시리즈 {key}"

            self._append_log(f"📌 선택된 시리즈: {key}")
            insta_data = prepare_instagram_post(post_data, image_dir, self._append_log)

            if insta_data.get("ready"):
                self._append_log(f"📤 이미지 URL: {insta_data['image_url'][:60]}...")
                self._append_log("💡 인스타그램 MCP 포스팅 요청 완료!")
                self._append_log("   → Manus 화면에서 확인 카드가 표시되면 '게시'를 눌러주세요.")
                self.after(0, lambda: self._set_status("인스타 확인 필요", "#E1306C"))
            else:
                self._append_log("❌ 인스타그램 포스팅 준비 실패")
                self.after(0, lambda: self._set_status("대기 중", C_DGRAY))
        except Exception as e:
            self._append_log(f"❌ 오류: {e}")
            self.after(0, lambda: self._set_status("대기 중", C_DGRAY))

    def _set_status(self, text, color):
        self.status_label.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    def _append_log(self, message):
        def _do():
            self.log_box.config(state="normal")
            tag = "info"
            if "✅" in message or "성공" in message:
                tag = "success"
            elif "❌" in message or "실패" in message or "오류" in message:
                tag = "error"
            elif "⚠" in message or "경고" in message or "💡" in message:
                tag = "warn"
            self.log_box.insert("end", message + "\n", tag)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _on_close(self):
        if self._scheduler_running:
            if not messagebox.askyesno("종료 확인", "스케줄러가 실행 중입니다.\n종료하시겠습니까?"):
                return
            self.scheduler.stop()
        self.destroy()


if __name__ == "__main__":
    app = ImperialWingsApp()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()
