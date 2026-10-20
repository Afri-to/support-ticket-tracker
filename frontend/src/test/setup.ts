import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver or matchMedia; Recharts and the colour hook use them.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
window.matchMedia =
  window.matchMedia ||
  ((query: string) =>
    ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList);

// Charts have no size in jsdom; Recharts warns about it on every render.
const warn = console.warn;
console.warn = (...args: unknown[]) => {
  if (String(args[0]).includes("of chart should be greater than 0")) return;
  warn(...args);
};
