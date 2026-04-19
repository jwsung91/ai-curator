import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const reports = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/reports' }),
  schema: z.object({
    date: z.string(),           // YYYY-MM-DD
    title: z.string(),
    summary: z.string(),        // 한 줄 요약
    itemCount: z.number(),
  }),
});

export const collections = { reports };
