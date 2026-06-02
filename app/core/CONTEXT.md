# app/core 패키지 컨텍스트

`app/core`는 여러 노드와 API에서 공유하는 기반 기능을 담습니다.

현재 일정 에이전트가 직접 사용하는 핵심 기능은 `llm.py`의 `get_llm()`입니다.

PostgreSQL 저장, 인증, 캘린더 연동은 다음 단계에서 필요할 때 이 패키지에 추가합니다.

ChromaDB 기반 벡터 메모리 후보 코드는 `app/schedule_memory` 패키지에 분리되어 있습니다. `app/core`의 데이터베이스 파일명은 이후 PostgreSQL 연결 코드에 사용할 수 있도록 비워둡니다.
