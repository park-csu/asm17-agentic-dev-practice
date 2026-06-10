const DEFAULT_FALLBACK_REASON = "일정 상세 내용을 더 구체적으로 작성 후 재시도하세요.";
const RATE_LIMIT_REASON = "AI 검증 요청 한도를 초과했습니다. 잠시 후 다시 시도하세요.";

type ReasonSummary = {
  normalized: string;
  isRateLimit: boolean;
  hasOverlap: boolean;
  hasTravelProblem: boolean;
  hasInvalidRange: boolean;
  overlapTitle: string;
  previousTitle: string;
  routeFrom: string;
  routeTo: string;
  gapMinutes: string;
};

export function getFallbackReason(reason: string): string {
  const summary = summarizeReason(reason);
  if (!summary.normalized) {
    return DEFAULT_FALLBACK_REASON;
  }
  if (summary.isRateLimit) {
    return RATE_LIMIT_REASON;
  }

  const detail = buildDetailReason(summary);
  return detail || summary.normalized;
}

export function getCompactFallbackReason(reason: string): string {
  const summary = summarizeReason(reason);
  if (!summary.normalized) {
    return "정보 부족";
  }
  if (summary.isRateLimit) {
    return "AI 요청 한도 초과";
  }

  const items = [
    summary.hasOverlap ? "시간 겹침" : "",
    summary.hasTravelProblem ? "이동 시간 부족" : "",
    summary.hasInvalidRange ? "시간 설정 오류" : "",
  ].filter(Boolean);

  return items.length > 0 ? items.join(" 및 ") : "일정 생성 실패";
}

function summarizeReason(reason: string): ReasonSummary {
  const normalized = normalizeReason(reason);
  const routeMatch = normalized.match(/([가-힣A-Za-z\s]+?)에서\s*([가-힣A-Za-z\s]+?)까지\s*이동/);

  return {
    normalized,
    isRateLimit: isRateLimitReason(normalized),
    hasOverlap: /(겹칩니다|겹칩|겹치|시간대가 완전히 겹)/.test(normalized),
    hasTravelProblem: /(이동.*불가능|이동.*부족|물리적으로 불가능|이동할 수 없)/.test(normalized),
    hasInvalidRange: /시작 시간은 종료 시간보다 빨라야/.test(normalized),
    overlapTitle:
      extractFirstMatch(normalized, /다음 일정\(([^)]+)\)/) ||
      extractFirstMatch(normalized, /기존 일정\(([^)]+)\)/) ||
      extractFirstMatch(normalized, /기존 일정과 시간이 겹칩니다\.\s*\(([^)]+)\)/),
    previousTitle: extractFirstMatch(normalized, /이전 일정\(([^)]+)\)/),
    routeFrom: routeMatch ? cleanRoutePlace(routeMatch[1]) : "",
    routeTo: routeMatch ? cleanRoutePlace(routeMatch[2]) : "",
    gapMinutes: extractFirstMatch(normalized, /이동 시간\s*(\d+)\s*분/),
  };
}

function buildDetailReason(summary: ReasonSummary): string {
  const details = [
    buildOverlapDetail(summary),
    buildTravelDetail(summary),
    buildInvalidRangeDetail(summary),
  ].filter((item): item is string => Boolean(item));

  if (details.length === 0) {
    return "";
  }
  if (summary.hasOverlap && summary.hasTravelProblem && details.length >= 2) {
    return `${toConnectiveClause(details[0])}고, ${details[1]}`;
  }
  return dedupe(details).join(" ");
}

function normalizeReason(reason: string): string {
  return reason.trim().replace(/\s+/g, " ");
}

function isRateLimitReason(reason: string): boolean {
  return [
    "429",
    "too_many_requests",
    "api request limit",
    "요청 한도",
    "일정 유효성 검증 중 오류",
  ].some((keyword) => reason.toLowerCase().includes(keyword));
}

function buildOverlapDetail(summary: ReasonSummary): string | null {
  if (!summary.hasOverlap) {
    return null;
  }
  if (!summary.overlapTitle) {
    return "기존 일정과 시간이 겹칩니다.";
  }
  return `기존 일정(${shortenText(summary.overlapTitle)})과 시간이 겹칩니다.`;
}

function buildTravelDetail(summary: ReasonSummary): string | null {
  if (!summary.hasTravelProblem) {
    return null;
  }

  const previousText = summary.previousTitle ? "직전 일정 후 " : "";
  const routeText = summary.routeFrom && summary.routeTo ? `${summary.routeFrom}에서 ${summary.routeTo}까지 ` : "";
  const gapText = summary.gapMinutes ? `${summary.gapMinutes}분 안에 ` : "";

  return `${previousText}${routeText}${gapText}이동할 수 없습니다.`;
}

function buildInvalidRangeDetail(summary: ReasonSummary): string | null {
  if (!summary.hasInvalidRange) {
    return null;
  }
  return "시작 시간이 종료 시간보다 늦거나 같습니다.";
}

function extractFirstMatch(reason: string, pattern: RegExp): string {
  return reason.match(pattern)?.[1]?.trim() ?? "";
}

function shortenText(text: string): string {
  const normalized = text.trim();
  if (normalized.length <= 24) {
    return normalized;
  }
  return `${normalized.slice(0, 23)}...`;
}

function cleanRoutePlace(place: string): string {
  const normalized = place.trim().replace(/^.*(?:으로|로)\s*/, "");
  return normalized.split(/\s+/).at(-1) ?? normalized;
}

function toConnectiveClause(sentence: string): string {
  return sentence.replace(/시간이 겹칩니다\.$/, "시간이 겹치").replace(/\.$/, "");
}

function dedupe(items: string[]): string[] {
  return [...new Set(items)];
}
