# NME Project

## STEP 42: 개발 실행 안정성 개선

이 프로젝트는 Windows 개발 환경에서 Backend와 Frontend를 쉽게 실행할 수 있도록 최소 실행 스크립트를 제공합니다.

STEP 42의 목적은 기능 변경이 아니라, 개발자가 매번 수동으로 Uvicorn과 npm 명령을 입력하지 않아도 NME를 안전하게 실행할 수 있게 만드는 것입니다.

## 1. 프로젝트 구조

- Backend: `nme_backend`
- Frontend: `nme_frontend`
- Backend Python virtual environment: `nme_backend/.venv`
- Backend entrypoint: `nme_backend/app/main.py`
- Frontend package: `nme_frontend/package.json`
- Backend URL: <http://127.0.0.1:8000>
- Frontend URL: <http://127.0.0.1:5173>

## 2. Backend 실행 방법

1. Command Prompt 또는 PowerShell에서 프로젝트 루트로 이동합니다.
2. 아래 명령을 실행합니다.

```bat
start_nme.bat
```

기본 동작:

- Backend가 없으면 자동으로 `nme_backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` 를 실행합니다.
- Backend가 없으면 자동으로 `nme_backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers` 를 실행합니다.
- Backend가 이미 정상 실행 중이면 다시 실행하지 않습니다.
- Frontend를 이어서 실행합니다.

직접 실행하고 싶다면:

```bat
cd nme_backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

## 3. Backend 정지 방법

```bat
stop_backend.bat
```

이 스크립트는 포트 8000을 점유한 NME Backend 프로세스만 종료합니다.
다른 Python 프로세스는 종료하지 않습니다.

## 4. Frontend 실행 방법

기존 구조를 그대로 유지하므로, Frontend는 다음 명령으로 실행합니다.

```bat
cd nme_frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

브라우저에서 다음 주소를 엽니다.

- <http://127.0.0.1:5173/>

## 5. 통합 실행 방법

프로젝트 루트에서 아래를 실행하면 Backend와 Frontend를 한 번에 시작할 수 있습니다.

```bat
start_nme.bat
```

실행 순서:

1. Backend 상태 확인
2. Backend가 없으면 시작
3. Backend health 확인
4. Frontend 시작
5. 브라우저로 접속 가능 상태 유지

## 6. Health check 방법

브라우저에서 아래를 확인할 수 있습니다.

- <http://127.0.0.1:8000/health>

정상 응답은 다음과 같습니다.

```json
{"status":"ok"}
```

PowerShell에서도 확인 가능합니다.

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

## 7. Swagger 주소

```text
http://127.0.0.1:8000/docs
```

## 8. Market API 확인 방법

```text
http://127.0.0.1:8000/market
```

정상적으로 실행되면 Product 데이터 배열이 반환됩니다.

## 9. Windows 환경에서 주의할 점

- .venv가 있는 환경만 사용합니다.
- 전역 Python 또는 전역 uvicorn에 의존하지 않습니다.
- 포트 8000이 이미 사용 중이면 해당 프로세스를 먼저 확인합니다.
- 다른 프로세스가 사용 중이면 무조건 종료하지 않습니다.
- DB를 삭제하거나 초기화하지 않습니다.
- JWT, AuthSession, API 구조는 STEP 42에서 변경하지 않습니다.

## 10. Backend가 실행되지 않았을 때 나타날 수 있는 Frontend 오류

Backend가 실행되지 않은 상태에서 Frontend를 실행하면 다음과 같은 문제가 발생할 수 있습니다.

- Market data를 불러오지 못했습니다.
- 현재 사용자 정보를 불러오지 못했습니다.
- 서버와 통신할 수 없습니다.
- 개발용 기본 사용자로 계속하는 것이 보일 수 있습니다.

이 문제를 막기 위해 STEP 42에서는 Backend가 먼저 준비된 상태에서 Frontend를 실행하도록 스크립트를 구성했습니다.

## 11. 보존 범위

이번 STEP 42는 아래 항목을 절대 변경하지 않습니다.

- User, Deal, Order, Product, AuthSession 모델
- JWT 구조와 토큰 로테이션
- refresh, revoke, logout, session 관리
- /auth/login, /auth/me, /auth/refresh 등 인증 API
- /market, 거래 API, 주문 API
- App.jsx의 인증 로직
- SQLite 데이터

이 단계는 오직 실행 편의성 개선만 수행합니다.

## 12. 개발자용 빠른 시작

1. 프로젝트 루트에서 `start_nme.bat` 실행
2. 브라우저에서 <http://127.0.0.1:5173/> 접속
3. Backend 확인: <http://127.0.0.1:8000/health>
4. Swagger 확인: <http://127.0.0.1:8000/docs>
5. 필요할 때 `stop_backend.bat` 실행

## 13. 참고

- Backend 실행 명령: `nme_backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers`
- Frontend 실행 명령: `npm run dev -- --host 0.0.0.0 --port 5173`
- 기존 데이터는 유지하며, 실행 스크립트만으로 작업 환경을 쉽게 제어합니다.

## STEP 43: 최소 운영 보안 보강

STEP 43의 목적은 NME MVP를 깨뜨리지 않으면서 최소한의 운영 보안 경계를 추가하는 것입니다.

### 1. Rate Limiting

- 적용 대상: `POST /auth/login`, `POST /auth/refresh`
- 기본 window: 60초
- `POST /auth/login`: 동일 IP 기준 60초당 10회
- `POST /auth/refresh`: 동일 IP 기준 60초당 30회
- 제한 초과 시: HTTP 429
- 응답 헤더: `Retry-After`

환경변수:

- `AUTH_RATE_LIMIT_WINDOW_SECONDS=60`
- `AUTH_LOGIN_RATE_LIMIT=10`
- `AUTH_REFRESH_RATE_LIMIT=30`

중요:

- 현재 구현은 메모리 기반입니다.
- 서버를 재시작하면 rate limit 상태는 초기화됩니다.
- 향후 운영 확장 시 Redis 기반 분산 rate limit으로 교체할 수 있습니다.

### 2. Security Headers

