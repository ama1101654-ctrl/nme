NME Frontend (STEP 13)

Run:

cd nme_frontend
npm install
npm run dev

Dev server: http://localhost:5173
Backend: http://127.0.0.1:8000 (API base can be set via VITE_API_URL)

This minimal frontend shows Market data from backend and a simple "거래 제안" selection.

STEP 14 - Deal 생성 및 Deal Room

목적:
- Market 화면에서 거래 제안을 생성하고, 생성된 Deal을 확인하는 간단한 Deal Room을 제공합니다.

사용 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm install
	npm run dev

3. 브라우저 접속
	http://localhost:5173

플로우 요약:
- Market에서 상품 선택 → "거래 제안" 클릭
- 수량/제안 가격 입력 → "거래 제안 보내기" 클릭
- POST /deals 호출, 성공 시 Deal Room에 생성된 Deal 표시
- Deal Room에서 "상태 새로고침"으로 최신 Deal 상태 재조회

주의사항:
- 기본 테스트용 구매자 ID는 `2`로 하드코딩되어 있습니다 (파일 상단의 `DEFAULT_BUYER_ID`).
- Backend가 실행 중이어야 합니다. API 기본 URL: http://127.0.0.1:8000

테스트 시나리오와 검증 포인트는 프로젝트 루트의 작업 지침을 참고하세요.

STEP 15 - Deal Room 상태 변경

목적:
- Deal Room에서 `NEGOTIATING` 상태의 Deal을 `AGREED`, `REJECTED`, `CANCELLED`로 변경할 수 있도록 Backend의 `PATCH /deals/{deal_id}/status` API와 연결합니다.

사용 방법 요약:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm install
	npm run dev

3. 브라우저 접속: http://localhost:5173

동작:
- Deal Room에서 상태가 `NEGOTIATING`이면 `거래 승인`, `거래 거절`, `거래 취소` 버튼이 표시됩니다.
- 각 버튼 클릭 시 확인 창이 표시되고, 확인하면 `PATCH /deals/{id}/status` 호출로 상태가 변경됩니다.
- 호출 중에는 버튼이 비활성화되어 중복 요청을 막습니다.
- 성공 시 Deal Room에 성공 메시지가 표시됩니다.

테스트 포인트:
- NEGOTIATING → AGREED, REJECTED, CANCELLED 변경 확인
- 상태 변경 후 `상태 새로고침`으로 최신 상태 반영 확인
- 잘못된 요청(예: 404, 400, 네트워크 오류)에 대한 에러 메시지 표시 확인

STEP 16 - Deal → Order 연결

목적:
- Deal Room에서 Deal 상태가 `AGREED`일 때 주문 생성 기능을 연결합니다.
- 생성된 주문을 Deal Room에서 바로 확인하고, 재진입/새로고침 시 기존 주문을 복구합니다.

사용 API:
- `POST /deals/{deal_id}/create-order`
- `GET /deals/{deal_id}/order`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm install
	npm run dev

3. 빌드 확인
	npm run build

테스트 방법:
1. Market에서 상품 선택 후 Deal 생성
2. Deal Room에서 상태를 `AGREED`로 변경
3. `주문 생성` 클릭 후 Order 정보 표시 확인
4. 동일 Deal에서 다시 생성 시 중복 생성 차단(400) 및 기존 주문 표시 확인
5. Deal Room 재진입/새로고침 후 `GET /deals/{deal_id}/order` 기반 주문 복구 확인

STEP 17 - Order 상태 관리

목적:
- Deal Room의 Order 영역에서 실제 거래 진행 상태를 단계별로 변경합니다.
- Frontend에서 상태 변경을 요청하고 Backend 상태를 다시 조회해 화면과 동기화합니다.

Order 상태 흐름:
- PENDING → ACCEPTED → PAID → SHIPPED → COMPLETED

사용 API:
- `PATCH /orders/{order_id}/status`
- `GET /deals/{deal_id}/order`
- `GET /deals/{deal_id}`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm run dev

3. Production build
	npm run build

테스트 방법:
1. Deal을 `AGREED`로 만들고 Order를 생성합니다.
2. Order 상태가 `PENDING`이면 `주문 승인` 버튼으로 `ACCEPTED` 변경을 확인합니다.
3. `ACCEPTED`에서 `결제 완료` 버튼으로 `PAID` 변경을 확인합니다.
4. `PAID`에서 `출하 처리` 버튼으로 `SHIPPED` 변경을 확인합니다.
5. `SHIPPED`에서 `거래 완료` 버튼으로 `COMPLETED` 변경을 확인합니다.
6. `COMPLETED`에서는 다음 상태 버튼이 없어야 합니다.
7. `주문 상태 새로고침`으로 Backend 최신 상태 재조회가 동작해야 합니다.

정상 상태 전이:
- PENDING → ACCEPTED
- ACCEPTED → PAID
- PAID → SHIPPED
- SHIPPED → COMPLETED

오류 처리:
- 400: Backend detail 메시지 우선 표시 (예: Invalid order status transition)
- 404: 주문을 찾을 수 없습니다.
- Network Error: 서버와 통신할 수 없습니다.
- 기타 오류: 주문 상태를 변경하지 못했습니다.

STEP 18 - 거래 이력(History)

목적:
- 거래 완료 후 사용자가 전체 거래 이력을 확인할 수 있는 History 화면을 제공합니다.
- 기존 Backend API를 재사용하여 Deal, Order, Completion 정보를 함께 보여줍니다.

거래 이력 기능:
- 상단 네비게이션에 `거래 이력` 탭 추가
- 거래 이력 필터: `전체`, `진행중`, `완료`
- 거래별 표시 정보:
  - Deal ID, Product ID, Buyer ID, Quantity, Proposed Price
  - Deal Status, Order ID, Order Status, Created At, 거래 완료 여부
- `상세 보기`로 Deal 단건 상세 확인
- `이력 새로고침`으로 Backend 최신 상태 재조회

사용 API:
- `GET /deals`
- `GET /deals/{deal_id}`
- `GET /deals/{deal_id}/order`
- `GET /deals/{deal_id}/completion`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm run dev

3. Production build
	npm run build

테스트 방법:
1. 거래를 생성하고 Deal 상태를 `AGREED`로 변경합니다.
2. Order를 생성하고 상태를 `COMPLETED`까지 진행합니다.
3. `거래 이력` 탭에서 완료 거래가 `완료` 필터에 표시되는지 확인합니다.
4. Order가 없는 Deal이 `주문 생성 전`으로 표시되는지 확인합니다.
5. `상세 보기`에서 Deal/Order/완료 여부가 정상 표시되는지 확인합니다.
6. `이력 새로고침` 클릭 시 최신 상태가 다시 반영되는지 확인합니다.

오류 처리:
- 이력 로딩 실패: `거래 이력을 불러오지 못했습니다.`
- 네트워크 오류: `서버와 통신할 수 없습니다.`
- Deal에 Order가 없는 404는 정상 상황으로 처리하여 카드에 `주문 생성 전` 표시

완료 조건:
- 거래 이력 목록/필터/상세 보기가 정상 동작
- 완료 거래가 별도 필터에서 확인 가능
- 기존 STEP 1~17 기능이 그대로 동작

STEP 19 - 내 거래 관리 (Buyer 기준)

목적:
- 인증 없이 MVP 단계에서 현재 사용자(Buyer) 기준으로 거래를 관리할 수 있게 확장합니다.
- 거래 이력에서 내 거래/전체 거래, 검색, 상태 필터, 정렬 기능을 제공합니다.

현재 사용자:
- `DEFAULT_BUYER_ID`를 현재 사용자로 사용합니다.
- 기본 화면은 Buyer 기준 `내 거래`를 우선 표시합니다.

주요 기능:
- `내 거래` / `전체 거래` 범위 전환
- 검색: Deal ID / Product ID 부분 일치
- 상태 필터: 전체 / 진행중 / 완료
- 정렬: 최신순 / 오래된순 / 가격 높은순 / 가격 낮은순
- 결과 건수 표시
- 기존 상세 보기 유지 + 거래 진행 단계 표시

사용 API:
- `GET /deals`
- `GET /deals/{deal_id}`
- `GET /deals/{deal_id}/order`
- `GET /deals/{deal_id}/completion`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm run dev

3. Production build
	npm run build

테스트 방법:
1. `내 거래`에서 Buyer #2의 거래만 표시되는지 확인
2. 검색어 `10` 입력 시 Deal #10 포함 결과 확인
3. Product ID 검색(예: `3`) 결과 확인
4. `완료` 필터에서 COMPLETED 거래만 확인
5. `진행중` 필터에서 COMPLETED 제외 확인
6. 정렬(최신순/오래된순/가격 높은순/가격 낮은순) 확인
7. 검색 결과 없음 시 `조건에 맞는 거래가 없습니다.` 표시 확인
8. Order 없는 Deal은 `주문 생성 전` 표시 확인
9. 상세 보기에서 Deal/Order/완료 여부/진행 단계 표시 확인

오류 처리:
- API 오류: `거래 정보를 불러오지 못했습니다.`
- 네트워크 오류: `서버와 통신할 수 없습니다.`
- 검색 결과 없음: `조건에 맞는 거래가 없습니다.`

완료 조건:
- Buyer 기준 거래 관리 + 검색/필터/정렬이 정상 동작
- 기존 STEP 1~18 흐름이 유지됨

STEP 20 - 거래 관리 UX 고도화

목적:
- STEP 1~19 흐름을 하나의 일관된 MVP 사용자 경험으로 정리합니다.
- 거래 이력 화면을 중심으로 대시보드/상세 UX/현재 할 일 안내를 강화합니다.

핵심 기능:
1. 거래 Dashboard
- 전체 거래
- 진행중 거래
- 완료 거래
- 주문 생성 전 거래

