import type { MetadataRoute } from 'next';

const BASE_URL = 'https://avtoraskroy.ru';

/** Sitemap для Яндекса и Google: публичные страницы + статьи. */
export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages = ['', '/pricing', '/oferta', '/privacy', '/blog'];
  const articles = ['/blog/prisadka-petel', '/blog/karta-raskroya-ldsp'];

  return [...staticPages, ...articles].map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date('2026-07-26'),
    changeFrequency: path === '' ? 'weekly' : 'monthly',
    priority: path === '' ? 1.0 : path.startsWith('/blog') ? 0.7 : 0.5,
  }));
}
