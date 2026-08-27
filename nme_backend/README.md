# nme_backend

간단한 FastAPI + SQLAlchemy + SQLite MVP 백엔드입니다.

## 설치

```bash
cd nme_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

개발환경 표준 실행은 프로젝트 루트의 `start_nme.bat` 사용을 권장합니다.

## 접속

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## STEP 4 — Order 기능 (MVP)

간단한 거래 요청(Order) 기능이 추가되었습니다.

API 목록:

- `POST /orders` : 거래 요청 생성
- `GET /orders` : 거래 요청 목록 조회
- `GET /orders/{order_id}` : 거래 요청 상세 조회

실행 및 테스트:

```bash
cd nme_backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Swagger: http://127.0.0.1:8000/docs

## STEP 10 — Final verification and stability checks

간단한 통합 검사를 통해 STEP 1~9의 기능이 정상 동작하는지 확인합니다.

- 실행: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
- Swagger: http://127.0.0.1:8000/docs
- 통합 테스트 스크립트(선택): `step10_integration_test.py` — 기본 시나리오를 자동 점검합니다.
- 간단한 정적 프론트엔드: `static/index.html` 추가됨 — 서버 실행 후 `http://127.0.0.1:8000/` 에서 접속하면 `GET /health` 및 `GET /market` 호출을 테스트할 수 있습니다.
- 핵심 검사: `GET /health`, `GET /market`, `POST /deals`, `PATCH /deals/{id}/status`, `POST /deals/{id}/create-order`, `PATCH /orders/{id}/status`, `GET /deals/{id}/completion`

주의: 기존 데이터(`nme.db`)는 절대 삭제하거나 초기화하지 마세요. 테스트는 신규 리소스를 생성하거나 안전하게 상태를 변경하도록 설계되어 있습니다.

간단 테스트 시나리오:

1. `GET /products/1` 으로 기존 상품 확인
2. `POST /orders` 로 주문 생성: `{ "product_id":1, "buyer_id":2, "quantity":50, "price":3200000 }`
3. `GET /orders` 로 주문 목록 확인
4. `GET /orders/1` 로 상세 확인

## STEP 5 — Order Status Update

주문 상태 변경 기능이 추가되었습니다.

엔드포인트:

- `PATCH /orders/{order_id}/status` : 주문 상태 변경

상태 흐름 (허용된 전환):

- PENDING → ACCEPTED → PAID → SHIPPED → COMPLETED
- 취소: PENDING → CANCELLED, ACCEPTED → CANCELLED

테스트 방법: Swagger에서 `PATCH /orders/{order_id}/status` 를 사용하여 상태 전환을 시도하세요.

## STEP 6 — Market API

간단한 Market 조회 API가 추가되었습니다. Product 테이블의 `status == "available"` 인 항목만 반환합니다.

- `GET /market` : 현재 거래 가능한 상품 목록 반환

Swagger: http://127.0.0.1:8000/docs

## STEP 7 — Deal (거래 제안) 기능

간단한 Deal(거래 제안) 기능이 추가되었습니다. Market의 상품을 선택한 구매자가 거래 제안을 생성하고 협상 상태를 관리할 수 있습니다.

엔드포인트:

- `POST /deals` : 거래 제안 생성
- `GET /deals` : 거래 제안 목록 조회
- `GET /deals/{deal_id}` : 거래 제안 상세 조회
- `PATCH /deals/{deal_id}/status` : 거래 제안 상태 변경

Deal 상태:

- `NEGOTIATING` (기본)
- `AGREED`
- `REJECTED`
- `CANCELLED`

허용된 상태 전환:

- `NEGOTIATING` → `AGREED` / `REJECTED` / `CANCELLED`

주의: 이번 단계에서는 Deal이 자동으로 Order로 변환되지는 않습니다.

## STEP 8 — Create Order from AGREED Deal

AGREED 상태의 Deal을 기반으로 실제 Order를 생성하는 기능이 추가되었습니다.

 - STEP 9: Deal → Order → 거래 완료 흐름 검증 API 추가.
	 - GET /deals/{deal_id}/order : 해당 Deal로 생성된 Order 조회 (없으면 404).
	 - GET /deals/{deal_id}/completion : Order의 현재 상태와 `completed` 불리언 반환.
	 - 기존 `PATCH /orders/{order_id}/status`를 사용해 상태를 순차적으로 `ACCEPTED -> PAID -> SHIPPED -> COMPLETED`로 진행하면 최종적으로 `completed: true`가 됩니다.
	 - 잘못된 상태 전환은 400으로 차단됩니다. 예: COMPLETED -> PENDING은 허용되지 않습니다.

Swagger: http://127.0.0.1:8000/docs