2. 거래 진행 단계(상세)
- ① 거래 제안
- ② 거래 승인
- ③ 주문 생성
- ④ 주문 승인
- ⑤ 결제
- ⑥ 배송
- ⑦ 거래 완료

3. 거래 상세 정보 구분
- 거래 정보, 주문 정보, 거래 완료, 현재 할 일 섹션

4. 현재 할 일 안내(상태 기반)
- NEGOTIATING: 상대방의 거래 승인을 기다리고 있습니다.
- AGREED + Order 없음: 주문을 생성할 수 있습니다.
- PENDING: 주문 승인을 기다리고 있습니다.
- ACCEPTED: 결제를 진행할 수 있습니다.
- PAID: 배송을 기다리고 있습니다.
- SHIPPED: 거래 완료를 기다리고 있습니다.
- COMPLETED: 거래가 완료되었습니다.
- REJECTED/CANCELLED: 거래가 종료되었습니다.

5. 거래 이력 UX 보강
- 거래 없음: `아직 거래 내역이 없습니다.`
- 조건 미일치: `조건에 맞는 거래가 없습니다.`
- 상태 요약: `거래 완료` / `진행 중` / `주문 생성 전`

사용 API:
- `GET /health`
- `GET /market`
- `POST /deals`
- `GET /deals`
- `GET /deals/{deal_id}`
- `PATCH /deals/{deal_id}/status`
- `POST /deals/{deal_id}/create-order`
- `GET /deals/{deal_id}/order`
- `PATCH /orders/{order_id}/status`
- `GET /deals/{deal_id}/completion`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm run dev

3. Production build
	npm run build

포트/CORS 주의사항:
- 기본 Frontend 포트는 `5173`입니다.
- 5173 점유 시 Vite가 `5174`로 자동 전환될 수 있습니다.
- Backend CORS는 `5173`과 `5174`(localhost/127.0.0.1) 모두 허용하도록 구성되어 있습니다.

테스트 방법:
1. Market 표시 확인
2. 거래 제안 생성
3. Deal Room에서 거래 승인
4. Order 생성 및 상태 변경(완료까지)
5. 거래 이력에서 내 거래/전체 거래 확인
6. 검색/필터/정렬 확인
7. 상세 보기에서 진행 단계/현재 할 일 확인
8. 주문 없는 Deal/완료된 Deal 표시 확인
9. 새로고침 후 상태 복구 확인

오류 처리:
- API 오류: `거래 정보를 불러오지 못했습니다.`
- 네트워크 오류: `서버와 통신할 수 없습니다.`
- 개발자 상세: `console.error()`

완료 조건:
- Dashboard/상세 UX/현재 할 일 안내가 정상 동작
- 기존 STEP 1~19 기능이 모두 유지됨
- `npm run build` 성공

STEP 21 - 거래 관리 고도화 + 사용자 Action Center

목적:
- 사용자가 현재 거래 상태와 해야 할 행동을 즉시 이해할 수 있도록 거래 관리 UX를 강화합니다.
- 기존 STEP 1~20 기능을 유지한 상태에서 Action Center 중심으로 개선합니다.

Action Center:
- 거래 상세 화면에서 상태 기반 `현재 할 일`을 표시합니다.
- 상태, 설명, 현재 단계, 다음 단계, 필요한 버튼을 함께 안내합니다.

