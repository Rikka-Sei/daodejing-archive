import { quotePath } from './html';

/** 线条图标，24×24 网格，描边由样式统一设置。 */
export const ICONS = {
  panel: '<rect x="3.5" y="5" width="17" height="14" rx="3"/><path d="M9.5 5v14"/>',
  search: '<circle cx="10.8" cy="10.8" r="6.3"/><path d="m20 20-4.7-4.7"/>',
  book: '<path d="M12 6.8C10.3 5.4 7.8 4.9 3.8 5.1v12.6c4-.2 6.5.3 8.2 1.7 1.7-1.4 4.2-1.9 8.2-1.7V5.1c-4-.2-6.5.3-8.2 1.7Z"/><path d="M12 6.8v12.6"/>',
  list: '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.2 6.5h.1M4.2 12h.1M4.2 17.5h.1" stroke-width="2.4"/>',
  table: '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M3.5 10h17M10 10v9"/>',
  chev: '<path d="m9.5 6 6 6-6 6"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  books:
    '<rect x="4" y="4" width="4.5" height="16" rx="1"/><rect x="10.5" y="4" width="4.5" height="16" rx="1"/><path d="m17.2 5.3 3.6.9-3.2 13.3-3.6-.9"/>',
  folder:
    '<path d="M3.5 7.5a2 2 0 0 1 2-2h3.3l2.2 2.3h7.5a2 2 0 0 1 2 2v7.7a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7.5Z"/>',
  'folder-open':
    '<path d="M4.5 17.5v-10a2 2 0 0 1 2-2h2.3l2.2 2.3h6a2 2 0 0 1 2 2V10"/><path d="m3.7 18.1 2-6.3a1.5 1.5 0 0 1 1.4-1h13.2a1.1 1.1 0 0 1 1.05 1.45l-1.8 5.6a2 2 0 0 1-1.9 1.4H5.4a1.6 1.6 0 0 1-1.7-1.15Z"/>',
  file: '<path d="M7 3.5h6.3l5.2 5.2V19a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5Z"/><path d="M13.2 3.7v5h5"/>',
  more: '<path d="M5.5 12h.1M12 12h.1M18.5 12h.1" stroke-width="2.6"/>',
  download: '<path d="M12 4.5v10.2m0 0 4-4m-4 4-4-4"/><path d="M5 19.5h14"/>',
  focus: '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/>',
  back: '<path d="m14.5 6-6 6 6 6"/>',
} as const;

export type IconName = keyof typeof ICONS;

/** 标签页图标：内嵌 SVG，省得浏览器去请求 favicon.ico。 */
export const FAVICON =
  'data:image/svg+xml,' +
  quotePath(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#cc7c5e"/>' +
      `<g fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS.book}</g></svg>`,
  );
