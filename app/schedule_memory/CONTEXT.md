# app/schedule_memory 패키지 컨텍스트

`app/schedule_memory`는 TaskPilot의 향후 유사 일정 검색과 개인화 task 패턴 추천을 위한 확장 후보 패키지입니다.

현재 MVP 핵심 실행 경로에서는 사용하지 않습니다. 일정 서브태스크 생성 에이전트의 기본 동작은 `app/schedule_agent`가 담당하며, 현재 일정 입력값과 LangGraph State를 기준으로 task를 생성합니다.

이 패키지는 ChromaDB와 Upstage 임베딩을 사용해 일정 패턴 예시를 벡터화하고, 입력 일정과 의미상 유사한 일정 패턴을 검색하는 구조를 보관합니다.

현재 데이터:
- `data/schedule_memory_examples.json`: 발표, 회의, 시험, 해커톤, 멘토링 같은 일정 패턴 샘플

현재 모듈:
- `chroma.py`: ChromaDB 클라이언트 생성
- `embedding.py`: Upstage 임베딩을 ChromaDB embedding function 인터페이스에 맞추는 어댑터
- `vector_store.py`: 일정 패턴 샘플 seed 및 유사 문서 검색

환경 및 실행 설정:
- `.env.example`의 `CHROMA_MODE`, `CHROMA_HOST`, `CHROMA_PORT`를 사용합니다.
- Docker Compose의 `chroma_data` 볼륨은 로컬 ChromaDB 저장소를 유지하기 위한 협업용 기본 설정입니다.
- 현재 핵심 API 실행에서는 이 설정이 없어도 일정 에이전트는 동작하지만, 확장 개발자가 같은 구조로 실험할 수 있도록 유지합니다.

주의사항:
- 이 패키지는 현재 API나 LangGraph 노드에서 import하지 않습니다.
- PostgreSQL 기반 사용자, 일정, task 저장은 이 패키지의 책임이 아닙니다.
- 실제 개인화 기능이 도입되기 전까지는 핵심 기능 의존성으로 연결하지 않습니다.