모든 HTTP 응답에 아래 최소 보안 헤더를 추가합니다.

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`

이번 단계에서는 로컬 HTTP 개발환경을 유지하기 위해 HSTS는 적용하지 않았습니다.
또한 Frontend/Vite 동작을 깨뜨릴 수 있으므로 CSP는 강제로 추가하지 않았습니다.

### 3. CORS 정책

현재 허용 origin은 실제 개발 환경에 필요한 최소 범위만 유지합니다.

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174` - 로컬에서 BUYER/SELLER 화면을 병렬 검증할 때 사용 가능
- `http://127.0.0.1:8000`

주의:

- `allow_credentials=True` 상태에서 `allow_origins=["*"]` 는 사용하지 않습니다.
- 허용되지 않은 origin은 `Access-Control-Allow-Origin` 헤더를 받지 못합니다.

### 4. 테스트 결과 요약

- `GET /health`: 200 OK
- `GET /market`: 기존 Product 데이터 정상 반환
- Security headers 확인 완료
- 허용 origin CORS 확인 완료
- 비허용 origin 미허용 확인 완료
- BUYER login/me/refresh/logout 정상
- SELLER login/me/refresh/logout 정상
- refresh rotation 재사용 401 유지
- session ownership 404 유지
- cleanup 일반 사용자 403 유지
- cleanup admin 200 유지
- rate limit 429 동작 확인 완료
- `npm run build` 성공

### 5. DB 무결성

- STEP 43은 DB schema를 변경하지 않습니다.
- User, Deal, Order, Product, AuthSession 모델은 변경하지 않습니다.
- 거래/주문/상품 데이터는 변경하지 않습니다.
- 인증 회귀 테스트 과정에서 `auth_sessions` 수는 증가할 수 있습니다.
- 증가 원인은 login/refresh 검증으로 생성된 세션이며, 스크립트가 DB를 직접 수정한 것은 아닙니다.

### 6. 다음 확장 방향

향후 실제 운영 환경으로 확장할 때는 다음을 고려할 수 있습니다.

- Redis 기반 rate limit 저장소
- reverse proxy 기준 실제 client IP 처리
- CSP 정책 정교화
- HTTPS 환경에서 HSTS 적용

## STEP 44: 운영 보안 경계 정리

STEP 44의 목적은 로컬 개발 환경을 깨뜨리지 않으면서 운영 보안 개념을 환경별로 분리하는 것입니다.

### 1. Rate Limit client IP 정책

- 기본 client identifier는 `request.client.host` 입니다.
- 현재 로컬 개발 환경에서는 reverse proxy가 없으므로 `X-Forwarded-For`, `X-Real-IP` 를 기본적으로 신뢰하지 않습니다.
- 실행 명령에는 `--no-proxy-headers` 를 사용해 Uvicorn이 spoofed forwarded header를 client IP로 승격하지 않도록 했습니다.

### 2. Reverse Proxy 신뢰 정책

- 기본값: `TRUST_PROXY_HEADERS=false`
- 기본값: `TRUSTED_PROXY_IPS=`
- production에서 reverse proxy를 실제로 둘 때만 `TRUST_PROXY_HEADERS=true` 로 바꾸고, `TRUSTED_PROXY_IPS` 에 신뢰할 proxy IP만 명시해야 합니다.
- 이 설정이 꺼져 있으면 앱은 forwarded header를 무시하고 직접 접속한 client IP를 사용합니다.

### 3. Development / Production 보안 경계

환경변수:

- `APP_ENV=development`
- `DEV_CORS_ALLOW_ORIGINS=...`
- `PROD_CORS_ALLOW_ORIGINS=`
- `SECURITY_ENABLE_CSP=true`
- `SECURITY_ENABLE_HSTS=true`
- `SECURITY_HSTS_MAX_AGE_SECONDS=31536000`

development:

- localhost CORS 유지
- HTTP 개발 환경 유지
- CSP 강제 적용 안 함
- HSTS 적용 안 함

production:

- production CORS allowlist만 사용
- HTML 응답에 CSP 적용 가능
- HTTPS 요청에만 HSTS 적용 가능

### 4. Security Headers

현재 확인된 헤더:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), geolocation=(), microphone=()`

### 5. CSP 정책

development:

- Vite HMR과 로컬 개발 동작을 깨뜨리지 않기 위해 CSP를 적용하지 않습니다.

production:

- HTML 응답에만 CSP를 적용합니다.
- 기본 정책은 self 기반이며 Swagger UI가 사용하는 jsDelivr 자산과 inline script/style 을 허용하는 최소 정책입니다.
- 필요하면 `PRODUCTION_CONTENT_SECURITY_POLICY` 로 명시적으로 덮어쓸 수 있습니다.

### 6. HSTS 정책

development:

- localhost HTTP 환경이므로 HSTS를 적용하지 않습니다.

production:

- `APP_ENV=production` 이고 HTTPS 요청일 때만 `Strict-Transport-Security` 를 적용합니다.
- HTTP 개발 환경에서는 절대 강제하지 않습니다.

### 7. CORS 정책

현재 development 허용 origin:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174`
- `http://127.0.0.1:8000`

차단 확인:

- `http://evil.example.com` 은 `Access-Control-Allow-Origin` 헤더를 받지 못합니다.

### 8. JWT 정책 유지

- JWT algorithm, payload 구조, access token, refresh token, `sid`, `type`, `sub` 검증은 변경하지 않았습니다.
- refresh rotation, logout revoke, session revoke, revoke-all 도 그대로 유지합니다.

### 9. DB 변경 여부

- User, Deal, Order, Product 테이블 수는 변경하지 않았습니다.
- STEP 44 검증 중 login/refresh/logout 으로 인해 `auth_sessions` 수는 증가할 수 있습니다.
- DB 초기화, migration, cleanup 실행을 통한 데이터 정리는 하지 않았습니다.

### 10. 인증 회귀 테스트 결과

- BUYER login/me/sessions/refresh/logout 정상
- BUYER logout 후 refresh 401 정상
- SELLER login/me/sessions/refresh 정상
- ADMIN cleanup 200 정상
- BUYER cleanup 403 정상
- 타 사용자 session revoke 404 정상

### 11. Frontend build 결과

- `npm run build` 성공

