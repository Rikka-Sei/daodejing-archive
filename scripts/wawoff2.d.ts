/** wawoff2 不带类型，这里只声明用到的部分。 */
declare module 'wawoff2' {
  const wawoff2: {
    /** TrueType 字体 → WOFF2 */
    compress(font: Uint8Array): Promise<Uint8Array>;
  };
  export default wawoff2;
}
