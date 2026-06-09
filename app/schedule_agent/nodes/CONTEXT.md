# app/schedule_agent/nodes 패키지 컨텍스트

`nodes`는 LangGraph에 등록되는 일정 에이전트 노드 함수를 담습니다.

노드는 상태 일부를 입력으로 받고 변경된 상태 일부를 dict로 반환합니다. 외부 저장소에 직접 저장하지 않습니다.

## pre_validate 노드

입력 일정이 에이전트가 처리할 수 있는 수준인지 사전 검증합니다.

- 완전히 비어 있거나 의미 없는 1-2단어 입력만 `is_valid=False`로 반환합니다.
- 불분명하거나 맥락이 부족한 입력은 `needs_question=True`로 전환해 사용자에게 추가 질문을 요청합니다.
- LLM이 `is_valid=False`를 반환했지만 이유가 없으면 `needs_question=True`로 변환합니다.
- `prompts.PRE_VALIDATE_SYSTEM`에서 검증 기준 프롬프트를 관리합니다.
