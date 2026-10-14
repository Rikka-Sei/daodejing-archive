/** 用 Astro 的 Container API 渲染组件，返回去掉开发期调试属性的 HTML。 */
import { experimental_AstroContainer as AstroContainer } from 'astro/container';

type Component = Parameters<AstroContainer['renderToString']>[0];
type Options = NonNullable<Parameters<AstroContainer['renderToString']>[1]>;

let container: Promise<AstroContainer> | undefined;

export async function render(component: unknown, options: Options = {}): Promise<string> {
  container ??= AstroContainer.create();
  const html = await (await container).renderToString(component as Component, options);
  // 开发模式会给每个元素加 data-astro-source-file / -loc，测试不关心
  return html.replace(/ data-astro-source-(?:file|loc)="[^"]*"/g, '');
}

/** 子串出现的次数 */
export function count(html: string, part: string): number {
  return html.split(part).length - 1;
}
