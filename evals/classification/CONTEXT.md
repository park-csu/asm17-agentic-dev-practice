# classification 평가 컨텍스트

`evals/classification`은 일정 에이전트의 classification 노드가 실제 LLM 환경에서 일정의 task 분해 필요성과 맥락 충분성을 원하는 기준으로 판단하는지 측정합니다.

평가 대상은 그래프 전체가 아니라 `app.schedule_agent.nodes.classification.classify_schedule` 함수입니다.

저장소에는 합성·익명화된 평가 케이스와 평가 코드를 커밋합니다. 실제 사용자 일정, API 키, 실행 결과 파일은 커밋하지 않습니다.

평가 결과는 초기 단계에서 리포트 용도로만 사용하며 CI 실패 기준으로 사용하지 않습니다. 기본 5회 반복하고 모든 케이스가 5회 모두 통과해야 안정적인 결과로 판단합니다.

평가 케이스는 단일 행동 일정, 분해 가능하고 맥락이 충분한 일정, 분해 가능하지만 추가 질문이 필요한 일정, classification retry 소진 흐름을 포함합니다.