Action Required:
- Dashboard에 `내가 해야 할 일` 카드를 추가합니다.
- 현재 사용자(Buyer #2) 기준으로 실제 액션이 필요한 거래를 동적으로 계산합니다.

상태별 사용자 행동(요약):
- NEGOTIATING: 상대방 승인 대기
- AGREED + Order 없음: 주문 생성 가능 (`주문 생성` 버튼)
- PENDING: 주문 승인 대기
- ACCEPTED: 결제 준비 가능 (`결제 준비` 버튼, 안내 메시지)
- PAID: 배송 대기
- SHIPPED: 배송 진행 중
- COMPLETED: 거래 완료
- REJECTED/CANCELLED: 거래 종료

거래 상세 개선:
- 거래 정보 / 주문 정보 / 거래 완료 / 현재 할 일 / 7단계 진행 표시로 분리
- 7단계 진행 표시: 제안 → 승인 → 주문 생성 → 주문 승인 → 결제 → 배송 → 거래 완료

Dashboard 개선:
- 전체 거래, 진행중, 완료, 주문 생성 전, 내가 해야 할 일

사용 API:
- `GET /market`
- `POST /deals`
- `GET /deals`
- `GET /deals/{deal_id}`
- `PATCH /deals/{deal_id}/status`
- `POST /deals/{deal_id}/create-order`
- `GET /deals/{deal_id}/order`
- `PATCH /orders/{order_id}/status`
- `GET /deals/{deal_id}/completion`

실행 방법:
1. Backend 실행
	cd nme_backend
	.venv\Scripts\python.exe -m uvicorn app.main:app --reload

2. Frontend 실행
	cd nme_frontend
	npm run dev

3. Production build
	npm run build

테스트 방법:
1. 거래 이력에서 Dashboard 수치 확인
2. 거래 카드의 `현재 단계` / `다음 행동` 확인
3. 상세 보기에서 Action Center와 7단계 진행 표시 확인
4. AGREED + Order 없음에서 주문 생성 버튼 동작 확인
5. ACCEPTED에서 결제 준비 버튼 클릭 시 안내 메시지 확인
6. COMPLETED에서 추가 액션 버튼이 없는지 확인

오류 처리:
- API 오류: 사용자 메시지 표시
- 네트워크 오류: `서버와 통신할 수 없습니다.`
- 개발자 로그: `console.error()` 유지

기존 데이터 보호:
- `nme.db` 삭제/초기화/스키마 변경 없이 기존 데이터 유지

STEP 21 완료 조건:
- Action Center/Action Required가 상태에 맞게 정확히 동작
- 기존 STEP 1~20 기능 유지
- `npm run build` 성공

STEP 21 보완 - CANCELLED 거래 종료 UX 정리

목적:
- `Order.status === CANCELLED`일 때 fallback(`상태 확인 필요`, `-`)으로 내려가지 않도록 명시 처리합니다.
- 사용자가 즉시 거래 종료 상태를 이해할 수 있도록 Action Center/상세/목록/진행 단계를 보완합니다.

핵심 변경:
1. Action Center
- 상태: 거래 취소
- 메인 메시지: `거래가 취소되었습니다.`
- 설명: `주문이 취소되어 현재 거래는 종료되었습니다.`
- 현재 단계: `거래 취소`
- 다음 단계: `없음`
- Action Required: 없음
- 실행 버튼: 없음

2. Action Required 집계
- CANCELLED 거래는 `required: false`로 계산되어 `내가 해야 할 일`에 포함되지 않습니다.

3. 거래 진행 단계
- 기존 7단계 흐름은 유지합니다.
- CANCELLED 상태에서는 별도 종결 문구 `🔴 거래 취소됨`을 함께 표시해 정상 완료(COMPLETED)와 구분합니다.

4. 거래 상세
- 주문 상태는 `주문 취소`로 표시됩니다.
- 거래 완료 여부는 completion 결과를 그대로 사용합니다(예: `NO`).
- 추가 안내: `이 거래는 취소되어 더 이상 진행되지 않습니다.`

5. 거래 목록
- 상태 요약에서 CANCELLED는 `거래 취소`로 표시됩니다.
- fallback 문구가 노출되지 않도록 처리합니다.

Backend 계약 주의:
- 현재 Backend Order status enum: `PENDING`, `ACCEPTED`, `PAID`, `SHIPPED`, `COMPLETED`, `CANCELLED`
- `REJECTED`는 Order enum에 존재하지 않으므로 이번 CANCELLED 검증 대상에서 제외합니다.

테스트 방법:
1. CANCELLED 주문이 연결된 거래 상세 진입
2. Action Center에서 취소 메시지/설명/단계(`거래 취소`, `없음`) 확인
3. 액션 버튼 없음 확인
4. 진행 단계에서 fallback(`-`, `상태 확인 필요`) 미노출 확인
5. Dashboard `내가 해야 할 일`에 CANCELLED 미집계 확인
6. 거래 목록 상태 요약에서 `거래 취소` 표시 확인

Build 검증:
- `npm run build` 실행
- Vite build 성공(`✓ built`) 확인

STEP 22 - 사용자 거래 관리 UX 개선 (Action Required 강화)

목적:
- 사용자가 `지금 처리해야 할 거래`를 한눈에 파악할 수 있도록 거래 이력 화면의 Action Center를 강화합니다.
- 기존 STEP 1~21 기능과 API 계약을 유지한 상태에서 Frontend 계산으로만 구현합니다.

핵심 변경:
1. Action Required 전용 목록
- 거래 이력 상단 Dashboard 아래에 `내가 해야 할 일` 전용 영역 추가
- Action Required 거래만 표시, 기본 최대 5건 노출
- 5건 초과 시 `전체 보기` 버튼으로 확장/접기
- 각 항목에 `거래 상세 보기` 버튼 제공(기존 상세 state 재사용)

2. 우선순위 정렬
- 우선순위 오름차순 + 생성일 최신순 정렬
- 우선순위 규칙:
	- 1: 주문 생성 필요 (AGREED + Order 없음)
	- 2: 결제 필요 (ACCEPTED)
	- 3: 주문 승인 대기 (PENDING)
	- 4: 거래 완료 처리 대기 (SHIPPED)
	- 5: 거래 승인 대기 (NEGOTIATING)

3. 제외 규칙
- COMPLETED 거래: Action Required 제외
- CANCELLED 거래: Action Required 제외

4. Dashboard 카드 보강
- 기존 카드 유지
- `내가 해야 할 일` 카드에 설명 문구 `지금 처리해야 하는 거래` 추가

5. 상태 메시지
- 로딩: `처리할 거래를 불러오는 중...`
- API 오류: `처리할 거래를 불러오지 못했습니다.`
- 네트워크 오류: `서버와 통신할 수 없습니다.`
- Empty state:
	- `현재 처리할 거래가 없습니다.`
	- `새로운 거래가 제안되거나 진행되면 이곳에 표시됩니다.`

Backend/DB 제약 준수:
- Backend 파일(`main.py`, `database.py`, `models.py`, `schemas.py`, `crud.py`) 미수정
- 신규 API 추가 없음
- `nme.db` 초기화/삭제/마이그레이션 없음

검증 포인트:
1. `npm run build` 성공
2. 거래 이력에서 `내가 해야 할 일` 목록 노출 확인
3. 우선순위 정렬 및 최대 5건 노출 확인
4. `거래 상세 보기`로 기존 상세 화면 이동 확인
5. COMPLETED/CANCELLED가 Action Required 목록에서 제외되는지 확인
6. 기존 검색/필터/정렬/상세/Deal/Order 흐름 회귀 없음 확인

STEP 23 - Current User 구조 도입 (MVP)

목적:
- `DEFAULT_BUYER_ID` 하드코딩 의존을 줄이고, Frontend에서 현재 사용자 개념을 단일 구조로 관리합니다.
- 실제 로그인/회원가입 없이도 향후 인증 연동이 쉬운 형태로 정리합니다.

Current User 구조:
- App 내부에서 현재 사용자 정보를 단일 객체로 관리
- 예: `{ id, role, name }`
- 현재 MVP 값:
	- `id: 2`
	- `role: BUYER`
	- `name: MVP Buyer`

역할 표시:
- 거래 관리/거래 이력 화면에서 현재 사용자와 역할을 표시합니다.
- MVP에서는 `BUYER(구매자)`만 사용합니다.

내 거래 기준:
- 기존 `buyer_id === DEFAULT_BUYER_ID`를 `buyer_id === CURRENT_USER.id` 기준으로 통합
- `내 거래(MY)` 범위, 거래 건수, 사용자 기반 대시보드 지표, Action Required가 모두 현재 사용자 기준으로 동작

Dashboard 기준:
- `전체 거래`: 전체 Deal 기준
- `진행중`, `완료`, `주문 생성 전`, `내가 해야 할 일`: 현재 사용자(`CURRENT_USER.id`) 기준

Action Required 연동:
- 현재 사용자 거래만 대상으로 계산
- 포함: NEGOTIATING, AGREED+Order 없음, PENDING, ACCEPTED, SHIPPED
- 제외: COMPLETED, CANCELLED

History 연동:
- `내 거래`/`전체 거래` 전환 유지
- 검색/필터/정렬/상세 보기 기존 동작 유지
- 상세 화면에서 `거래 구분(내 거래/전체 거래)` 표시

Backend/DB 제약 준수:
- Backend 파일 수정 없음
- 신규 API 없음
- SQLite(`nme.db`) 초기화/삭제/마이그레이션/데이터 삭제 없음

실행 방법:
1. Backend 실행
2. Frontend 실행
3. `npm run build` 확인

테스트 방법:
1. 거래 이력에서 현재 사용자/역할 표시 확인
2. `내 거래`에서 CURRENT_USER.id 기준 데이터 확인
3. `전체 거래` 전환 후 전체 데이터 확인
4. Action Required가 현재 사용자 기준으로 계산되는지 확인
5. 검색/상태 필터/정렬/상세 보기 회귀 확인
6. Market/Deal/Order/History/Dashboard 기존 흐름 유지 확인

STEP 24 - Role 기반 거래 화면 분리 준비

목적:
- 실제 로그인/회원가입 없이 `CURRENT_USER.role` 기준으로 거래 화면의 역할 표시와 Action Center 문구를 분리합니다.
- Backend/DB/API 계약은 그대로 유지하고 Frontend 구조만 역할 확장 가능 형태로 정리합니다.

Current User 구조:
- 기존 단일 구조 유지: `{ id, role, name }`
- 기본값은 BUYER
- 지원 역할 라벨 구조:
	- BUYER: 구매자
	- SELLER: 판매자
	- ADMIN: 관리자(표시 구조만 준비)

역할 Helper:
- `isBuyerRole`, `isSellerRole`, `labelUserRole`, `labelUserCode` 추가
- 향후 로그인 정보 주입 시 동일 참조 지점 재사용 가능

역할별 UI 반영:
1. Market
- 현재 사용자 표시: `Buyer/Seller/Admin #id · name · 역할`

2. 거래 이력/거래 관리
- 현재 사용자/역할 표시 유지
- 상세 화면에 `현재 사용자 역할` 표시
- 상세 화면의 `거래 구분(내 거래/전체 거래)` 유지

3. Action Required
- 기존 계산 로직(상태 포함/제외 규칙)은 그대로 유지
- 역할에 따라 제목/설명만 분기
	- BUYER: `내가 해야 할 일`
	- SELLER: `판매자가 해야 할 일`

MY / ALL:
- 기존 동작 유지
- `MY`: `buyer_id === CURRENT_USER.id`
- `ALL`: 전체 거래

Seller 테스트 방법:
1. App 상단 `CURRENT_USER.role`을 `SELLER`로 변경
2. 화면의 현재 사용자/역할 표기, Action Required 제목 분기 확인
3. History/Dashboard/상세 화면 진입 확인
4. 검증 후 role을 `BUYER`로 복원

실행 방법:
1. `npm run dev`
2. `npm run build`

검증 결과(요약):
- BUYER 기본 흐름 유지
- SELLER role 변경 시 역할 표기/문구 분기 정상
- COMPLETED/CANCELLED Action Required 제외 유지
- Backend 변경 없음, DB 보호 유지

STEP 25 준비 상태:
- 로그인 시스템 연결 시 `CURRENT_USER` 주입만 교체하면 역할 기반 화면을 그대로 확장 가능

STEP 25 - Current User 구조와 거래 조회 API 계약 안정화

STEP 35 - DB 기반 Authentication Session 관리

DB 기반 AuthSession 추가:
- Backend에 `AuthSession` 모델 추가
- 필드:
	- `id`
	- `user_id`
	- `refresh_jti`
	- `expires_at`
	- `revoked_at`
	- `created_at`
- 기존 `User`, `Deal`, `Order`, `Product` 모델은 변경하지 않음

AuthSession과 Refresh Token 연결:
- 로그인 성공 시 refresh token의 `jti`와 `expires_at`를 DB `auth_sessions` 테이블에 저장
- `POST /auth/refresh`는 JWT 검증 후 DB `auth_sessions`를 source of truth로 조회
- `revoked_at`이 있거나 세션이 없으면 `401`

Refresh Rotation:
- `R1` 사용 -> `R2` 발급 + `R1` DB revoke
- `R1` 재사용 -> `401`
- `R2` 사용 -> `R3` 발급 + `R2` DB revoke
- rotation은 BUYER / SELLER 모두 검증 완료

`revoked_at`:
- refresh token이 사용되거나 logout될 때 현재 AuthSession의 `revoked_at`을 기록
- 메모리 set이 아니라 DB `auth_sessions`가 revoke 상태의 source of truth가 됨

서버 재시작 후 revoke 유지:
- Buyer 세션으로 R1 -> R2 생성 후 서버 재시작
- 재시작 후 R1 재사용 -> `401`
- 재시작 후 R2 정상 refresh -> `200`
- logout된 refresh token도 재시작 후 `401`

`POST /auth/logout`:
- Access Token 인증 유지
- body의 `refresh_token`을 decode하여 해당 AuthSession revoke
- Frontend는 기존처럼 finally에서 local token 삭제 유지

BUYER 테스트:
- `bob@example.com / secret`
- `POST /auth/login` 200
- `GET /auth/me` 200
- Market / History / Dashboard / Action Required 정상
- refresh rotation과 logout revoke 정상

SELLER 테스트:
- `charlie@example.com / secret`
- `POST /auth/login` 200
- `GET /auth/me` 200
- Market / History / Dashboard / Action Required 정상
- refresh rotation 정상

인증 실패 테스트:
- refresh token 없음 -> `401`
- invalid refresh token -> `401`
- expired refresh token -> `401`
- access token을 refresh token 자리에 사용 -> `401`
- refresh token을 `/auth/me`에 사용 -> `401`
- revoke된 refresh token -> `401`
- 이미 사용된 이전 refresh token -> `401`
- logout 후 refresh -> `401`

DB 보호 결과:
- 기존 데이터 수량 유지
- 최종 확인:
	- `users = 8`
	- `deals = 19`
	- `orders = 13`
	- `products = 4`
- 인증 테스트는 `auth_sessions`만 증가 가능

`npm run build` 결과:
- 성공

Swagger 결과:
- `/docs` 정상
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/refresh`
- `POST /auth/logout`
모두 노출 확인

Browser Console 결과:
- 정상 BUYER / SELLER 경로에서 치명 오류 없음
- 의도된 인증 실패 `401`만 기록

STEP 36 준비 상태:
- 현재는 DB `auth_sessions`를 사용해 revoke가 서버 재시작 후에도 유지됨
- 다음 단계에서는 token family, session/device 관리, refresh session 정리 정책, refresh token hash 저장 강화 등을 검토할 수 있음

목적:
- `CURRENT_USER` 구조를 유지한 채 거래 조회는 Backend의 실제 API 계약에 정확히 맞추어 호출합니다.
- 로그인/JWT 없이도 History/Dashboard/Action Required가 안정적으로 동작하도록 GET `/deals` 연동 기준을 명확히 합니다.

GET `/deals` 실제 API 계약:
- Method: `GET`
- Path: `/deals`
- Query parameter:
	- `skip` (integer, optional, default `0`)
	- `limit` (integer, optional, default `100`)
- Required query parameter 없음
- `buyer_id`, `user_id`, `role` query parameter 없음
- Response model: `list[DealResponse]`

422 원인 분석:
- STEP 24 검증 중 관찰된 `422`는 실제 `GET /deals` 실패가 아니었습니다.
- 원인은 존재하지 않는 경로 `GET /deals/history` 호출 시 FastAPI가 이를 `/deals/{deal_id}`로 해석하고, `deal_id='history'`를 integer로 검증하다 실패한 것입니다.
- 즉 원인 분류는 다음과 같습니다.
	- `F. path/query parameter 충돌`
	- 세부 원인: 존재하지 않는 path가 `/deals/{deal_id}`와 충돌하여 Pydantic/FastAPI path validation 422 발생

Frontend 호출 방식:
- History 로딩은 `GET /deals`만 사용합니다.
- `CURRENT_USER.id`는 서버 query parameter로 보내지 않습니다.
- `MY / ALL` 범위 계산은 Frontend에서 `buyer_id === CURRENT_USER.id` 기준으로 처리합니다.
- STEP 25에서 추가 인증 구조는 도입하지 않습니다.

수정한 파일:
- `src/App.jsx`
- `README.md`

수정 내용:
1. `GET /deals` 호출을 `buildDealsUrl()` helper로 고정
2. `CURRENT_USER` 기반 query parameter를 보내지 않는 계약을 코드에 명시
3. History 로딩 시 `422 / 404 / 500 / network` 오류 메시지 구분
4. `GET /deals` 응답이 배열이 아닐 경우 형식 오류로 처리

Swagger / OpenAPI 검증:
- `http://127.0.0.1:8000/openapi.json` 기준 `GET /deals`는 `skip`, `limit`만 노출
- `GET /deals/history`는 Swagger에 존재하지 않음
- `DealResponse`는 `id`, `product_id`, `buyer_id`, `quantity`, `proposed_price`, `status`, `created_at` 필드를 반환

직접 API 검증:
1. `GET /health` → `200`, `{"status":"ok"}`
2. `GET /deals` → `200`, Deal 목록 정상 반환
3. `GET /deals/history` → `422`
4. 422 detail:
	- `path.deal_id`
	- `Input should be a valid integer`
	- `input: "history"`

Browser 검증:
1. Market
- Buyer #2 / 구매자 표시 확인
- 상품 목록 정상 표시 확인

2. 거래 관리
- 빈 Deal Room 상태 메시지 정상 표시 확인
- 기존 진입 구조 유지 확인

3. 거래 이력
- History 진입 시 `GET /deals`와 per-deal order/completion API 정상 호출 확인
- `내 거래` / `전체 거래` 전환 확인
- 상세 진입 확인

4. Dashboard
- 전체 거래 / 진행중 / 완료 / 주문 생성 전 / 내가 해야 할 일 카드 표시 확인

5. Action Required
- 우선순위 정렬 표시 확인
- 상세 진입 확인
- COMPLETED / CANCELLED 항목 제외 유지 확인

6. Role
- BUYER 기본값에서 `Buyer #2 · MVP Buyer · 역할: 구매자` 확인
- SELLER 임시 전환 시 `Seller #3 · MVP Seller · 역할: 판매자` 및 Action Required 제목/설명 분기 확인
- 검증 후 BUYER 기본값으로 복원

데이터 보호:
- SQLite 초기화/삭제 없음
- Deal/Order 데이터 삭제 없음
- schema / migration 변경 없음

Build 결과:
- `npm run build` 성공

STEP 26 준비 상태:
- 현재 사용자 구조는 UI/클라이언트 필터 기준으로 유지
- 향후 로그인 사용자 주입 시에도 거래 조회는 `GET /deals` 계약 그대로 재사용 가능
- 다음 단계에서는 인증 도입 전에도 API wrapper 또는 사용자 주입 레이어만 분리하면 확장 가능

STEP 26 - Backend User 기반 Current User 연결

목적:
- Frontend의 임시 `CURRENT_USER` 상수를 Backend 실제 User API와 연결 가능한 구조로 전환합니다.
- 로그인/JWT 없이 `GET /users/{user_id}` 응답을 `currentUser` state에 연결하고, 기존 MY 거래 / Dashboard / Action Required / Role UI를 유지합니다.

기존 Current User 구조:
- 기존에는 Frontend 내부 상수 `CURRENT_USER = { id, role, name }`를 직접 사용했습니다.
- STEP 26에서는 이 구조를 `DEFAULT_USER_ID + currentUser state + GET /users/{id}` 흐름으로 전환했습니다.

Backend User 분석 결과:
- User 모델 존재: `id`, `company_name`, `name`, `email`, `password`, `role`, `created_at`
- 기존 User CRUD 존재: `get_users`, `get_user`, `create_user`
- 기존 User API 존재:
	- `GET /users`
	- `GET /users/{user_id}`
- 기존 UserResponse schema 존재:
	- `id`
	- `company_name`
	- `name`
	- `email`
	- `role`

Current User 조회 API:
- 재사용 API: `GET /users/{user_id}`
- 새 `/users/me` API는 추가하지 않음
- 인증 시스템도 추가하지 않음

User Response Schema 사용 방식:
- Frontend에서 사용하는 최소 필드:
	- `id`
	- `name`
	- `role`
- 기존 `UserResponse`를 그대로 재사용

실데이터 정합화:
- 기존 DB에는 `User #2`, `User #3`가 존재했지만 이름/role이 MVP 기대값과 달랐습니다.
- 스키마 변경이나 행 삭제 없이 기존 두 사용자 레코드만 최소 수정했습니다.
	- `User #2` → `MVP Buyer`, `BUYER`
	- `User #3` → `MVP Seller`, `SELLER`
- Deal / Order / User row 삭제는 없었고 ID도 유지했습니다.

Frontend Current User 연결:
- `DEFAULT_USER_ID = 2`
- 앱 시작 시 `GET /users/2` 호출
- 성공 시 응답의 `id`, `name`, `role`을 `currentUser` state에 저장
- 실패 시 fallback 사용자 구조를 유지하고 사용자 메시지 표시

추가한 연결 규칙:
1. `userLoading` 상태 분리
2. `userError` 상태 분리
3. `currentUser`가 null이어도 fallback으로 UI 유지
4. React StrictMode 중복 mount를 피하기 위해 사용자 bootstrap 요청 캐시 적용

MY 거래 연결:
- Backend `GET /deals`는 그대로 사용
- `buyer_id` query parameter 추가 없음
- Frontend에서 `item.deal.buyer_id === currentUser.id` 기준으로 MY 거래 계산

Dashboard 연결:
- `currentUser.id` 기준으로 내 거래 집계 유지
- 다음 카드가 currentUser 기준으로 정상 계산됨
	- 전체 거래
	- 진행중
	- 완료
	- 주문 생성 전
	- 내가 해야 할 일

Action Required 연결:
- 기존 규칙 유지
- 계산 기준만 `currentUser.id`, `currentUser.role`로 연결
- COMPLETED / CANCELLED 제외 규칙 유지
- 우선순위 유지

Role UI 연결:
- Backend에서 받은 `role`을 그대로 사용
- BUYER:
	- `Buyer #2 · MVP Buyer · 역할: 구매자`
- SELLER:
	- `Seller #3 · MVP Seller · 역할: 판매자`

오류 처리:
- `GET /users/{id}`
	- 200: 정상
	- 404: 현재 사용자를 찾을 수 없음
	- 422: 요청 계약 오류
	- 500: 서버 오류
	- Network Error: 서버 연결 실패
- 개발 상세는 `console.error`, 사용자 메시지는 화면에 표시

API 테스트:
1. `GET /health` → `200`
2. `GET /users` → `200`
3. `GET /users/2` → `200`, `MVP Buyer / BUYER`
4. `GET /users/3` → `200`, `MVP Seller / SELLER`
5. `GET /deals` → `200`
6. `GET /deals/{deal_id}/order` → 정상 응답 확인
7. `GET /deals/{deal_id}/completion` → 정상 응답 확인

BUYER 테스트:
- 기본값 `DEFAULT_USER_ID = 2`
- Market에서 Buyer #2 / MVP Buyer / 구매자 표시 확인
- History / MY 거래 / Dashboard / Action Required / 상세 / 거래 구분 확인
- 사용자 bootstrap API는 최초 진입 시 1회 호출 확인

SELLER 테스트:
1. `DEFAULT_USER_ID = 3`으로 임시 변경
2. `GET /users/3` 연결 확인
3. Market에서 Seller #3 / MVP Seller / 판매자 표시 확인
4. History에서 `판매자가 해야 할 일` 제목/설명 확인
5. 검증 후 `DEFAULT_USER_ID = 2`로 복원

Browser 테스트:
- Console에서 `422`, `404`, `CORS`, `Failed to fetch`, React runtime error, `undefined`, `null reference` 없음
- History 검색/상세 진입 확인
- 전체 거래 전환 확인
- Action Required 상세 진입 확인

SQLite 데이터 보호:
- DB 초기화 없음
- 테이블 삭제 없음
- migration 없음
- Deal 삭제 없음
- Order 삭제 없음
- User 삭제 없음
- 스키마 변경 없음

Build 결과:
- `npm run build` 성공

STEP 27 준비 상태:
- 현재 사용자 bootstrap이 Backend User API 기반으로 연결됨
- 향후 로그인 도입 시 `DEFAULT_USER_ID` 대신 실제 인증 사용자 id만 주입하면 현재 구조를 재사용 가능
- 다음 단계에서 `/users/me` 또는 인증 토큰이 도입되더라도 `currentUser` state 연결 지점만 교체하면 됨

STEP 27 - 인증 도입을 위한 최소 Bootstrap 경계 정리

목적:
- 실제 인증(JWT/OAuth/로그인/권한) 구현 없이, Frontend에서 인증 사용자 연결 교체 지점을 명확히 고정합니다.
- 기존 Backend API/DB 계약은 변경하지 않고 현재 동작을 유지합니다.

핵심 변경:
1. 사용자 bootstrap id 해석 지점 분리
- `resolveBootstrapUserId()` 추가
- 우선순위: `VITE_BOOTSTRAP_USER_ID`(유효한 양의 정수) → `DEFAULT_USER_ID`
- 유효하지 않은 env 값은 경고 로그 후 안전하게 기본값으로 fallback

2. 인증 교체 지점 고정
- `BOOTSTRAP_USER_ID` 상수를 기준으로 fallback 사용자 생성 및 `GET /users/{id}` 조회를 통일
- 향후 인증 도입 시 이 상수/해석 함수만 교체하면 `currentUser`, History, Dashboard, Action Required 로직은 재사용 가능

3. 사용자 로딩 네트워크 오류 메시지 보강
- HTTP 오류(404/422/500)는 기존 상태코드 기반 메시지 유지
- 네트워크 오류(TypeError)는 `현재 사용자 API에 연결할 수 없습니다. 기본 사용자 정보로 계속합니다.`로 명확화

수정 파일:
- `src/App.jsx`
- `README.md`

검증 결과:
1. 브라우저 진입
- `http://127.0.0.1:5174/` 정상 접속

2. 현재 사용자 bootstrap
- `GET /users/2` 200 응답 확인
- StrictMode 환경에서도 사용자 bootstrap 응답은 1회로 dedupe 확인

3. 거래 이력 회귀
- 거래 이력 진입, MY/ALL 전환, 상태 필터(완료), 정렬(가격 높은순), 검색(Deal/Product ID), 상세 진입 동작 확인
- 콘솔에서 `422`, `404`, `CORS`, React runtime error 미발생 확인

4. API/DB 보호
- Backend 코드 변경 없음
- DB 스키마 변경/초기화/삭제 없음

Build 결과:
- `npm run build` 성공

다음 인증 단계 연결 가이드:
- 이후 로그인 도입 시에는 `resolveBootstrapUserId()` 반환값만 인증 사용자 id(또는 `/users/me` 결과 id)로 교체
- 거래 조회(`GET /deals`) 계약 및 클라이언트 필터 구조는 그대로 유지 가능

STEP 28 - 인증 컨텍스트 주입을 위한 Current User 경계 분리

목적:
- 실제 로그인/JWT 인증 구현 없이, `현재 사용자 ID를 어디서 가져오는지`를 UI/거래 로직에서 분리합니다.
- STEP 29 이후 인증 컨텍스트를 주입할 수 있는 최소 경계를 만듭니다.

왜 인증 시스템을 지금 구현하지 않았는가:
- 이번 단계는 인증 기능 구현 단계가 아니라 연결 경계 준비 단계입니다.
- `/login`, `/token`, JWT 발급/검증, 비밀번호 해시, 인증 테이블 추가 없이 기존 계약을 유지합니다.

현재 사용자 ID abstraction:
- `resolveAuthenticatedUserId()`
	- 현재는 `null` 반환(placeholder)
	- STEP 29에서 실제 인증 컨텍스트 주입 지점
- `resolveCurrentUserId()`
	- 인증 사용자 ID가 유효하면 우선 사용
	- 아니면 `BOOTSTRAP_USER_ID` fallback
- `resolveCurrentUserBootstrapContext()`
	- `{ userId, fallbackUser }`를 반환해 bootstrap 경계를 명확화

향후 인증 연결 지점:
- STEP 29에서 `resolveAuthenticatedUserId()`만 교체하면 됨
- `currentUser` state, History/Dashboard/Action Required 소비 로직은 그대로 재사용 가능

currentUser 흐름:
- `VITE_BOOTSTRAP_USER_ID` -> `resolveBootstrapUserId()` -> `BOOTSTRAP_USER_ID`
- `resolveAuthenticatedUserId()` -> `resolveCurrentUserId()` -> `resolveCurrentUserBootstrapContext()`
- `fetchCurrentUserById(userId)` -> `currentUser` -> `activeUser`

BUYER/SELLER 검증 결과:
1. BUYER
- User #2 (`MVP Buyer`, `BUYER`)로 Market/History/Dashboard/Action Required 동작 확인

2. SELLER
- `VITE_BOOTSTRAP_USER_ID=3` 환경으로 실행해 User #3 (`MVP Seller`, `SELLER`) 기준 역할 표시 및 History/Action Required 문구 분기 확인

3. 원복
- 기본 bootstrap 사용자를 Buyer #2 기준(`DEFAULT_USER_ID=2`)으로 유지

StrictMode 중복 호출 방지:
- 기존 module-level `CURRENT_USER_CACHE`, `CURRENT_USER_PROMISE_CACHE` 유지
- 최초 bootstrap 시 불필요한 중복 사용자 조회를 dedupe하도록 유지

오류 처리:
- `GET /users/{id}` 404/422/500 메시지 분기 유지
- 네트워크 오류 시 fallback 사용자로 계속 진행 + 사용자 안내 메시지 유지
- 개발자 디버깅용 `console.error` 유지

Backend/DB 무변경:
- Backend 코드 파일 수정 없음
- API 계약 변경 없음
- DB schema/migration/삭제/초기화 없음

Build 결과:
- `npm run build` 성공

STEP 29 준비 상태:
- 인증 컨텍스트 주입 위치가 `resolveAuthenticatedUserId()`로 고정됨
- 실제 인증 도입 시 user id 공급 경계만 교체하면 기존 거래/이력/대시보드 로직을 유지 가능

STEP 29 - 실제 인증 컨텍스트 연결 준비 및 최소 구현

목적:
- 실제 로그인/JWT를 구현하지 않고, 현재 bootstrap 사용자 흐름을 향후 인증 컨텍스트로 자연스럽게 교체할 수 있는 최소 인터페이스를 준비합니다.

인증 컨텍스트 추상화:
- `resolveAuthenticationContext()` 추가
- 현재는 다음 상태를 표현합니다.
	- `authenticated`
	- `unauthenticated`
	- `bootstrap`
- 실제 인증 정보가 없으면 `unauthenticated`에서 `bootstrap` 사용자로 안전하게 fallback합니다.

`resolveAuthenticatedUserId()` 역할:
- 향후 JWT / 세션 / 인증 Context가 user id를 공급할 단일 교체 지점입니다.
- STEP 29에서는 placeholder로 유지하며 실제 로그인 API는 구현하지 않습니다.

bootstrap fallback 구조:
- 우선순위는 다음과 같습니다.
	1. 인증 컨텍스트 user id
	2. `VITE_BOOTSTRAP_USER_ID`
	3. `DEFAULT_USER_ID`
- 인증 정보가 없으면 기본적으로 Buyer #2 bootstrap이 사용됩니다.

currentUser 연결 구조:
- `resolveAuthenticatedUserId()`
- `resolveAuthenticationContext()`
- `resolveCurrentUserId()`
- `resolveCurrentUserBootstrapContext()`
- `fetchCurrentUserById(userId)`
- `currentUser`
- `activeUser`

향후 JWT 연결 지점:
- 실제 인증 도입 시 `resolveAuthenticatedUserId()`만 교체하면 됩니다.
- History / Dashboard / Action Required / Market / 상세화면 소비 로직은 그대로 유지할 수 있습니다.

BUYER / SELLER 검증:
1. BUYER
- User #2 (`MVP Buyer`, `BUYER`) 기준으로 Market, History, MY/ALL, 검색, 필터, 정렬, Dashboard, Action Required, 상세 진입 확인

2. SELLER
- `VITE_BOOTSTRAP_USER_ID=3` 임시 실행으로 User #3 (`MVP Seller`, `SELLER`) 기준 역할 표시, History, MY/ALL, Dashboard, Action Required 확인
- 검증 후 기본 상태는 Buyer #2 유지

StrictMode dedupe 검증:
- 기존 `CURRENT_USER_CACHE`, `CURRENT_USER_PROMISE_CACHE` 유지
- bootstrap 기준 사용자 조회가 중복되지 않도록 유지

Backend 무변경:
- Backend 코드 수정 없음
- 기존 API 계약 유지 (`GET /users`, `GET /users/{user_id}`, `GET /deals` 등)
- `/users/me` 같은 신규 인증 API는 호출하지 않음

DB 보호:
- SQLite 초기화/삭제 없음
- 스키마 변경/migration 없음
- 기존 User / Deal / Order 삭제 없음
- 검증은 읽기 위주로 수행

빌드 결과:
- `npm run build` 성공

브라우저 검증 결과:
- BUYER #2 정상 표시 및 핵심 화면 회귀 없음
- SELLER #3 정상 표시 및 판매자 문구 분기 확인
- 콘솔 치명 오류 없이 동작 확인

STEP 30 준비 상태:
- 실제 로그인/JWT 도입 시 인증 컨텍스트에서 user id를 공급하도록 `resolveAuthenticatedUserId()`만 확장하면 됨
- 현재 bootstrap 기반 MVP 흐름은 유지하면서 인증 사용자로 치환할 경계가 준비됨

STEP 30 - 실제 로그인 인증의 최소 기반 구축 및 currentUser 연결

목적:
- 최소 로그인 UI와 로그인 검증 API를 추가해 `인증된 user_id -> currentUser -> activeUser` 연결을 실제로 동작시키되, 기존 거래 화면과 계산 로직은 유지합니다.

로그인 API:
- `POST /auth/login`
- Request:
	- `email`
	- `password`
- Response:
	- `user_id`
	- `name`
	- `role`
- 실패 응답:
	- 잘못된 이메일/비밀번호: `401`
	- 빈 이메일/비밀번호: `400`

로그인 UI:
- 기존 NME 화면을 재작성하지 않고 최소 로그인 패널을 추가했습니다.
- 로그인 전에는 이메일/비밀번호 입력과 `로그인`, `개발용 기본 사용자로 계속` 버튼을 표시합니다.

인증 사용자 연결:
- `resolveAuthenticatedUserId()`는 `sessionStorage`의 `nme_auth_user_id`를 읽습니다.
- 로그인 성공 시 저장된 `user_id`가 `resolveAuthenticationContext()` -> `resolveCurrentUserId()` -> `fetchCurrentUserById()` 흐름으로 연결됩니다.
- 기존 `currentUser`, `activeUser`, History, Dashboard, Action Required, Market 소비 구조는 유지됩니다.

session/local storage 사용 여부:
- `sessionStorage` 사용
- 저장 키: `nme_auth_user_id`
- 비밀번호 저장 없음

logout:
- 로그아웃 시 `nme_auth_user_id`를 제거합니다.
- 로그인 화면으로 복귀합니다.
- 이전 사용자의 History 필터/검색/정렬/상세 상태가 남지 않도록 사용자 전환 시 관련 view state를 초기화합니다.

BUYER 테스트:
- `bob@example.com / secret`
- 로그인 성공 후 `Buyer #2 · MVP Buyer · 역할: 구매자` 확인
- Market, History, MY/ALL, 검색, 필터, 정렬, Dashboard, Action Required, 상세 진입 확인

SELLER 테스트:
- `charlie@example.com / secret`
- 로그인 성공 후 `Seller #3 · MVP Seller · 역할: 판매자` 확인
- Market, History, MY/ALL, Dashboard, Action Required, 상세 진입 확인

인증 실패 테스트:
1. 빈 입력
- `이메일과 비밀번호를 입력해 주세요.` 표시

2. 잘못된 비밀번호
- `이메일 또는 비밀번호를 확인해 주세요.` 표시

3. 존재하지 않는 이메일
- `401` 응답 확인

기존 기능 회귀 테스트:
- 로그인 도입 후에도 Market, Deal Room, History, Dashboard, Action Required, BUYER/SELLER 역할 표시 유지
- History는 사용자 전환 시 기본값 `MY / ALL / 전체 / 최신순`으로 다시 초기화되도록 보정

SQLite 데이터 보호 결과:
- DB 초기화/삭제 없음
- 스키마 변경 없음
- 기존 User / Deal / Order 삭제 없음
- 로그인 검증은 기존 `users` 데이터(`bob@example.com`, `charlie@example.com`)를 재사용

build 결과:
- `npm run build` 성공

Swagger 결과:
- `/docs` 접속 정상
- `/auth/login` 경로가 OpenAPI/Swagger에 표시됨

발생한 오류와 해결 방법:
- 로그인 전환 검증 중 이전 사용자의 History 필터/범위 상태가 남는 현상을 확인
- 사용자 전환 시 History scope/filter/search/sort를 초기화하도록 최소 수정해 해결

STEP 31 준비 상태:
- 현재는 `sessionStorage` 기반 최소 인증 상태만 구현됨
- 다음 단계에서는 `resolveAuthenticatedUserId()`를 JWT/세션 기반으로 교체하고, 필요 시 `/auth/me` 또는 토큰 검증 구조를 연결할 수 있음

STEP 31 - 인증 상태 확인 API(/auth/me) 추가 및 currentUser 연결

STEP 31 목적:
- 로그인 후 Frontend가 현재 인증 사용자를 `GET /auth/me`로 직접 확인하고, 이를 `currentUser -> activeUser` 흐름에 연결합니다.
- JWT 없이도 향후 인증 방식만 교체할 수 있는 최소 인증 확인 경계를 추가합니다.

`/auth/me` 추가:
- Backend에 `GET /auth/me` 추가
- 현재 단계에서는 개발용 인증 헤더 `X-Auth-User-Id`를 통해 로그인 사용자 ID를 식별
- 응답은 기존 `UserResponse` 재사용

인증 사용자 helper:
- Backend `get_current_auth_user()` dependency 추가
- 현재는 `X-Auth-User-Id`를 읽어 사용자 조회
- STEP 32 이후 JWT/토큰 기반 인증으로 교체 가능한 지점으로 유지

Frontend currentUser 연결:
- 인증 세션(`sessionStorage`의 `nme_auth_user_id`)이 있으면 `fetchAuthenticatedCurrentUser()`가 `GET /auth/me`를 우선 호출
- 인증 세션이 없으면 기존 bootstrap fallback과 `GET /users/{id}` 구조 유지
- `currentUser`, `activeUser`, History / Dashboard / Action Required / Market 소비 로직은 그대로 유지

BUYER 검증:
- `bob@example.com / secret` 로그인 성공
- `GET /auth/me` -> `id=2`, `name=MVP Buyer`, `role=BUYER` 확인
- Market / History / MY / ALL / 검색 / 완료 필터 / 가격 정렬 / 상세 / Dashboard / Action Required 정상

SELLER 검증:
- `charlie@example.com / secret` 로그인 성공
- `GET /auth/me` -> `id=3`, `name=MVP Seller`, `role=SELLER` 확인
- Market / History / MY / ALL / 상세 / Dashboard / Action Required 정상

Logout 검증:
- 로그아웃 후 로그인 화면 복귀 확인
- `sessionStorage`에서 `nme_auth_user_id` 제거 확인
- 로그아웃 후 `GET /auth/me`는 `401` 확인

사용자 전환 검증:
- Buyer 로그인 -> Logout -> Seller 로그인 -> Logout -> Buyer 재로그인 순서 검증
- 사용자 전환 후 이전 사용자의 `currentUser`가 남지 않고 새 사용자 기준으로 Market / History / Dashboard / Action Required가 표시됨 확인

History 상태 초기화 검증:
- BUYER에서 `MY`, 검색 `9`, 완료 필터, 가격 높은순 적용 후 로그아웃
- SELLER 로그인 시 History 상태가 기본값으로 초기화됨 확인
- 사용자 전환 시 `scope`, `filter`, `search`, `sort`, `detail` 상태 초기화 유지

StrictMode 중복 호출 검증:
- 앱 자체 호출 기준 `GET /auth/me`
	- BUYER: 1회
	- SELLER: 1회
- 기존 `CURRENT_USER_CACHE`, `CURRENT_USER_PROMISE_CACHE` 유지
- `/auth/me`도 module-level dedupe cache로 중복 호출 방지

Swagger 검증:
- `/docs` 접속 정상
- `GET /auth/me`가 OpenAPI에 표시됨 확인
- 응답 schema는 `UserResponse` 사용

DB 보호 결과:
- DB 초기화/삭제 없음
- 스키마 변경 없음
- 기존 User / Deal / Order / Product 삭제 없음
- 최종 확인: `users = 8`, `deals = 18`, `orders = 12`

`npm run build` 결과:
- 성공

Browser Console 결과:
- 정상 BUYER/SELLER 경로에서는 치명 오류 없음
- 로그인 실패 테스트에서 발생한 `401`은 의도된 오류로 분리 확인

발생한 오류와 해결 방법:
- 사용자 전환 후 SELLER History가 BUYER의 이전 필터 상태를 유지하는 현상 재확인
- 사용자 전환 시 History 상태 초기화를 유지하도록 보정해 해결

STEP 32 준비 상태:
- Frontend는 인증 세션이 있으면 `/auth/me`를 우선 사용하도록 준비됨
- Backend는 `get_current_auth_user()` dependency만 교체하면 JWT/토큰 인증으로 확장 가능
- 기존 `/users/{id}` fallback과 거래 화면 구조는 유지됨

최종 판정:
- STEP 31 STATUS: COMPLETE

STEP 32 - JWT 기반 실제 인증 최소 전환

STEP 32 목적:
- STEP 31의 개발용 인증 헤더 기반 `/auth/me`를 JWT Bearer Token 기반 인증으로 최소 전환합니다.
- 기존 `currentUser -> activeUser -> NME UI` 구조는 유지하고, 인증 방식만 교체 가능한 상태로 분리합니다.

JWT 도입 이유:
- `X-Auth-User-Id` 개발용 인증을 정상 인증 경로에서 제거하고, 실제 토큰 기반 인증 흐름으로 전환하기 위함입니다.
- STEP 33 이후 refresh token, 권한 제어, 만료 갱신 등의 확장을 위한 기반입니다.

변경 파일:
- `nme_backend/app/main.py`
- `nme_backend/app/schemas.py`
- `nme_backend/requirements.txt`
- `nme_backend/.env`
- `nme_frontend/src/App.jsx`
- `README.md`

`POST /auth/login`:
- 기존 email/password 검증 유지
- 응답에 다음 필드 추가
	- `access_token`
	- `token_type`
	- `user_id`
	- `name`
	- `role`

`GET /auth/me`:
- `Authorization: Bearer <token>` 기반 인증으로 전환
- JWT의 `sub` claim으로 현재 사용자 ID를 복원
- 기존 `UserResponse`를 그대로 반환

JWT 인증 흐름:
- Login 화면
- `POST /auth/login`
- JWT access token 수신
- Frontend `sessionStorage`에 `nme_auth_token` 저장
- `GET /auth/me` 요청 시 `Authorization: Bearer <token>` 전송
- Backend `get_current_auth_user()`가 JWT 검증 후 사용자 조회
- `currentUser` -> `activeUser` 연결

Authorization Bearer 방식:
- 정상 인증 경로에서 `X-Auth-User-Id`는 더 이상 사용하지 않음
- Swagger/OpenAPI에서 `GET /auth/me`는 Bearer 인증 scheme으로 노출됨

Logout:
- `nme_auth_token` 삭제
- `nme_auth_user_id`도 함께 제거
- 로그인 화면 복귀
- 이전 사용자 History / 상세 상태 초기화 유지

401 처리:
- 로그인 실패 시 `이메일 또는 비밀번호를 확인해 주세요.`
- `/auth/me`의 401 발생 시 token 제거 후 로그인 화면으로 복귀하도록 처리
- 인증 만료/무효 토큰과 Network Error를 분리해 처리

BUYER 테스트:
- `bob@example.com / secret`
- `POST /auth/login` 200
- `access_token` 수신 확인
- `GET /auth/me` 200
- `id=2`, `name=MVP Buyer`, `role=BUYER` 확인
- Market / History / MY / ALL / 검색 / 완료 필터 / 가격 정렬 / 상세 / Dashboard / Action Required 정상

SELLER 테스트:
- `charlie@example.com / secret`
- `POST /auth/login` 200
- `access_token` 수신 확인
- `GET /auth/me` 200
- `id=3`, `name=MVP Seller`, `role=SELLER` 확인
- Market / History / MY / ALL / 상세 / Dashboard / Action Required 정상

Swagger 테스트:
- `/docs` 접속 정상
- `POST /auth/login` 확인
- `GET /auth/me` 확인
- OpenAPI에 `/auth/me`와 Bearer security scheme 노출 확인

DB 보호 결과:
- DB 초기화/삭제 없음
- 스키마 변경 없음
- 기존 User / Deal / Order / Product 삭제 없음
- 최종 확인: `users = 8`, `deals = 18`, `orders = 12`

`npm run build` 결과:
- 성공

Console 결과:
- 정상 BUYER/SELLER 경로에서는 치명 오류 없음
- 의도적인 인증 실패 테스트의 `401`만 기록됨

기존 기능 회귀 결과:
- Login / Logout
- Market
- History
- Dashboard
- Action Required
- BUYER / SELLER 역할 표시
- currentUser / activeUser 구조 유지

STEP 34 준비 상태:
- Backend는 `get_current_auth_user()` dependency만 교체하면 JWT 확장 정책을 수용 가능
- Frontend는 token 저장과 `/auth/me` 기반 currentUser 로딩 구조를 이미 사용하고 있어 refresh token 또는 `/auth/refresh` 단계로 확장 가능

STEP 34 - Refresh Token Rotation + Revoke 경계 구축

수정 파일:
- `nme_backend/app/main.py`
- `nme_backend/app/schemas.py`
- `nme_backend/.env`
- `nme_frontend/src/App.jsx`
- `README.md`

추가 파일:
- 없음

Refresh Token 구현:
- `POST /auth/login`이 이제 `access_token`과 `refresh_token`을 함께 반환합니다.
- Access Token payload:
	- `sub`
	- `type=access`
	- `exp`
- Refresh Token payload:
	- `sub`
	- `type=refresh`
	- `jti`
	- `exp`

`/auth/refresh`:
- `POST /auth/refresh`
- Request: `refresh_token`
- 검증 순서:
	- JWT decode
	- signature 확인
	- exp 확인
	- `type == refresh` 확인
	- `sub` 확인
	- DB 사용자 존재 확인
- 성공 시 새 `access_token`과 `token_type` 반환
- STEP 34에서는 성공 시 새 `refresh_token`도 함께 반환
- 기존 refresh token은 즉시 revoke 처리되어 재사용할 수 없음

Access Token / Refresh Token 구조:
- `POST /auth/login` → `access_token`, `refresh_token`, `token_type`, `user_id`, `name`, `role`
- `GET /auth/me`는 Access Token만 허용
- Refresh Token으로 `GET /auth/me` 접근 시 `401`
- `POST /auth/refresh`는 Refresh Token만 허용

Refresh Token Rotation / Reuse 방지:
- `R1` 사용 → `R2` 발급 + `R1` revoke
- `R1` 재사용 → `401`
- `R2` 사용 → `R3` 발급 + `R2` revoke
- 이전 refresh token 재사용 차단을 위해 `jti` 기반 메모리 revoke store 사용

Refresh Token revoke:
- Backend는 메모리 기반 `ACTIVE_REFRESH_TOKEN_JTIS` / `REVOKED_REFRESH_TOKEN_JTIS`를 사용
- 서버 재시작 시 초기화되는 MVP 제한이 있으며, 실서비스에서는 Redis/DB 기반 revoke store가 필요

Frontend 저장 방식:
- `sessionStorage`
- `nme_auth_token`
- `nme_refresh_token`
- `nme_auth_user_id`
- 비밀번호 저장 없음

401 자동 refresh:
- 인증된 API 요청이 `401`이면 즉시 로그인 화면으로 가지 않음
- 먼저 `POST /auth/refresh` 호출
- 성공 시 새 access token, 새 refresh token 저장 후 원래 API 요청 재시도
- 실패 시 인증 정보 전체 삭제 후 로그인 화면 복귀

refresh promise dedupe:
- Frontend module-level `AUTH_REFRESH_PROMISE`로 refresh 중복 요청 방지
- 동시에 여러 인증 요청이 `401`이 되어도 refresh 요청은 하나만 유지하도록 구현

Logout:
- `POST /auth/logout`으로 현재 refresh token revoke 시도
- 이후 `nme_auth_token`, `nme_refresh_token`, `nme_auth_user_id` 삭제
- 로그인 화면 복귀
- 사용자 전환 시 History scope/filter/search/sort/detail 상태 초기화 유지

BUYER 검증:
- `bob@example.com / secret`
- `POST /auth/login` 200
- `access_token` 존재
- `refresh_token` 존재
- `GET /auth/me` 200
- `id=2`, `name=MVP Buyer`, `role=BUYER`
- Market / History / MY / ALL / Dashboard / Action Required 정상

SELLER 검증:
- `charlie@example.com / secret`
- `POST /auth/login` 200
- `access_token` 존재
- `refresh_token` 존재
- `GET /auth/me` 200
- `id=3`, `name=MVP Seller`, `role=SELLER`
- Market / History / MY / ALL / Dashboard / Action Required 정상

인증 실패 검증:
1. Access Token 없음 → `/auth/me` 401
2. 잘못된 Access Token → `/auth/me` 401
3. 만료된 Access Token → `/auth/me` 401
4. Refresh Token 없음 → `/auth/refresh` 401
5. 잘못된 Refresh Token → `/auth/refresh` 401
6. 만료된 Refresh Token → `/auth/refresh` 401
7. Access Token을 refresh token 자리에 사용 → `/auth/refresh` 401
8. Refresh Token을 `/auth/me`에 사용 → 401
9. 이미 사용된 이전 Refresh Token 재사용 → `/auth/refresh` 401
10. Logout 후 기존 Refresh Token 사용 → `/auth/refresh` 401

데이터 보호 결과:
- DB 초기화/삭제 없음
- migration 없음
- 기존 User / Deal / Order / Product 삭제 없음
- 최종 확인: `users = 8`, `deals = 19`, `orders = 13`, `products = 4`

`npm run build`:
- 성공

Swagger:
- `/docs` 정상
- `POST /auth/login`, `GET /auth/me`, `POST /auth/refresh`, `POST /auth/logout` 노출 확인
- Bearer security scheme 확인

Browser Console:
- 정상 BUYER/SELLER 경로에서 치명 오류 없음
- 의도적으로 발생시킨 인증 실패의 `401`만 기록됨

발생한 오류와 해결 방법:
- `/auth/logout` endpoint가 `get_current_auth_user`보다 먼저 선언되어 backend reload 시 `NameError`가 발생함
- endpoint 선언 순서를 dependency 아래로 이동해 해결
- `/auth/refresh`가 새 refresh token을 반환해도 response schema가 필드를 누락해 잘려나가던 문제를 수정함
- `authFetch()` + `refreshAccessToken()` + `AUTH_REFRESH_PROMISE` 구조로 1회 refresh 후 원래 요청을 재시도하도록 유지

보안상 주의사항:
- Access Token은 stateless JWT로 유지됨
- Refresh Token 원문은 DB에 저장하지 않음
- 메모리 revoke store는 서버 재시작 시 초기화됨
- 실서비스에서는 Redis/DB 기반 revoke store와 세션 관리가 필요

STEP 35 준비 상태:
- 현재는 메모리 기반 revoke store를 사용하므로 다음 단계에서는 Redis 또는 DB 기반 refresh session 저장소를 도입할 수 있음
- refresh token rotation, reuse 차단, logout revoke 경계는 이미 분리되어 있어 장치별 세션 관리나 token family 확장으로 이어갈 수 있음

STEP 36 - DB 기반 Authentication Session Management

목적:
- STEP 35의 DB 기반 AuthSession을 확장해 사용자 세션 조회/회수(Session Management) 최소 API를 구축
- 기존 거래 기능과 거래 데이터는 변경하지 않고 인증 경계만 강화

Backend 변경 요약:
- AuthSession 전용 CRUD 확장
	- create_auth_session
	- get_auth_session_by_refresh_jti
	- get_active_auth_sessions_by_user
	- revoke_auth_session
	- revoke_all_auth_sessions_for_user
- 신규 인증 API 추가
	- GET /auth/sessions
	- POST /auth/sessions/{session_id}/revoke
	- POST /auth/sessions/revoke-all
- refresh rotation 유지 + DB AuthSession source-of-truth 유지
- access token에 sid(session id)를 포함해 현재 세션(is_current) 판별 정확도 보강

AuthSession 변경 결과:
- 모델 필드는 과도 확장 없이 기존 유지
	- id, user_id, refresh_jti, expires_at, revoked_at, created_at
- last_used_at, revoked_reason는 이번 단계에서 추가하지 않음

세션 관리 API 결과:
1. GET /auth/sessions
- 현재 로그인 사용자 자신의 활성 세션만 반환
- 응답 필드: id, created_at, expires_at, is_current
- refresh_token/refresh_jti/password 미노출

2. POST /auth/sessions/{session_id}/revoke
- 자신의 세션은 revoke 성공: {"status":"revoked"}
- 이미 revoke된 세션은 {"status":"already_revoked"}
- 다른 사용자 세션 id 시도는 404로 차단

3. POST /auth/sessions/revoke-all
- 현재 사용자 활성 세션 전체 revoke
- 응답: {"status":"all_sessions_revoked"}
- 다른 사용자 세션에는 영향 없음

테스트 결과:
- Buyer 로그인(bob@example.com/secret): 200
- Seller 로그인(charlie@example.com/secret): 200
- Buyer의 GET /auth/sessions: 200, 타 사용자 소유 세션 포함 0건
- Buyer로 Seller session revoke 시도: 404 (차단)
- Buyer 자신의 세션 revoke 후 해당 refresh 재사용: 401
- revoke-all 후 Buyer refresh: 401, Seller refresh: 200
- Rotation 회귀:
	- R1 -> refresh -> R2: 200
	- R1 재사용: 401
	- R2 -> refresh -> R3: 200
	- R2 재사용: 401
- Logout 회귀:
	- logout: 200
	- 기존 refresh 재사용: 401
- 서버 재시작 회귀:
	- 재시작 전 revoke된 refresh: 재시작 후 401
	- 재시작 전 active refresh: 재시작 후 200

기존 거래 기능 보존:
- Market / History / Dashboard / Action Required / BUYER / SELLER 화면 회귀 없음
- 인증 경계 변경으로 거래 API 동작 변경 없음

최종 DB 수량:
- users = 8
- deals = 19
- orders = 13
- products = 4
- auth_sessions = 22

Swagger 결과:
- /docs 노출 확인
- POST /auth/login
- GET /auth/me
- POST /auth/refresh
- POST /auth/logout
- GET /auth/sessions
- POST /auth/sessions/{session_id}/revoke
- POST /auth/sessions/revoke-all
- 세션 관리 3개 endpoint 모두 Bearer 인증 적용 확인

Build 결과:
- Backend: python -m compileall app 성공
- Frontend: npm run build 성공

Browser Console 결과:
- Buyer/Seller 로그인, Market, 거래 관리, 거래 이력, Dashboard/Action Required, Logout 경로에서 치명 콘솔 오류 없음

발생한 오류와 해결 방법:
- uvicorn --reload 재기동 중 포트 점유/리로더 프로세스 충돌이 발생
- 기존 점유 프로세스를 종료하고 non-reload 모드로 재기동해 안정적으로 검증 수행

STEP 37 준비 상태:
- 세션 관리 API 최소 기능이 완성되어, 다음 단계에서 장치 식별/세션 메타데이터/관리 UI 확장 준비 완료

STEP 37 - AuthSession last_used_at 기반 세션 품질 개선

변경 파일:
- nme_backend/app/models.py
- nme_backend/app/schemas.py
- nme_backend/app/crud.py
- nme_backend/app/main.py
- nme_frontend/README.md

추가 파일:
- 없음

AuthSession 변경 내용:
- `last_used_at` 필드 추가 (모델 기준 `nullable=False`, `server_default=func.now()`)
- 기존 SQLite 데이터 보존을 위해 DB reset 없이 in-place 컬럼 추가/백필 적용
	- 컬럼 미존재 시 `ALTER TABLE auth_sessions ADD COLUMN last_used_at DATETIME`
	- 기존 행의 `last_used_at`이 NULL이면 `COALESCE(created_at, expires_at, CURRENT_TIMESTAMP)`로 백필
- 신규 세션 생성 시 `created_at`과 함께 `last_used_at`도 현재 UTC로 기록

세션 관리 동작:
- `POST /auth/refresh` 성공 시
	- 기존 refresh 세션 `last_used_at` 갱신
	- 기존 세션 revoke
	- 새 refresh/session 생성(회전 정책 유지)
- `GET /auth/sessions`는 활성 세션만 반환
	- `revoked_at IS NULL`
	- `expires_at > now`
	- 응답 필드: `id`, `created_at`, `last_used_at`, `expires_at`, `is_current`
	- 민감 정보(`refresh_token`, `refresh_jti`, `password`) 미노출
- `is_current`는 access token의 `sid` 기반 판별 유지

검증 결과 요약:
- Rotation
	- R1 -> refresh -> R2: 200
	- R1 재사용: 401
	- R2 -> refresh -> R3: 200
	- R2 재사용: 401
- revoke
	- 본인 세션 revoke: 200
	- 타 사용자 세션 revoke 시도: 404(차단)
- revoke-all
	- Buyer revoke-all 후 Buyer refresh: 401
	- 같은 시점 Seller active refresh: 200
- logout
	- logout 200
	- 기존 refresh 재사용 401
- 재시작 내구성
	- 서버 재시작 후 revoked refresh: 401
	- 서버 재시작 후 active refresh: 200

Buyer/Seller 검증:
- Buyer 로그인/`/auth/me`/`/auth/sessions` 정상
- Seller 로그인/`/auth/me`/`/auth/sessions` 정상
- Market/거래 관리/거래 이력/Dashboard/Action Required/Logout 회귀 없음

인증 실패 테스트:
- access token 없음 `/auth/me` -> 401
- invalid access token -> 401
- expired access token -> 401
- refresh token 없음 `/auth/refresh` -> 401
- invalid refresh token -> 401
- expired refresh token -> 401
- access token을 refresh token 자리에 사용 -> 401
- refresh token을 `/auth/me`에 사용 -> 401
- revoke된 refresh token -> 401
- rotation으로 이전 refresh token 재사용 -> 401
- 타 사용자 session revoke 시도 -> 404

DB 보호 결과:
- 거래 데이터 불변 유지
	- users = 8
	- deals = 19
	- orders = 13
	- products = 4
- AuthSession 집계(최종):
	- total = 35
	- active = 8
	- revoked = 27
	- expired = 0
	- last_used_at NULL = 0

빌드/문서:
- Backend compile: `python -m compileall app` 성공
- Swagger/OpenAPI: 세션 관리 포함 auth endpoints 노출 + Bearer 적용 확인
- Frontend: `npm run build` 성공

Browser Console:
- 정상 BUYER/SELLER 경로에서 치명 runtime 에러 징후 없음
- 의도적 인증 실패(401)는 정상 동작으로 확인

발생한 오류와 해결:
- SQLite에서 `ALTER TABLE ... ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP` 실패
	- 원인: SQLite는 ADD COLUMN 시 non-constant default 제한
	- 해결: nullable 컬럼 추가 후 기존 데이터 백필 방식으로 전환(데이터 보존)

기존 STEP 1~36 보존 여부:
- 보존됨 (거래/주문/상품/사용자 도메인 및 API 미변경)

STEP 38 준비 상태:
- 세션 품질(마지막 사용 시각/활성 세션 필터/재시작 내구성) 기반이 정리되어
	다음 단계에서 세션 정리 정책(예: 만료 세션 cleanup)이나 UI 확장 검토 가능

최종 STATUS:
- STEP 37 STATUS: COMPLETE

STEP 38 - AuthSession Cleanup Policy

1. 수정한 파일
- nme_backend/app/crud.py
- nme_backend/app/main.py
- nme_backend/app/schemas.py
- nme_backend/.env
- nme_frontend/README.md

2. 추가한 파일
- 없음

3. cleanup 정책
- AuthSession 정리 대상을 "오래된 expired 세션" 또는 "오래된 revoked 세션"으로 제한
- cleanup은 오직 auth_sessions 데이터에만 적용
- 활성 세션은 cleanup 대상에서 제외

4. retention 기간
- 환경변수 기반: AUTH_SESSION_CLEANUP_RETENTION_DAYS
- 기본값: 1

5. cleanup 대상 조건
- expired: expires_at <= now - retention_days
- revoked: revoked_at IS NOT NULL AND revoked_at <= now - retention_days

6. 활성 session 보호 결과
- cleanup 직전/직후 active 세션 수 동일 확인: 13 -> 13
- 활성 세션 삭제 없음

7. refresh rotation 검증
- R1 -> refresh -> R2: 200
- R1 재사용: 401
- R2 -> refresh -> R3: 200
- R2 재사용: 401

8. logout 검증
- logout: 200
- logout 후 기존 refresh 재사용: 401

9. 서버 재시작 검증
- 재시작 후 revoked refresh: 401
- 재시작 후 active refresh: 200

10. BUYER 검증
- login 200
- /auth/me 200
- /auth/sessions 200
- Market / History / Dashboard / Action Required 화면 정상 확인

11. SELLER 검증
- login 200
- /auth/me 200
- /auth/sessions 200
- Market / History / Dashboard / Action Required 화면 정상 확인

12. SQLite 최종 수량
- users = 8
- deals = 19
- orders = 13
- products = 4

13. AuthSession 최종 수량
- total = 46
- active = 13
- revoked = 33
- expired = 0

14. Swagger 결과
- /auth/sessions/cleanup 노출 확인
- cleanup endpoint에 Bearer 보안 적용 확인
- 기존 auth endpoints 유지 확인

15. npm run build 결과
- 성공

16. Browser Console 결과
- 정상 BUYER/SELLER 경로 점검 중 치명적 runtime/CORS/500 징후 없음
- 의도적 인증 실패(401)는 정상 동작으로 확인

17. 기존 STEP 1~37 기능 보존 여부
- 보존됨
- 거래/주문/상품/사용자 도메인 로직 및 기존 인증 동작 유지

18. 발생한 오류와 해결 방법
- 특이 오류 없음
- 비관리자 cleanup 호출은 의도대로 403(Admin role required)로 차단됨

19. STEP 39 준비 상태
- 세션 cleanup 정책 기반이 마련되어 다음 단계에서 수동 운영 절차 고도화나 모니터링 확장 검토 가능

20. 최종 판정
- STEP 38 STATUS: COMPLETE

