import { describe, it, expect } from 'vitest';
import { interpolateColor, readableTextColor } from './DotplotView';

// Two-stop Blues-like palette: near-white low end → dark high end.
const BLUES: number[][] = [[247, 251, 255], [8, 48, 107]];

describe('interpolateColor', () => {
  it('returns the palette endpoints at 0 and 1', () => {
    expect(interpolateColor(0, BLUES)).toEqual([247, 251, 255]);
    expect(interpolateColor(1, BLUES)).toEqual([8, 48, 107]);
  });

  it('clamps out-of-range values to the endpoints', () => {
    expect(interpolateColor(-5, BLUES)).toEqual([247, 251, 255]);
    expect(interpolateColor(5, BLUES)).toEqual([8, 48, 107]);
  });

  it('linearly interpolates the midpoint', () => {
    expect(interpolateColor(0.5, BLUES)).toEqual([
      Math.round((247 + 8) / 2),
      Math.round((251 + 48) / 2),
      Math.round((255 + 107) / 2),
    ]);
  });
});

describe('readableTextColor (W1)', () => {
  const luminance = (rgb: string): number => {
    const [r, g, b] = rgb.match(/\d+/g)!.map(Number);
    return 0.299 * r + 0.587 * g + 0.114 * b;
  };

  it('darkens near-white colors below the readability cap', () => {
    // Blues low-end is near-white and would be invisible as panel text.
    expect(luminance(readableTextColor([247, 251, 255]))).toBeLessThanOrEqual(141);
  });

  it('leaves already-dark colors unchanged', () => {
    expect(readableTextColor([8, 48, 107])).toBe('rgb(8,48,107)');
  });

  it('preserves hue direction while darkening (stays bluish)', () => {
    const [r, g, b] = readableTextColor([247, 251, 255]).match(/\d+/g)!.map(Number);
    // The original is roughly neutral-light; after scaling, blue should remain the
    // largest channel (the scale is uniform, so ordering is preserved).
    expect(b).toBeGreaterThanOrEqual(r);
  });
});
