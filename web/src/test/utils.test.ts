/**
 * 工具函数测试示例
 * Sprint 6: 单元测试框架
 */

import { describe, it, expect } from 'vitest';

describe('Utility Functions', () => {
  describe('String Utilities', () => {
    it('should truncate long strings', () => {
      const truncate = (str: string, len: number): string => {
        if (str.length <= len) return str;
        return str.slice(0, len) + '...';
      };

      expect(truncate('Hello World', 5)).toBe('Hello...');
      expect(truncate('Hi', 10)).toBe('Hi');
    });

    it('should format dates correctly', () => {
      const formatDate = (date: Date): string => {
        return date.toISOString().split('T')[0];
      };

      const testDate = new Date('2024-01-15T10:30:00Z');
      expect(formatDate(testDate)).toBe('2024-01-15');
    });
  });

  describe('Number Utilities', () => {
    it('should format numbers with commas', () => {
      const formatNumber = (num: number): string => {
        return num.toLocaleString('en-US');
      };

      expect(formatNumber(1000000)).toBe('1,000,000');
      expect(formatNumber(123.456)).toBe('123.456');
    });

    it('should calculate percentage', () => {
      const percentage = (value: number, total: number): number => {
        if (total === 0) return 0;
        return Math.round((value / total) * 100 * 10) / 10;
      };

      expect(percentage(50, 100)).toBe(50);
      expect(percentage(1, 3)).toBe(33.3);
      expect(percentage(10, 0)).toBe(0);
    });
  });

  describe('Array Utilities', () => {
    it('should chunk arrays correctly', () => {
      const chunk = <T,>(arr: T[], size: number): T[][] => {
        const result: T[][] = [];
        for (let i = 0; i < arr.length; i += size) {
          result.push(arr.slice(i, i + size));
        }
        return result;
      };

      expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
      expect(chunk([], 3)).toEqual([]);
    });

    it('should unique arrays', () => {
      const unique = <T,>(arr: T[]): T[] => {
        return Array.from(new Set(arr));
      };

      expect(unique([1, 2, 2, 3, 1])).toEqual([1, 2, 3]);
      expect(unique(['a', 'b', 'a'])).toEqual(['a', 'b']);
    });
  });

  describe('Object Utilities', () => {
    it('should deep clone objects', () => {
      const deepClone = <T,>(obj: T): T => {
        return JSON.parse(JSON.stringify(obj));
      };

      const original = { a: 1, b: { c: 2 } };
      const cloned = deepClone(original);

      expect(cloned).toEqual(original);
      expect(cloned).not.toBe(original);

      // 修改克隆对象不应影响原始对象
      (cloned as { b: { c: number } }).b.c = 999;
      expect(original.b.c).toBe(2);
    });

    it('should pick object properties', () => {
      const pick = <T extends object, K extends keyof T>(
        obj: T,
        keys: K[]
      ): Pick<T, K> => {
        const result = {} as Pick<T, K>;
        keys.forEach((key) => {
          if (key in obj) {
            result[key] = obj[key];
          }
        });
        return result;
      };

      const obj = { a: 1, b: 2, c: 3 };
      expect(pick(obj, ['a', 'c'])).toEqual({ a: 1, c: 3 });
    });
  });
});
