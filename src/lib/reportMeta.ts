type DailyMeta = {
  date: string;
  publishedAt?: string;
  itemCount: number;
  collectedCount?: number;
  citedCount?: number;
};

type WeeklyMeta = {
  weekStart: string;
  weekEnd: string;
  dailyCount: number;
  itemCount: number;
  collectedCount?: number;
  citedCount?: number;
};

export function formatKstDateTime(value?: string, fallbackDate?: string): string | null {
  const source = value ?? (fallbackDate ? `${fallbackDate}T06:00:00+09:00` : undefined);
  if (!source) return null;

  const date = new Date(source);
  if (Number.isNaN(date.getTime())) return source;

  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${values.year}-${values.month}-${values.day} ${values.hour}:${values.minute} KST`;
}

export function dailyCitedCount(data: DailyMeta): number {
  return data.citedCount ?? data.itemCount;
}

export function dailyCollectedCount(data: DailyMeta): number | undefined {
  return data.collectedCount;
}

export function weeklyCollectedCount(data: WeeklyMeta): number {
  return data.collectedCount ?? data.itemCount;
}

export function weeklyCitedCount(data: WeeklyMeta): number | undefined {
  return data.citedCount;
}