### 12. Browser 검증 결과

- 현재 환경에서는 backend access log와 frontend dev server 로그를 통해 API 흐름을 확인했습니다.
- 공유된 브라우저 페이지가 없는 상태여서 Browser Console은 직접 수집하지 않았습니다.
- 다만 이번 단계에서 frontend 코드는 수정하지 않았고, `/market`, `/docs`, `/openapi.json` 및 인증 API는 정상 응답을 확인했습니다.

### 13. 발생한 오류와 해결 방법

- 초기 STEP 44 점검에서 spoofed `X-Forwarded-For` 값이 rate limit을 우회했습니다.
- 원인은 Uvicorn이 기본 proxy header 처리로 localhost 요청의 forwarded 값을 client IP로 반영하고 있었기 때문입니다.
- 해결: app 내부에서는 proxy header를 기본 불신으로 유지하고, 실행 명령에 `--no-proxy-headers` 를 추가해 로컬 개발 환경에서 spoofing을 차단했습니다.

### 14. STEP 45 준비 상태

- 준비됨
- 다음 단계에서는 실제 reverse proxy 환경을 둘 때의 trusted proxy 운영 절차나 Redis 기반 분산 rate limit 같은 확장 사항을 검토할 수 있습니다.

## STEP 45: Frontend ↔ Backend 연결 복구

STEP 45의 목적은 새로운 기능을 추가하는 것이 아니라, 실제 Vite 개발 서버가 `http://localhost:5174/` 에서 열렸을 때 Frontend가 Backend API에 정상 연결되도록 복구하는 것입니다.

### 1. 문제 원인

- Frontend의 API base 자체는 이미 `http://127.0.0.1:8000` 으로 올바르게 설정되어 있었습니다.
- Backend의 `/health`, `/market` 도 정상 응답하고 있었습니다.
- 실제 실패 원인은 development CORS allowlist에 `http://localhost:5174` 가 빠져 있었던 점입니다.
- 기존 allowlist에는 `http://127.0.0.1:5174` 만 있었기 때문에, 브라우저 origin이 `http://localhost:5174` 일 때 `/market`, `/auth/me` 요청이 차단될 수 있었습니다.

### 2. 수정 내용

- development CORS allowlist에 `http://localhost:5174` 를 추가했습니다.
- `.env` 의 `DEV_CORS_ALLOW_ORIGINS` 와 backend 기본 development fallback 양쪽을 동일하게 맞췄습니다.
- Frontend 코드, JWT 구조, 거래 API, DB schema는 변경하지 않았습니다.

### 3. 확인 결과

- `GET /health` : 200
- `GET /market` : 200, 상품 4건 반환
- Origin `http://localhost:5174` 요청 시 `Access-Control-Allow-Origin: http://localhost:5174` 확인
- BUYER login, `/auth/me`, `/auth/sessions`, `/market` 재검증 정상
- frontend build 성공

### 4. 주의 사항

- Vite가 5173 대신 5174로 자동 변경되는 것은 정상 동작일 수 있습니다.
- 이 경우 backend CORS는 `127.0.0.1` 과 `localhost` 를 각각 별도 origin으로 취급하므로 둘 다 허용해야 합니다.

## STEP 46: 개발환경 실행 표준화 및 환경변수 정리

STEP 46의 목적은 기능 추가가 아니라, NME 개발환경을 동일한 규칙으로 실행하고 점검하도록 기준을 고정하는 것입니다.

### 1. 표준 실행 기준

- Backend 표준 주소: `http://127.0.0.1:8000`
- Frontend 표준 시작 포트: `5173` (점유 시 Vite가 `5174`로 자동 전환 가능)
- Backend 실행 정책: `--no-proxy-headers` 유지
- Frontend API base: `VITE_API_URL` 미설정 시 `http://127.0.0.1:8000`

### 2. 표준 실행 방법 (Windows)

통합 실행(권장):

```bat
start_nme.bat
```

개별 실행:

```bat
cd nme_backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```bat
cd nme_frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

정지:

```bat
stop_backend.bat
```

### 3. 디렉터리/명령 규칙

- Python 관련 명령은 `nme_backend`에서 실행
- npm 관련 명령은 `nme_frontend`에서 실행
- 프로젝트 루트에서 `npm run ...` 실행 금지 (`package.json` 없음으로 실패)

### 4. 환경변수 기준

- `APP_ENV=development`
- `TRUST_PROXY_HEADERS=false`
- `DEV_CORS_ALLOW_ORIGINS`에는 아래 origin을 모두 포함
	- `http://localhost:5173`
	- `http://localhost:5174`
	- `http://127.0.0.1:5173`
	- `http://127.0.0.1:5174`
	- `http://127.0.0.1:8000`

주의:

- `localhost`와 `127.0.0.1`은 브라우저에서 서로 다른 origin입니다.
- 둘 중 하나만 허용하면 CORS 오류가 재발할 수 있습니다.

### 5. STEP 46 점검 결과 (실측)

아래 결과는 로컬 개발환경에서 실제 호출/빌드로 확인한 값입니다.

1. Backend 포트 8000 LISTEN: 확인됨
2. Backend 프로세스 명령행에 `--no-proxy-headers` 포함: 확인됨
3. `GET /health`: 200
4. `GET /market`: 200
5. `/market` 상품 수: 4
6. `GET /docs`: 200
7. `GET /openapi.json`: 200
8. Origin `http://localhost:5174` CORS 허용: 확인됨
9. Origin `http://127.0.0.1:5174` CORS 허용: 확인됨
10. Origin `http://evil.example.com` CORS 비허용(ACAO 미반환): 확인됨
11. `GET /users/2`: 200
12. `GET /deals`: 200
13. BUYER login: 200
14. BUYER `GET /auth/me`: 200
15. BUYER `GET /auth/sessions`: 200
16. BUYER refresh: 200
17. SELLER login: 200
18. SELLER `GET /auth/me`: 200
19. SELLER refresh: 200
20. 세션 ownership 보호(타 사용자 revoke): 404 유지
21. ADMIN `POST /auth/sessions/cleanup`: 200
22. Frontend production build (`npm run build`): 성공
23. DB 핵심 테이블 개수(users/deals/orders/products): 전후 동일
24. 인증 점검으로 `auth_sessions` 증가 가능성: 실제 증가 확인(정상)

