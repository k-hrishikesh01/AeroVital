import '@testing-library/jest-dom';

// Polyfill ResizeObserver for testing Recharts ResponsiveContainer
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserver;
