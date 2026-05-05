import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context: any) {
  const curation = await getCollection('curation');
  const weekly = await getCollection('weekly');

  const site = new URL(import.meta.env.BASE_URL, context.site);

  const dailyItems = curation
    .sort((a, b) => new Date(b.data.date).getTime() - new Date(a.data.date).getTime())
    .map((report) => ({
      title: report.data.title,
      pubDate: new Date(report.data.date + 'T06:00:00+09:00'),
      description: report.data.summary,
      link: `${site}curation/${report.id}/`,
    }));

  const weeklyItems = weekly
    .sort((a, b) => new Date(b.data.date).getTime() - new Date(a.data.date).getTime())
    .map((report) => ({
      title: report.data.title,
      pubDate: new Date(report.data.date + 'T09:00:00+09:00'),
      description: report.data.summary,
      link: `${site}weekly/${report.id}/`,
    }));

  const allItems = [...weeklyItems, ...dailyItems].sort(
    (a, b) => b.pubDate.getTime() - a.pubDate.getTime()
  );

  return rss({
    title: 'AI Curator — jwsung91',
    description: 'AI가 수집하고 요약한 로보틱스 & AI 테크 리포트 (데일리 + 위클리)',
    site: site,
    items: allItems,
    customData: `<language>ko-kr</language>`,
  });
}
