import asyncio
import random
import os
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright가 설치되지 않았습니다. 'pip install playwright'를 실행하세요.")

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"

async def random_delay(min_sec=0.5, max_sec=1.5):
    """사람처럼 보이게 하기 위한 랜덤 딜레이"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)

async def login_naver(page, naver_id, naver_pw):
    """네이버 로그인 수행"""
    print("🔐 네이버 로그인 중...")
    try:
        await page.goto(NAVER_LOGIN_URL, wait_until='networkidle', timeout=30000)
        await random_delay(1, 2)
        
        # ID 입력
        await page.fill('input[name="id"]', naver_id)
        await random_delay(0.5, 1)
        
        # PW 입력
        await page.fill('input[name="pw"]', naver_pw)
        await random_delay(0.5, 1)
        
        # 로그인 버튼 클릭
        await page.click('button[type="submit"]')
        
        # 로그인 완료 대기 (URL 변경 확인)
        await page.wait_for_url(lambda url: 'blog.naver.com' in url or 'naver.com' in url, timeout=15000)
        await random_delay(2, 3)
        
        print("✓ 네이버 로그인 성공")
        return True
        
    except Exception as e:
        print(f"❌ 로그인 실패 (봇 감지 또는 정보 오류): {e}")
        return False

async def post_to_blog(page, blog_id, post_data, image_dir=None):
    """네이버 블로그에 글 작성 및 발행"""
    write_url = f"https://blog.naver.com/{blog_id}/PostWriteForm.naver"
    print(f"📝 포스팅 작성 중: {post_data['title'][:30]}...")
    
    try:
        # 포스팅 작성 페이지 이동
        await page.goto(write_url, wait_until='networkidle', timeout=30000)
        await random_delay(2, 4)
        
        # 제목 입력
        print("  - 제목 입력 중...")
        title_selector = 'input[placeholder*="제목"]'
        await page.fill(title_selector, post_data['title'])
        await random_delay(1, 2)
        
        # 본문 입력 (에디터 프레임 처리)
        print("  - 본문 입력 중...")
        try:
            frames = page.frames
            editor_frame = None
            
            for frame in frames:
                try:
                    if await frame.query_selector('textarea') or await frame.query_selector('[contenteditable]'):
                        editor_frame = frame
                        break
                except:
                    pass
            
            if editor_frame:
                # contenteditable div에 입력
                editable = await editor_frame.query_selector('[contenteditable="true"]')
                if editable:
                    await editor_frame.fill('[contenteditable="true"]', post_data['body'])
                else:
                    await editor_frame.fill('textarea', post_data['body'])
            else:
                await page.fill('textarea', post_data['body'])
        except Exception as e:
            print(f"  ⚠ 본문 입력 중 오류: {e}")
            
        await random_delay(1, 2)
        
        # 랜덤 이미지 업로드 (이미지 디렉토리가 있는 경우)
        if image_dir and os.path.exists(image_dir):
            images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            if images:
                selected_img = random.choice(images)
                img_path = os.path.join(image_dir, selected_img)
                print(f"  - 이미지 업로드 중... ({selected_img})")
                try:
                    upload_btn = await page.query_selector('button[title*="이미지"]') or \
                                 await page.query_selector('button:has-text("이미지")')
                    
                    if upload_btn:
                        await upload_btn.click()
                        await random_delay(1, 2)
                        
                        file_input = await page.query_selector('input[type="file"]')
                        if file_input:
                            await file_input.set_input_files(img_path)
                            await random_delay(2, 3)
                except Exception as e:
                    print(f"  ⚠ 이미지 업로드 중 오류: {e}")
                    
        # 해시태그 입력
        if post_data.get('hashtags'):
            print("  - 해시태그 입력 중...")
            try:
                tag_selector = 'input[placeholder*="태그"]'
                tag_input = await page.query_selector(tag_selector)
                if tag_input:
                    await tag_input.fill(post_data['hashtags'])
                    await random_delay(0.5, 1)
            except:
                pass
                
        # 발행 버튼 클릭
        print("  - 포스팅 발행 중...")
        await random_delay(1, 2)
        
        publish_btn = await page.query_selector('button:has-text("발행")') or \
                      await page.query_selector('button:has-text("저장")') or \
                      await page.query_selector('button[class*="publish"]')
                      
        if publish_btn:
            await publish_btn.click()
            await random_delay(3, 5)
            print("✓ 포스팅 발행 완료!")
            return True
        else:
            print("⚠ 발행 버튼을 찾을 수 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 포스팅 작성 실패: {e}")
        return False

async def run_auto_post(naver_id, naver_pw, blog_id, post_data, image_dir=None, headless=False):
    """브라우저를 열고 로그인 후 포스팅하는 전체 프로세스"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 720},
        )
        
        page = await context.new_page()
        
        # 봇 감지 우회
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
        
        success = False
        if await login_naver(page, naver_id, naver_pw):
            success = await post_to_blog(page, blog_id, post_data, image_dir)
            
        await browser.close()
        return success
