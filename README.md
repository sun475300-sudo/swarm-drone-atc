# 군집드론 공역통제 자동화 시스템 (SDACS)

> **Swarm Drone Airspace Control System** — 자율 비행 군집드론의 충돌 회피, 경로 계획, 임무 조율을 담당하는 자동화 공역통제 시스템

---

## 📋 목차

- [개요](#개요)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [시작하기](#시작하기)
- [커밋이 Unverified로 표시되는 이유](#커밋이-unverified로-표시되는-이유)
- [GPG 서명 설정 방법](#gpg-서명-설정-방법)
- [라이선스](#라이선스)

---

## 개요

SDACS는 SimPy 기반의 이산 이벤트 시뮬레이션 위에서 동작하며, 다음 핵심 기능을 제공합니다.

| 기능 | 설명 |
|------|------|
| **CBS 경로 계획** | Conflict-Based Search 알고리즘으로 다중 드론 경로 충돌 사전 해결 |
| **APF 충돌 회피** | Artificial Potential Field 기반 실시간 장애물 회피 기동 |
| **Voronoi 공역 분할** | 드론 밀도에 따른 동적 공역 구획 관리 |
| **Redis 통신 버스** | 비동기 메시지 브로커를 통한 드론 간 실시간 통신 |
| **FastAPI 백엔드** | REST API + WebSocket으로 실시간 상태 모니터링 |
| **PX4 SITL 연동** | Gazebo ROS2 시뮬레이터와 연동한 현실적 비행 테스트 |

---

## 기술 스택

- **언어:** Python 3.11+
- **시뮬레이션:** SimPy 4.1+, NumPy 2.0+, SciPy 1.13+
- **웹 백엔드:** FastAPI 0.111+, Uvicorn 0.30+, Pydantic 2.7+
- **캐시/메시지:** Redis 5.0+, aioredis 2.0+
- **시각화:** Plotly 5.22+, Dash 2.17+, Matplotlib 3.9+
- **컴퓨터 비전:** OpenCV 4.10+, YOLOv8 8.2+
- **컨테이너:** Docker, Docker Compose
- **테스트:** pytest 8.2+, hypothesis 6.100+

---

## 프로젝트 구조

```
swarm-drone-atc/
├── src/airspace_control/
│   ├── agents/          # 드론 에이전트 상태 및 프로파일
│   ├── avoidance/       # 충돌 회피 Resolution Advisory
│   ├── comms/           # 통신 버스 및 메시지 타입
│   ├── controller/      # 우선순위 큐 기반 관제 컨트롤러
│   ├── planning/        # 경로 계획 및 웨이포인트
│   └── utils/           # 지리 좌표 변환 등 유틸리티
├── simulation/
│   ├── apf_engine/      # APF 충돌 회피 엔진
│   ├── cbs_planner/     # CBS 다중 에이전트 경로 계획
│   └── voronoi_airspace/ # Voronoi 공역 분할
├── config/              # YAML 설정 파일 (공역, 드론 프로파일, 시나리오)
├── data/seeds/          # 검증된 시뮬레이션 시드
└── docker-compose.yml   # Redis, vLLM, FastAPI, PX4 SITL 오케스트레이션
```

---

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Docker 서비스 실행

```bash
docker compose up -d redis backend dashboard
```

### 3. 테스트 실행

```bash
pytest
```

---

## 커밋이 Unverified로 표시되는 이유

GitHub에서 커밋 옆에 **"Unverified"** 배지가 표시되는 것은 해당 커밋에 **GPG(또는 SSH) 서명이 없거나**, 서명은 있지만 **GitHub 계정에 등록된 키와 일치하지 않기** 때문입니다.

### GitHub 커밋 서명 검증 원리

```
커밋 생성
    │
    ▼
GPG 개인키로 서명 (git commit -S)
    │
    ▼
GitHub 서버에서 공개키로 서명 검증
    │
    ├── 검증 성공 → ✅ Verified  배지
    └── 검증 실패 / 서명 없음 → ⚠️ Unverified 배지
```

### Unverified가 표시되는 주요 원인

| 원인 | 설명 |
|------|------|
| **서명 미설정** | `git config commit.gpgsign true`가 설정되지 않아 서명 없이 커밋이 생성됨 |
| **공개키 미등록** | 로컬에서 GPG 서명을 했으나 해당 공개키가 GitHub 계정에 등록되지 않음 |
| **이메일 불일치** | 커밋의 author email이 GitHub 계정 이메일 또는 GPG 키의 이메일과 다름 |
| **키 만료** | GPG 키의 유효기간이 만료됨 |
| **봇/자동화 커밋** | GitHub Actions, Copilot 에이전트 등 봇이 생성한 커밋은 별도 서명이 없으면 Unverified로 표시됨 |

> **이 저장소의 경우:** 일부 커밋이 `copilot-swe-agent[bot]` 또는 로컬 개발 환경에서 GPG 서명 없이 생성되어 Unverified로 표시됩니다.

---

## GPG 서명 설정 방법

### 1단계: GPG 키 생성

```bash
gpg --full-generate-key
```

- 키 종류: `RSA and RSA` 선택
- 키 길이: `4096` 권장
- 유효기간: 적절히 설정
- 이름/이메일: GitHub 계정 이메일과 **동일하게** 입력

### 2단계: 생성된 키 ID 확인

```bash
gpg --list-secret-keys --keyid-format=long
```

출력 예시:
```
sec   rsa4096/ABCD1234EFGH5678 2024-01-01 [SC]
```

`ABCD1234EFGH5678` 부분이 키 ID입니다.

### 3단계: 공개키를 GitHub에 등록

```bash
# 공개키 출력
gpg --armor --export ABCD1234EFGH5678
```

출력된 `-----BEGIN PGP PUBLIC KEY BLOCK-----` 내용을 복사하여:  
**GitHub → Settings → SSH and GPG keys → New GPG key** 에 붙여넣기

### 4단계: Git에 GPG 서명 설정

```bash
# 서명에 사용할 키 ID 등록
git config --global user.signingkey ABCD1234EFGH5678

# 모든 커밋에 자동으로 서명 적용
git config --global commit.gpgsign true
```

### 5단계: 설정 확인

```bash
# 서명된 테스트 커밋 생성
git commit --allow-empty -m "test: GPG 서명 테스트"

# GitHub에 push 후 커밋 목록에서 ✅ Verified 확인
```

### macOS에서 GPG Suite 사용 시

```bash
brew install gnupg pinentry-mac
echo "pinentry-program $(brew --prefix)/bin/pinentry-mac" >> ~/.gnupg/gpg-agent.conf
```

### GitHub Actions에서 서명된 커밋 만들기

워크플로우에서 봇 커밋을 서명하려면 `actions/checkout`에 `commit-signing`을 활성화하거나,
GPG 키를 Repository Secret에 저장하고 서명 단계를 추가합니다.

```yaml
- name: Import GPG key
  uses: crazy-max/ghaction-import-gpg@v6
  with:
    gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
    passphrase: ${{ secrets.GPG_PASSPHRASE }}
    git_user_signingkey: true
    git_commit_gpgsign: true
```

---

## 라이선스

MIT License — 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