### 6. DB 전후 스냅샷

- 점검 전: users 8, deals 20, orders 14, products 4, auth_sessions 64
- 점검 후: users 8, deals 20, orders 14, products 4, auth_sessions 69

해석:

- 비즈니스 데이터(users/deals/orders/products)는 변동 없음
- `auth_sessions` 증가는 login/refresh 검증 트래픽에 의한 정상 증가

### 7. 보존 확인

- 신규 기능 추가 없음
- DB schema 변경 없음
- JWT/세션 계약 변경 없음
- 기존 거래/주문/마켓 API 계약 변경 없음

## STEP 47: NME 전체 거래 흐름 End-to-End 실측 검증

### 1. 목적

- STEP 47의 목적은 신규 기능 추가가 아니라, 기존 구현(Frontend + Backend)이 실제 거래 흐름에서 끝까지 연결되는지 실측으로 증명하는 것입니다.

### 2. 실행 환경

- OS: Windows
- Backend 실행 재사용 확인: `127.0.0.1:8000` LISTEN 프로세스 재사용
- Backend 프로세스 명령행 확인:
	- `...python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers`
- Frontend 실행 위치: `nme_frontend` (`package.json` 확인)
- Frontend 실제 브라우저 Origin: `http://localhost:5174/`

### 3. Backend/Frontend 표준 확인

- Backend URL: `http://127.0.0.1:8000`
- Health: `GET /health` -> 200
- Swagger: `GET /docs` -> 200
- OpenAPI: `GET /openapi.json` -> 200
- Frontend build: `npm run build` 성공

### 4. 실제 엔드포인트 확인 결과

아래는 코드 기준으로 존재를 확인한 엔드포인트입니다.

- Auth: `/auth/login`, `/auth/me`, `/auth/sessions`, `/auth/refresh`, `/auth/logout`
- Market: `/market`
- Deal: `/deals`, `/deals/{id}`, `/deals/{id}/status`, `/deals/{id}/create-order`, `/deals/{id}/order`, `/deals/{id}/completion`
- Order: `/orders`, `/orders/{id}`, `/orders/{id}/status`
- User: `/users/{id}`

주의:

- Completion endpoint는 `POST`가 아니라 `GET /deals/{id}/completion` 입니다.
- History 전용 별도 backend endpoint는 없고, Frontend는 `/deals` + `/deals/{id}/order` + `/deals/{id}/completion` 조합으로 이력을 구성합니다.
- Dashboard도 Frontend 계산이며, 데이터 소스는 `/users/{id}`, `/market`, `/deals` 입니다.

### 5. BUYER 인증 검증

- 계정: `bob@example.com / secret`
- `POST /auth/login` -> 200
	- `access_token` 존재
	- `refresh_token` 존재
- `GET /auth/me` -> 200
- `GET /auth/sessions` -> 200
- `POST /auth/refresh` -> 200

### 6. SELLER 인증 검증

- 계정: `charlie@example.com / secret`
- `POST /auth/login` -> 200
	- `access_token` 존재
	- `refresh_token` 존재
- `GET /auth/me` -> 200
- `GET /auth/sessions` -> 200
- `POST /auth/refresh` -> 200

### 7. Session Isolation 최소 검증

- SELLER 토큰으로 BUYER 세션 revoke 시도:
	- `POST /auth/sessions/{buyer_session_id}/revoke` -> 404
- 기존 ownership 차단 동작 유지 확인.

### 8. FLOW A/B 실측 결과

실측 1건 기준:

- Market 조회: `GET /market` -> 200
- 선택 상품: `product_id=4` (Aluminum, A1050, status=available)
- Deal 생성: `POST /deals` -> 200
	- 생성 `deal_id=23`
	- payload: `product_id=4, buyer_id=2, quantity=1, proposed_price=3200237`
- Deal 승인: `PATCH /deals/23/status` with `AGREED` -> 200
- Order 생성: `POST /deals/23/create-order` -> 200
	- 생성 `order_id=16`
- Order 상태 전이:
	- `PATCH /orders/16/status` -> `ACCEPTED` (200)
	- `PATCH /orders/16/status` -> `PAID` (200)
	- `PATCH /orders/16/status` -> `SHIPPED` (200)
	- `PATCH /orders/16/status` -> `COMPLETED` (200)
- Completion 조회:
	- `GET /deals/23/completion` -> 200
	- `completed=true`, `status=COMPLETED`

### 9. History / Dashboard 검증

- Backend 소스 확인:
	- `GET /deals` -> 200
	- `GET /deals/23/order` -> 200
	- `GET /deals/23/completion` -> 200
	- `GET /users/2` -> 200
	- `GET /users/3` -> 200

- Frontend 브라우저 실측:
	- BUYER 상태에서 Market 카드/사용자 표시 확인
	- SELLER 로그인 후 `거래 이력 > 전체 거래`에서 검색 `23` 적용
	- `Deal #23`, `Order #16`, `거래 완료` 표시 확인
	- SELLER Dashboard 카드(전체/진행중/완료/주문 생성 전/판매자가 해야 할 일) 표시 확인

### 10. 거래 상태 일관성

생성 거래(`deal_id=23`) 기준:

- Deal status: `AGREED`
- Order status: `COMPLETED`
- Completion API: `completed=true`
- Product status(선택 상품): `available`

현재 스키마 특성:

- `orders` 테이블에 `deal_id` FK가 없고, backend는 `(product_id, buyer_id, quantity, price)` 매칭으로 Deal-Order를 연결합니다.
- 본 검증에서 해당 필드 매칭 결과는 `order_id=16`으로 일치했습니다.

### 11. DB 사전/사후 스냅샷

작업 전:

- users = 8
- products = 4
- deals = 22
- orders = 15
- auth_sessions = 77

작업 후:

- users = 8
- products = 4
- deals = 23
- orders = 16
- auth_sessions = 81

보조 분포(사후):

- products_by_status: `available=4`
- deals_by_status: `AGREED=19, NEGOTIATING=2, REJECTED=2`
- orders_by_status: `COMPLETED=10` 포함

