# PyInstaller spec for SDACS backend
# Build: pyinstaller desktop/backend.spec --clean --noconfirm
# Output: dist/sdacs-backend/sdacs-backend.exe (+libs)
#
# 정책:
#   - one-folder 모드: --onedir. one-file 보다 첫 실행이 빠르다 (임시 압축해제 없음).
#   - Electron 이 sdacs-backend.exe 를 child_process.spawn 으로 실행 → stdout 파싱.
#   - torch 포함: visualization._callbacks 가 transitively 임포트하므로 배제 어려움.
#     크기가 문제되면 Phase 1.5 로 lazy import 리팩터링 (지금은 스코프 아님).

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 프로젝트 루트를 spec 파일 기준으로 계산
import os
_HERE = os.path.dirname(os.path.abspath(SPEC))  # desktop/
_ROOT = os.path.dirname(_HERE)                    # repo root

block_cipher = None


# Dash 는 template/asset을 런타임에 로드하는 dynamic 임포트를 씀 → 명시적 수집 필요
hidden = []
hidden += collect_submodules('dash')
hidden += collect_submodules('plotly')
hidden += ['simpy', 'scipy', 'scipy.spatial', 'scipy.optimize', 'numpy']

# 프로젝트 자체 패키지
hidden += collect_submodules('visualization')
hidden += collect_submodules('simulation')
hidden += collect_submodules('src')

# datas — 런타임에 필요한 정적 파일 (config, YAML)
datas = []
datas += [(os.path.join(_ROOT, 'config'), 'config')]

# plotly / dash 정적 리소스
datas += collect_data_files('plotly')
datas += collect_data_files('dash')


a = Analysis(
    [os.path.join(_HERE, 'backend_launcher.py')],
    pathex=[_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # UI/notebook 관련 무거운 것 배제
        'jupyter',
        'notebook',
        'ipykernel',
        'ipython',
        'IPython',
        'matplotlib.tests',
        'PyQt5',
        'PySide2',
        'PySide6',
        'PyQt6',
        'tkinter.test',
        # 테스트/문서 도구
        'pytest',
        'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sdacs-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 는 안티바이러스 오탐 유발 → 미사용
    console=True,       # Electron 이 stdout 을 읽어야 함
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='sdacs-backend',
)
