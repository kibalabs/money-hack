

// eslint-disable-next-line import/no-extraneous-dependencies
import { MetaTag, Tag } from '@kibalabs/build/scripts/plugins/injectSeoPlugin.js';

const title = 'BorrowBot';
const description = 'AI Agents for Managing over-collateralizaed borrowing';
const url = 'https://borrowbot.kibalabs.com';
const imageUrl = `${url}/assets/banner.png`;

const seoTags = [
  new MetaTag('description', description),
  new Tag('meta', { property: 'og:title', content: title }),
  new Tag('meta', { property: 'og:description', content: description }),
  new Tag('meta', { property: 'og:url', content: url }),
  new Tag('meta', { property: 'og:image', content: imageUrl }),
  new MetaTag('twitter:card', 'summary_large_image'),
  new MetaTag('twitter:site', '@tokenpagexyz'),
  new Tag('link', { rel: 'canonical', href: url }),
  new Tag('link', { rel: 'icon', type: 'image/png', href: '/assets/icon-dark.png' }),
];

export default (config) => {
  const newConfig = config;
  newConfig.seoTags = seoTags;
  newConfig.title = title;
  newConfig.analyzeBundle = false;
  newConfig.viteConfigModifier = (viteConfig) => {
    const newViteConfig = viteConfig;
    newViteConfig.server.host = '0.0.0.0';
    newViteConfig.server.allowedHosts = true;
    newViteConfig.resolve = newViteConfig.resolve || {};
    newViteConfig.resolve.dedupe = ['react', 'react-dom'];
    return newViteConfig;
  };
  return newConfig;
};
