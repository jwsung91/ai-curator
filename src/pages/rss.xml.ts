import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context: any) {
  const curation = await getCollection('curation');
  const sortedCuration = curation.sort((a, b) => new Date(b.data.date).getTime() - new Date(a.data.date).getTime());
  const base = context.site.pathname.replace(/\/$/, '');

  return rss({
    title: 'AI Curator — jwsung91',
    description: 'AI가 수집하고 요약한 데일리 로보틱스 & AI 테크 리포트',
    site: context.site,
    items: sortedCuration.map((report) => ({
      title: `${report.data.date} Daily Report`,
      pubDate: new Date(report.data.date),
      description: report.data.summary,
      link: `${base}/curation/${report.id}/`,
    })),
    customData: `<language>ko-kr</language>`,
  });
}
