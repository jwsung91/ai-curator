export const topics = [
  { id: 'ros', label: 'ROS 2·미들웨어', pattern: /\bros\s?2?\b|rclcpp|rclpy|\bdds\b|\brmw\b|rosbag|open.rmf/i },
  { id: 'navigation', label: '내비게이션·조작', pattern: /nav2|navigation2|moveit|내비게이션|모션 플래닝|manipulation/i },
  { id: 'simulation', label: '시뮬레이션·엣지', pattern: /gazebo|isaac|jetson|webots|시뮬레이션/i },
  { id: 'ai-tools', label: 'AI 개발 도구', pattern: /ollama|litellm|\bmcp\b|copilot|cursor|claude|gemini|\bllm\b|에이전트/i },
  { id: 'industry', label: '산업·정책', pattern: /투자|인수|합병|규제|정책|파트너십|산업 동향/i },
];

export function plainText(body: string): string {
  return body.replace(/<[^>]*>/g, ' ').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[#*_`|]/g, ' ').replace(/\s+/g, ' ').trim();
}

export function topicIds(body: string): string[] {
  const editorialBody = body.split(/###\s+🔗/)[0];
  return topics.filter(topic => topic.pattern.test(plainText(editorialBody))).map(topic => topic.id);
}

export type SearchEntry = { text: string; topics: string[]; kind: string; date: string };
export type SearchFilters = { query: string; topic: string; kind: string; month: string };

export function matchesEntry(entry: SearchEntry, filters: SearchFilters): boolean {
  const normalize = (value: string) => value.normalize('NFKC').toLocaleLowerCase();
  const words = normalize(filters.query).trim().split(/\s+/).filter(Boolean);
  return words.every(word => normalize(entry.text).includes(word))
    && (!filters.topic || entry.topics.includes(filters.topic))
    && (!filters.kind || entry.kind === filters.kind)
    && (!filters.month || entry.date.startsWith(filters.month));
}