### 12. DB 변경 해석

- deals +1: STEP 47 실측용 거래 1건 생성
- orders +1: 해당 거래에서 주문 1건 생성
- auth_sessions +4: BUYER/SELLER login + refresh 검증으로 증가
- users/products 변경 없음: 데이터 보호 원칙 유지

### 13. Browser 검증 결과

실제 확인한 항목:

- 로그인 화면 정상 노출
- BUYER 로그인/SELLER 로그인 정상
- Market 화면에서 NME Live Market 및 상품 카드 표시
- History 화면에서 거래 카드 및 상세 정보 표시
- SELLER 전체 거래 검색에서 `Deal #23`와 완료 상태 표시

### 14. Browser Console

- 직접 확인하지 못함

### 15. Backend access log

- Uvicorn 프로세스 실행/옵션(`--no-proxy-headers`)은 확인했습니다.
- 다만 실행 중 서버 터미널의 access log 라인 자체는 직접 수집하지 못했습니다.
- 대신 동일 요청에 대한 실제 HTTP 응답 코드는 본 문서의 엔드포인트별 실측 결과로 기록했습니다.

### 16. npm run build

- `nme_frontend`에서 실행
- 결과: 성공 (`vite build` 완료)

### 17. 발견된 오류와 처리

- 검증 스크립트 초기 버전에서 `/docs` HTML을 JSON으로 파싱해 실패
	- 조치: content-type 기반 파서로 보정
- 검증 스크립트에서 `deals.seller_id`를 가정하여 실패
	- 조치: 실제 스키마(`Deal`에 seller_id 없음) 기준으로 보정
- 첫 주문 생성 시 기존 중복 방지 규칙과 충돌
	- 조치: 제안가에 최소 오프셋을 적용해 고유 조합 1건만 생성

### 18. 수정 파일

- `README.md` (STEP 47 결과 문서화)

### 19. 기존 기능 보존 여부

- JWT 구조: 보존
- endpoint 이름/HTTP method: 보존
- request/response schema: 보존
- authentication flow(login/me/refresh/sessions): 보존
- session ownership: 보존(404 차단 유지)
- rate limiting/CORS/security headers/CSP/HSTS/proxy header 정책: 코드 변경 없음
- User/Product/Deal/Order/AuthSession 모델: 코드 변경 없음

### 20. STEP 48 후보 (구현하지 않음)

- Deal-Order 관계를 명시 FK로 모델링할지 검토(현행 필드 매칭 방식의 운영 리스크 분석)
- History/Dashboard 전용 집계 endpoint 분리 여부 검토(Frontend 조합 비용 감소)
- E2E 회귀 시나리오를 스크립트/테스트 케이스로 고정해 반복 검증 자동화

## STEP 48: MVP E2E 회귀 테스트 자동화

### 1. 목적

- STEP 47에서 사람이 확인한 핵심 거래 흐름을 pytest 기반 자동 회귀 테스트로 고정했습니다.

### 2. 테스트 환경

- 테스트 파일: `nme_backend/tests/test_e2e_trade_flow.py`
- pytest 설정: `nme_backend/pytest.ini`
- 실행 명령: `cd nme_backend && .\.venv\Scripts\python.exe -m pytest -q`
- 테스트 DB: 실제 `nme.db`가 아닌 임시 SQLite 파일(`nme_test.db`) 사용
- DB 분리 방식: `DATABASE_URL`을 테스트 전용 SQLite 경로로 오버라이드

### 3. 테스트 시나리오

- `GET /health`
- `GET /market`
- BUYER login / `GET /auth/me` / `GET /auth/sessions`
- SELLER login / `GET /auth/me`
- `POST /deals`
- `PATCH /deals/{id}/status` with `AGREED`
- `POST /deals/{id}/create-order`
- `PATCH /orders/{id}/status` until `COMPLETED`
- `GET /deals/{id}/completion`
- `GET /deals`
- `GET /deals/{id}/order`
- `GET /users/{id}`
- 보안 회귀: rate limit, session ownership, CORS 헤더

### 4. 테스트 결과

- `python -m pytest -q`: `3 passed`
- 경고: `jose.jwt`의 UTC deprecation warning만 출력됨
- 핵심 거래 흐름 자동 테스트 통과
- 인증 회귀 통과
- Completion 통과
- History 데이터 확인 통과
- Dashboard 데이터 확인 통과

### 5. DB 보호 결과

- 실제 개발 DB `nme.db` 변경 없음
- 테스트는 전용 temp SQLite DB에서만 수행
- 기존 거래/사용자/상품 데이터 삭제 없음

### 6. Browser 검증 결과

- 실제 브라우저 화면은 STEP 47에서 수동 확인 완료
- STEP 48에서는 browser console을 직접 확인하지 못함

### 7. 수정한 파일

- `nme_backend/app/main.py`
- `nme_backend/tests/test_e2e_trade_flow.py`

## STEP 52: 개발환경 실행 표준화 및 Local Startup 안정화

STEP 52에서는 프로젝트 루트에서 동일한 명령으로 Backend와 Frontend를 안정적으로 시작하도록 표준을 고정했습니다.

### 표준 실행 경로

- 프로젝트 루트: `start_nme.bat`
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

### 표준 실행 명령

Backend:

```bat
cd nme_backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-proxy-headers
```

Frontend:

```bat
cd nme_frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### 포트 정책

- 8000에서 이미 NME backend가 health 응답을 주면 재사용합니다.
- 5173에서 이미 NME frontend가 서빙 중이면 재사용합니다.
- 다른 프로세스가 8000 또는 5173을 점유하면 재시작으로 덮어쓰지 않고 오류를 표시합니다.
- `localhost`와 `127.0.0.1`은 별도 origin이므로 CORS allowlist에서 함께 유지합니다.

### 점검 명령

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/market -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8000/openapi.json -UseBasicParsing
```

### 검증 결과

- Browser smoke와 Browser trade lifecycle E2E는 STEP 51 기준으로 유지됩니다.
- Full pytest는 `10 passed` 기준을 유지합니다.
- Frontend build는 `npm run build` 성공 기준을 유지합니다.
- 실개발 DB `nme.db`는 초기화하지 않습니다.

