import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const curation = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './reports/daily' }),
  schema: z.object({
    date: z.string(),
    title: z.string(),
    summary: z.string(),
    itemCount: z.number(),
  }),
});

const weekly = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './reports/weekly', ignore: ['**/.gitkeep'] }),
  schema: z.object({
    date: z.string(),
    weekStart: z.string(),
    weekEnd: z.string(),
    weekNumber: z.number(),
    title: z.string(),
    summary: z.string(),
    dailyCount: z.number(),
    itemCount: z.number(),
  }),
});

export const collections = { curation, weekly };
