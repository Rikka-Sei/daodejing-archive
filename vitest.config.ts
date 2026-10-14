import { getViteConfig } from 'astro/config';

export default getViteConfig({
  test: {
    include: ['tests/site/**/*.test.ts'],
    environment: 'node',
  },
});