## STEP 53: NME Local Development Startup 검증 자동화 및 개발환경 진단 체계 고정

STEP 53의 목적은 기능 추가가 아니라, STEP 52에서 고정한 실행 표준을 기준으로 개발환경 상태를 한 번에 진단하는 체계를 마련하는 것입니다.

### 1) START와 CHECK 역할 분리

- START: `start_nme.bat`
- CHECK: `check_nme.bat`

개발자는 아래 순서만 사용하면 됩니다.

1. `start_nme.bat`
2. `check_nme.bat`

### 2) 진단 실행 방법

프로젝트 루트에서 실행:

```bat
check_nme.bat
```

`check_nme.bat`는 내부적으로 `check_nme.ps1`을 실행하며 아래 항목을 자동 점검합니다.

1. Python 존재 여부
2. Backend `.venv` 존재 여부
3. Node 존재 여부
4. npm 존재 여부
5. Backend 디렉터리/핵심 파일 존재 여부
6. Frontend 디렉터리/핵심 파일 존재 여부
7. 8000 포트 상태(비어있음/재사용/충돌/서비스 오류)
8. 5173 포트 상태(비어있음/재사용/충돌/서비스 오류)
9. `/health`
10. `/market`
11. `/docs`
12. `/openapi.json`
13. Frontend `http://127.0.0.1:5173/` 응답
14. `VITE_API_URL` 정책 일치 여부
15. CORS 정책(allowlist + 런타임 헤더)
16. 실제 `nme_backend/nme.db` 존재 여부
17. 읽기 전용 DB count 확인(users/products/deals/orders/auth_sessions)
18. `pytest.ini` 기준 확인
19. browser test 파일 존재 여부
20. 최종 READY/NOT READY 판정

### 3) 표준 URL 및 정책

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`
- Frontend API 표준: `VITE_API_URL=http://127.0.0.1:8000`
- CORS 표준: `DEV_CORS_ALLOW_ORIGINS`에 `http://127.0.0.1:5173` 포함, `*` 금지, `http://evil.example.com` 비허용

### 4) 포트 진단 의미

- `NOT RUNNING`: 포트가 비어 있고 서비스 미기동
- `RUNNING/REUSE`: 표준 서비스가 정상 응답하여 재사용 가능
- `CONFLICT`: 다른 프로세스가 포트 점유
- `SERVICE ERROR`: 포트는 열려 있으나 기대 응답 실패

### 5) 정상 결과 예시

- `/health`, `/market`, `/docs`, `/openapi.json` 모두 `HTTP 200`
- Frontend `HTTP 200`
- `VITE_API_URL` 정책 PASS
- CORS 정책 PASS
- Final status: `READY`

### 6) 오류 상황 의미

- `Port 8000 is free`: Backend 미기동
- `CONFLICT - ... port 8000`: 다른 프로그램 점유
- `Frontend API URL mismatch`: Frontend가 표준 backend를 바라보지 않음
- `CORS runtime response mismatch`: backend 미기동 또는 CORS 응답 불일치

### 7) 회귀 검증 명령

Browser E2E:

```bat
cd nme_backend
python -m pytest -q tests/browser -m browser
```

전체 pytest:

```bat
cd nme_backend
python -m pytest -q
```

Frontend build:

```bat
cd nme_frontend
npm run build
```

### 8) DB 보호 정책

- STEP 53 진단은 `nme.db`를 읽기만 합니다.
- DB 삭제/초기화/seed/migration reset/cleanup을 수행하지 않습니다.
- 기존 API contract, DB schema, JWT 구조, Browser E2E business flow를 변경하지 않습니다.

## STEP 54: NME Quality Gate / 통합 사전검증 자동화

STEP 54의 목적은 비즈니스 기능 추가가 아니라, START/CHECK를 바탕으로 VERIFY를 추가해 개발자가 한 번에 품질 상태를 판정할 수 있도록 만드는 것입니다.

### 1) START / CHECK / VERIFY 역할

- START: `start_nme.bat`
	- Backend/Frontend 시작 또는 재사용
- CHECK: `check_nme.bat`
	- 개발환경 상태 진단(READY/NOT READY)
- VERIFY: `verify_nme.bat`
	- 전체 품질 게이트 실행(PASS/FAIL)

### 2) Quality Gate 실행 방법

프로젝트 루트에서 실행:

```bat
verify_nme.bat
```

`verify_nme.bat`는 내부적으로 `verify_nme.ps1`을 실행하고 아래 순서로 검증합니다.

1. `check_nme.bat` 실행
2. CHECK 실패 시 `start_nme.bat` 1회 실행 후 CHECK 재시도
3. Backend/Frontend + API 200 확인
4. CORS 확인(허용 origin/evil origin)
5. `nme.db` 읽기 전용 pre-count
6. `python -m pytest -q`
7. `python -m pytest -q tests/browser -m browser`
8. `npm run build`
9. `nme.db` 읽기 전용 post-count
10. 최종 `NME QUALITY GATE: PASS` 또는 `NME QUALITY GATE: FAIL`

### 3) 표준 URL

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:5173`

### 4) API 점검 항목

- `GET /health`
- `GET /market`
- `GET /docs`
- `GET /openapi.json`

모든 항목이 HTTP 200이어야 합니다.

### 5) CORS 정책

- 허용 origin 기준: `http://127.0.0.1:5173`
- 차단 origin 기준: `http://evil.example.com`
- CORS wildcard `*` 금지

### 6) 테스트/빌드 명령

전체 pytest:

```bat
cd nme_backend
python -m pytest -q
```

Browser pytest:

```bat
cd nme_backend
python -m pytest -q tests/browser -m browser
```

Frontend build:

```bat
cd nme_frontend
npm run build
```

### 7) DB 보호 및 테스트 DB isolation

- `verify_nme.bat`는 실제 `nme_backend/nme.db`를 읽기 전용으로만 조회합니다.
- 핵심 테이블(users/products/deals/orders) count 변동 시 FAIL 처리합니다.
- Browser/pytest는 기존 테스트 DB isolation 구조를 유지합니다.

### 8) Quality Gate 판정 기준

PASS 조건:

