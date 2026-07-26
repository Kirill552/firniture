import type { MetadataRoute } from 'next';

/** robots.txt: публичное открыто, кабинет и API закрыты. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/orders', '/bom', '/cam', '/settings', '/integrations', '/viewer', '/welcome'],
    },
    sitemap: 'https://avtoraskroy.ru/sitemap.xml',
  };
}
