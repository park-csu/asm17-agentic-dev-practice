# ask_context 평가 컨텍스트

`evals/ask_context`는 추가 질문 노드가 사용자 답변을 누적 컨텍스트에 반영하거나 질문 응답 상태를 반환하는 상태 전이를 검증합니다.

평가 대상은 그래프 전체가 아니라 `app.schedule_agent.nodes.ask_context.ask_context` 함수입니다.

`ask_context`는 LLM을 호출하지 않는 결정적 노드입니다. 따라서 이 평가는 실제 LLM 품질 평가가 아니라, classification 질문과 pre_validate 질문이 같은 상태 전달 규칙을 따르는지 확인하는 회귀 평가입니다.

평가 케이스는 classification 답변 누적, pre_validate 답변 누적, classification 질문 반환, pre_validate 질문 반환을 포함합니다.
