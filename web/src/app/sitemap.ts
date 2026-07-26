import type { MetadataRoute } from 'next';

const BASE_URL = 'https://avtoraskroy.ru';

/** Дата последнего изменения по каждому пути. */
const PAGES: Array<{ path: string; lastModified: string }> = [
  { path: '', lastModified: '2026-07-26' },
  { path: '/pricing', lastModified: '2026-07-20' },
  { path: '/oferta', lastModified: '2026-07-14' },
  { path: '/privacy', lastModified: '2026-07-14' },
  { path: '/blog', lastModified: '2026-07-26' },
  { path: '/blog/prisadka-petel', lastModified: '2026-07-12' },
  { path: '/blog/karta-raskroya-ldsp', lastModified: '2026-07-17' },
  { path: '/blog/kromka-pvh-tolshchina', lastModified: '2026-07-21' },
  { path: '/blog/specifikaciya-mebeli', lastModified: '2026-07-24' },
  { path: '/blog/dxf-dlya-chpu', lastModified: '2026-07-26' },
];

/** Sitemap для Яндекса и Google: публичные страницы + статьи. */
export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.map(({ path, lastModified }) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(lastModified),
    changeFrequency: path === '' ? 'weekly' : 'monthly',
    priority: path === '' ? 1.0 : path.startsWith('/blog') ? 0.7 : 0.5,
  }));
}