- environment PASS
- Backend/Frontend PASS
- `/health`, `/market`, `/docs`, `/openapi.json` 200
- CORS PASS
- pytest PASS
- browser PASS
- npm build PASS
- 실제 `nme.db` 핵심 count 불변
- API contract/JWT/DB schema 변경 없음

하나라도 실패하면 FAIL로 중단하고 아래 형식으로 원인을 표시합니다.

```text
[FAIL]
Item:
Cause:
Related file:
Recommended action:
```

### 9) STEP 54 실측 결과

- `verify_nme.bat` 실행 결과: `NME QUALITY GATE: PASS`
- full pytest: `10 passed, 47 warnings`
- browser pytest: `2 passed`
- frontend build: PASS
- `nme.db` pre/post count 동일
	- users 8
	- products 4
	- deals 23
	- orders 16
	- auth_sessions 82

### 10) 오류와 해결

- 초기 구현에서 `verify_nme.ps1` 문자열 인코딩/인용부호로 파서 오류 발생
- 해결: 스크립트를 ASCII 기반으로 재작성하고 batch 호출/frontend 체크 로직을 안정화

### 11) STEP 55 준비 상태

- 준비됨
- 다음 단계에서는 CI pre-flight로 `verify_nme.bat`를 연결해 PR 단위 품질 게이트로 확장할 수 있습니다.

## STEP 55: NME CI Pre-flight 자동 품질검증 구축

STEP 55의 목적은 로컬 START/CHECK/VERIFY 구조를 유지하면서, 같은 품질 기준을 CI에서도 자동으로 검증하도록 연결하는 것입니다.

### 1) CI 플랫폼 판단

- 현재 workspace에는 기존 CI 설정이 없었습니다.
- `.github/workflows`, GitLab CI, 기타 YAML 기반 CI 파일도 존재하지 않았습니다.
- `.git` 디렉터리와 remote 정보도 현재 workspace에서는 확인되지 않았습니다.
- 따라서 기존 CI를 수정하는 대신 GitHub Actions용 최소 workflow를 새로 추가했습니다.

### 2) 추가한 CI workflow

- Workflow: `.github/workflows/nme-ci.yml`
- 이름: `NME CI Preflight`
- Trigger: `push`, `pull_request`
- Runner: `ubuntu-latest`
- Job timeout: `30` minutes

### 3) CI 실행 순서

1. Python 3.13 설정
2. Node 24 설정
3. Backend dependency 설치
4. Frontend dependency 설치 (`npm ci`)
5. Playwright Chromium 설치
6. 실제 repo `nme.db` count 사전 기록(read-only)
7. 격리된 SQLite DB로 API smoke + CORS 검증
8. `python -m pytest -q`
9. `python -m pytest -q tests/browser -m browser`
10. `npm run build`
11. 실제 repo `nme.db` count 사후 비교(read-only)
12. 최종 `NME QUALITY GATE: PASS/FAIL`

### 4) Python / Node 정책

- Python: `3.13`
- Node: `24`
- backend install: `pip install -r requirements.txt`
- browser test 보조 패키지: `pytest==9.1.1`, `pytest-playwright==0.9.0`, `playwright==1.62.0`
- frontend install: `package-lock.json`이 존재하므로 `npm ci` 사용

### 5) Browser E2E와 CI의 관계

- CI는 실제 로컬 `127.0.0.1:8000`, `127.0.0.1:5173` 개발 서버에 의존하지 않습니다.
- browser 테스트는 기존 `tests/browser/conftest.py`의 동적 포트 + 동적 origin + 테스트용 frontend/backend 기동 구조를 그대로 사용합니다.
- workflow가 별도 browser 서버를 중복 실행하지 않습니다.

### 6) API smoke / CORS / DB isolation

- API smoke는 CI 내부에서만 사용하는 임시 SQLite DB `sqlite:///./nme_ci_smoke.db`로 실행됩니다.
- 검증 대상: `/health`, `/market`, `/docs`, `/openapi.json`
- CORS는 `http://127.0.0.1:5173` 허용, `http://evil.example.com` 비허용을 확인합니다.
- 실제 `nme_backend/nme.db`는 read-only count 비교만 수행합니다.

### 7) 로컬 verify_nme와 CI의 관계

- 로컬: `verify_nme.bat` / `verify_nme.ps1`
- CI: GitHub Actions workflow가 동일한 검증 항목을 CI-native 명령으로 실행
- 즉, Windows BAT/PowerShell 로직을 CI에 그대로 이식하지 않고 의미상 동일한 quality gate를 유지합니다.

### 8) PASS / FAIL 정책

CI PASS 조건:

- backend pytest PASS
- browser pytest PASS
- frontend build PASS
- API smoke PASS
- CORS PASS
- DB isolation PASS
- 실제 repo `nme.db` 핵심 count 불변

하나라도 실패하면 workflow 전체가 FAIL이며 마지막 단계에서 `NME QUALITY GATE: FAIL`을 출력합니다.

### 9) STEP 55 실측 범위

현재 workspace에서는 실제 Git hosting/remote/Actions runner 접근이 없어 원격 CI 실행 자체는 확인할 수 없었습니다.

대신 아래를 로컬에서 실측했습니다.

- `verify_nme.bat` -> PASS
- `python -m pytest -q` -> `10 passed, 47 warnings`
- `python -m pytest -q tests/browser -m browser` -> `2 passed`
- `npm run build` -> PASS
- CI와 동일한 isolated smoke backend 조건으로 `/health`, `/market`, `/docs`, `/openapi.json`, CORS 허용/차단 확인 PASS
- 실제 `nme.db` count unchanged

### 10) 실제 nme.db 보호 정책

- CI와 로컬 검증 모두 실제 `nme.db`를 삭제/초기화/seed/migration 하지 않습니다.
- CI smoke는 임시 SQLite DB를 사용합니다.
- browser/pytest의 test DB isolation 구조는 기존 구현을 유지합니다.

## STEP 50 - Browser Smoke and Monitoring

STEP 50에서는 실제 Browser 계층을 Playwright로 연결하고 console / pageerror / requestfailed / HTTP 4xx / HTTP 5xx 감시를 자동화했습니다.

검증 범위:

