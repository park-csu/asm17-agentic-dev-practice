import { describe, expect, it } from "vitest";

import { getCompactFallbackReason, getFallbackReason } from "./fallbackReason";

describe("fallback reason formatter", () => {
  it("시간 겹침과 위치 이동 불가 사유를 사용자용 문장으로 요약한다", () => {
    const reason =
      "시작 시간(10:30)이 종료 시간(11:30)보다 60분 앞서지만, 이전 일정(아침밥 만들기) 종료 시간(10:00) 대비 이동 시간 30분으로 서울에서 부산까지 이동이 물리적으로 불가능합니다. 또한 다음 일정(발표자료 준비 및 리허설)과 시간대가 완전히 겹칩니다(11:30-12:30). 장소 도착이 필수라는 사용자 답변에 따라 이동 시간 부족으로 invalid 처리합니다";

    const result = getFallbackReason(reason);

    expect(result).toBe(
      "기존 일정(발표자료 준비 및 리허설)과 시간이 겹치고, 직전 일정 후 서울에서 부산까지 30분 안에 이동할 수 없습니다.",
    );
    expect(result).not.toContain("invalid 처리");
    expect(result).not.toContain("시작 시간(10:30)");
  });

  it("캘린더와 사이드바용 짧은 사유를 반환한다", () => {
    const reason =
      "이전 일정(아침밥 만들기) 종료 시간(10:00) 대비 이동 시간 30분으로 서울에서 부산까지 이동이 물리적으로 불가능합니다. 또한 다음 일정(발표자료 준비 및 리허설)과 시간대가 완전히 겹칩니다(11:30-12:30).";

    expect(getCompactFallbackReason(reason)).toBe("시간 겹침 및 이동 시간 부족");
  });

  it("요청 한도 오류를 사용자가 이해할 수 있는 문장으로 바꾼다", () => {
    expect(getFallbackReason("Error code: 429 - too_many_requests")).toBe(
      "AI 검증 요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.",
    );
    expect(getCompactFallbackReason("Error code: 429 - too_many_requests")).toBe("AI 요청 한도 초과");
  });

  it("빈 사유에는 기본 안내를 반환한다", () => {
    expect(getFallbackReason("  ")).toBe("일정 상세 내용을 더 구체적으로 작성 후 재시도하세요.");
    expect(getCompactFallbackReason("  ")).toBe("정보 부족");
  });
});
