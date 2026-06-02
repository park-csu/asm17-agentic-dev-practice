# ADR-001: ChromaDB 기반 일정 메모리 후보 패키지 분리

## Status
Accepted

## Context
TaskPilot MVP는 현재 일정 하나의 제목, 상세 내용, 시작 시간, 종료 시간, 사용자 보충 답변을 바탕으로 실행 가능한 task를 생성합니다. 이 단계에서는 장기 기억이나 과거 일정 전체를 학습하는 기능이 필요하지 않습니다.

하지만 향후에는 사용자의 반복 일정, 자주 사용하는 task 패턴, 비슷한 과거 일정의 분해 방식 등을 참고해 개인화된 task 생성을 제공할 수 있습니다. 이 경우 의미 기반 검색을 위한 벡터 DB가 확장 후보가 될 수 있습니다.

기존 ChromaDB 코드는 `app/core/database.py`, `app/core/embedding.py`, `app/vector_store.py`에 흩어져 있었고, 파일명도 PostgreSQL 저장소 도입 시 혼동을 만들 수 있었습니다.

## Decision
- ChromaDB 기반 벡터 메모리 후보 코드를 `app/schedule_memory` 패키지로 분리한다.
- `app/core/database.py` 이름은 향후 PostgreSQL 연결 코드에 사용할 수 있도록 비워둔다.
- 의료 QA 샘플 데이터는 제거하고 TaskPilot 일정 패턴 샘플인 `data/schedule_memory_examples.json`으로 교체한다.
- 현재 MVP 핵심 실행 경로에서는 `app/schedule_memory`를 import하지 않는다.
- 협업과 확장 개발을 위해 `CHROMA_*` 환경변수와 Docker Compose의 `chroma_data` 볼륨은 유지한다.

## Consequences
- 일정 생성 MVP와 유사 일정 검색 확장 후보의 책임 경계가 명확해진다.
- PostgreSQL 저장소 도입 시 `app/core/database.py` 또는 별도 DB 패키지를 자연스럽게 사용할 수 있다.
- ChromaDB는 현재 기능 필수 구성요소가 아니라 확장 후보임이 문서와 코드 구조에 드러난다.
- 기본 Docker Compose 실행 시 ChromaDB 저장 볼륨이 함께 생성될 수 있지만, 현재 API가 해당 패키지를 import하지 않으므로 핵심 기능 동작에는 영향을 주지 않는다.
- 향후 개인화 기능을 실제로 도입할 때는 저장할 사용자 데이터 범위, 개인정보 처리, PostgreSQL 데이터와 벡터 메모리의 동기화 방식을 다시 결정해야 한다.