- 실제 Backend 8000 실행
- 실제 Frontend 5173 실행
- Login 화면 확인
- 기본 사용자 진입 확인
- Market 화면 확인
- History 화면 확인
- Browser Console error = 0
- pageerror = 0
- API requestfailed = 0
- API 4xx/5xx = 0

실행 방법:

```bash
cd nme_backend
python -m pytest -m browser -q
```

또는 전체 회귀:

```bash
cd nme_backend
python -m pytest -q
```

Browser smoke는 테스트 전용 SQLite DB를 사용하는 backend test instance와 연결되도록 구성했습니다. 실개발 DB `nme.db`는 건드리지 않습니다.

## STEP 51 - Browser Trade Lifecycle E2E

STEP 51은 단순 smoke가 아니라 실제 사용자의 거래 전체 라이프사이클을 Browser에서 자동 검증하는 단계입니다.

구조:

```text
Browser
  ├── BUYER context
  │    └── BUYER session
  └── SELLER context
	  └── SELLER session
	↓
Frontend dev server
	↓
FastAPI test instance
	↓
Test SQLite DB
```

검증 흐름:

1. BUYER login
2. Market 확인
3. Deal 생성
4. SELLER login
5. SELLER history에서 Deal 확인
6. SELLER가 Deal 승인
7. BUYER가 Deal refresh 후 Order 생성
8. BUYER가 Order를 COMPLETED까지 진행
9. Completion 확인
10. History 확인
11. Dashboard 확인

Browser monitoring:

- console error 수집
- pageerror 수집
- requestfailed 수집
- HTTP 4xx/5xx 수집

실행 방법:

```bash
cd nme_backend
python -m pytest tests/browser -m browser -q
```

```bash
cd nme_backend
python -m pytest -m browser -q
```

```bash
cd nme_backend
python -m pytest -q
```

Frontend build:

```bash
cd nme_frontend
npm run build
```

API contract / DB 보존:

- DB schema 변경 없음
- User/Product/Deal/Order/AuthSession model 변경 없음
- JWT 구조 변경 없음
- refresh rotation / logout / revoke / revoke-all / session ownership / rate limit / CORS 보존
- 실제 `nme.db` 직접 mutation 없음

검증 결과:

- `python -m pytest -q tests/browser -m browser` -> `2 passed`
- `python -m pytest -q` -> `10 passed`
- `npm run build` -> 성공
- 실제 `nme.db` counts: users 8, products 4, deals 23, orders 16, auth_sessions 82

Browser error policy:

- Browser smoke는 console error = 0, pageerror = 0, requestfailed = 0, unexpected 4xx/5xx = 0 기준으로 유지합니다.
- STEP 51 trade flow는 `GET /deals/{id}/order` 의 의도된 404를 허용하고, 그 외 브라우저/API 오류는 실패로 처리합니다.
- `nme_backend/pytest.ini`
- `README.md`

### 8. STEP 49 후보

- STEP 48 회귀 테스트를 더 작은 단위로 분리할지 검토
- History/Dashboard용 fixture를 재사용 가능한 공용 헬퍼로 분리할지 검토
- CORS 및 rate limit 회귀를 별도 파일로 분리할지 검토

## STEP 49: 테스트 체계 정리 및 품질 고정

### 1. 목적

- STEP 48에서 구축한 pytest 기반 회귀 테스트를 E2E / Security / Smoke로 정리해 반복 사용 가능한 상태로 고정했습니다.

### 2. 테스트 구조

- `nme_backend/tests/conftest.py`: 테스트 전용 임시 SQLite DB 및 공통 fixture
- `nme_backend/tests/test_e2e_trade_flow.py`: 거래 E2E 시나리오
- `nme_backend/tests/test_auth_security.py`: 인증 / 세션 / rate limit / CORS 회귀
- `nme_backend/tests/test_api_smoke.py`: health / market / docs / openapi smoke
- `nme_backend/pytest.ini`: `tests/`만 수집하고 marker(e2e, security, smoke) 정의

### 3. 테스트 DB 분리

- 테스트는 실제 `nme.db`를 사용하지 않습니다.
- `DATABASE_URL`을 임시 SQLite 파일로 override합니다.
- 테스트 종료 후 실제 개발 DB는 변경되지 않습니다.

### 4. pytest 명령

- 전체: `python -m pytest -q`
- Smoke: `python -m pytest -q -m smoke`
- E2E: `python -m pytest -q -m e2e`
- Security: `python -m pytest -q -m security`

### 5. 테스트 시나리오

- Smoke: `/health`, `/market`, `/docs`, `/openapi.json`
- E2E: BUYER login → `/auth/me` → `/auth/sessions` → `/market` → Deal → AGREED → Order → COMPLETED → Completion → History → Dashboard
- Security: login / refresh / logout / revoke / revoke-all / session ownership / rate limit / CORS

### 6. 테스트 결과

- `python -m pytest -q`: `8 passed`
- E2E 통과
- Security regression 통과
- Smoke 통과

### 7. Known warning

- `python-jose`의 `datetime.datetime.utcnow()` deprecation warning이 출력됩니다.
- 기능 실패는 아니며, 별도 dependency maintenance 단계로 미룹니다.

### 8. DB 보호 결과

- 실제 `nme.db` count는 STEP 49 전후 동일합니다.
- users = 8
- products = 4
- deals = 23
- orders = 16
- auth_sessions = 82

### 9. npm run build 결과

- `nme_frontend`에서 `npm run build` 성공

### 10. Browser 검증 결과

- STEP 47에서 Market / History / Dashboard의 실제 화면 확인을 수행했습니다.
- STEP 49에서는 Browser Console을 직접 확인하지 못했습니다.

### 11. 변경 파일

- `nme_backend/tests/conftest.py`
- `nme_backend/tests/test_api_smoke.py`
- `nme_backend/tests/test_auth_security.py`
- `nme_backend/tests/test_e2e_trade_flow.py`
- `nme_backend/pytest.ini`
- `README.md`

### 12. STEP 50 준비 상태

- 향후에는 공통 fixture를 더 세분화할지 검토할 수 있습니다.
- 현재 구조는 반복 실행 가능한 회귀 체계로 유지 가능합니다.
