/**
 * E2E Test Logger
 *
 * Provides structured logging for Playwright E2E tests with timestamps and levels.
 */

enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

interface LogConfig {
  level: LogLevel;
  timestamps: boolean;
  colors: boolean;
}

const DEFAULT_CONFIG: LogConfig = {
  level: LogLevel.INFO,
  timestamps: true,
  colors: true,
};

let config = { ...DEFAULT_CONFIG };

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function getTimestamp(): string {
  const now = new Date();
  return now.toISOString();
}

function colorize(text: string, color: keyof typeof COLORS): string {
  if (!config.colors) return text;
  return `${COLORS[color]}${text}${COLORS.reset}`;
}

function log(level: LogLevel, levelName: string, color: keyof typeof COLORS, ...args: unknown[]): void {
  if (level < config.level) return;

  const parts: string[] = [];

  if (config.timestamps) {
    parts.push(colorize(`[${getTimestamp()}]`, 'dim'));
  }

  parts.push(colorize(`[${levelName}]`, color));

  // Convert args to strings
  const messages = args.map(arg => {
    if (typeof arg === 'string') return arg;
    try {
      return JSON.stringify(arg, null, 2);
    } catch {
      return String(arg);
    }
  });

  console.log(parts.join(' '), ...messages);
}

export const logger = {
  /**
   * Set logger configuration
   */
  configure(options: Partial<LogConfig>): void {
    config = { ...config, ...options };
  },

  /**
   * Reset logger to default configuration
   */
  reset(): void {
    config = { ...DEFAULT_CONFIG };
  },

  /**
   * Log debug message
   */
  debug(...args: unknown[]): void {
    log(LogLevel.DEBUG, 'DEBUG', 'cyan', ...args);
  },

  /**
   * Log info message
   */
  info(...args: unknown[]): void {
    log(LogLevel.INFO, 'INFO', 'green', ...args);
  },

  /**
   * Log warning message
   */
  warn(...args: unknown[]): void {
    log(LogLevel.WARN, 'WARN', 'yellow', ...args);
  },

  /**
   * Log error message
   */
  error(...args: unknown[]): void {
    log(LogLevel.ERROR, 'ERROR', 'red', ...args);
  },

  /**
   * Log test section start
   */
  section(title: string): void {
    console.log('');
    console.log(colorize('='.repeat(60), 'dim'));
    console.log(colorize(`  ${title}`, 'bright'));
    console.log(colorize('='.repeat(60), 'dim'));
  },

  /**
   * Log test step
   */
  step(step: number, description: string): void {
    console.log(colorize(`  Step ${step}:`, 'blue'), description);
  },

  /**
   * Log success message
   */
  success(message: string): void {
    console.log(colorize('✓', 'green'), message);
  },

  /**
   * Log failure message
   */
  failure(message: string): void {
    console.log(colorize('✗', 'red'), message);
  },
};

export default logger;
