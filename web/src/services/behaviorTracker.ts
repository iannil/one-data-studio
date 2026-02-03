/**
 * 用户行为追踪SDK
 * 自动采集用户行为数据并上报到后端
 */

import { v4 as uuidv4 } from 'uuid';

// 配置
interface BehaviorTrackerConfig {
  apiBaseUrl: string;
  tenantId: string;
  userId: string;
  sessionTimeout?: number; // 会话超时时间（分钟），默认30分钟
  autoTrack?: boolean; // 是否自动追踪，默认true
  sampleRate?: number; // 采样率 0-1，默认1（全部采集）
}

// 行为事件类型
type BehaviorType =
  | 'page_view'
  | 'click'
  | 'submit'
  | 'form_submit'
  | 'login'
  | 'logout'
  | 'download'
  | 'export'
  | 'data_query'
  | 'api_call';

// 行为事件
interface BehaviorEvent {
  user_id: string;
  tenant_id: string;
  session_id: string;
  behavior_type: BehaviorType;
  action?: string;
  target_type?: string;
  target_id?: string;
  page_url: string;
  page_title?: string;
  referrer?: string;
  module?: string;
  duration?: number;
  metadata?: Record<string, any>;
}

class BehaviorTracker {
  private config: BehaviorTrackerConfig;
  private sessionId: string;
  private sessionStartTime: number;
  private currentPage: string;
  private pageViewStartTime: number;
  private queue: BehaviorEvent[] = [];
  private isInitialized: boolean = false;
  private flushTimer: NodeJS.Timeout | null = null;
  private sessionTimer: NodeJS.Timeout | null = null;
  private visibilityTimer: NodeJS.Timeout | null = null;

  constructor(config: BehaviorTrackerConfig) {
    this.config = {
      ...config,
      sessionTimeout: config.sessionTimeout || 30,
      autoTrack: config.autoTrack !== false,
      sampleRate: config.sampleRate ?? 1,
    };

    this.sessionId = this.getOrCreateSessionId();
    this.sessionStartTime = Date.now();
    this.currentPage = window.location.pathname;
    this.pageViewStartTime = Date.now();

    if (typeof window !== 'undefined') {
      this.init();
    }
  }

  private init(): void {
    if (this.isInitialized) return;

    // 自动追踪页面浏览
    if (this.config.autoTrack) {
      this.trackPageView();
      this.setupAutoTracking();
    }

    // 启动定时发送队列
    this.startFlushTimer();

    // 启动会话超时检查
    this.startSessionTimer();

    // 页面卸载时发送数据
    window.addEventListener('beforeunload', () => {
      this.flush();
    });

    // 页面可见性变化
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.trackPageDuration();
      } else if (document.visibilityState === 'visible') {
        this.pageViewStartTime = Date.now();
      }
    });

    this.isInitialized = true;
  }

  private setupAutoTracking(): void {
    // 自动追踪点击事件
    document.addEventListener('click', (event) => {
      const target = event.target as HTMLElement;
      this.trackClick(target);
    }, true);

    // 自动追踪表单提交
    document.addEventListener('submit', (event) => {
      const form = event.target as HTMLFormElement;
      this.trackFormSubmit(form);
    }, true);
  }

  private startFlushTimer(): void {
    // 每5秒发送一次队列中的数据
    this.flushTimer = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, 5000);
  }

  private startSessionTimer(): void {
    // 检查会话超时
    this.sessionTimer = setInterval(() => {
      const elapsed = (Date.now() - this.sessionStartTime) / 1000 / 60; // 分钟
      if (elapsed > (this.config.sessionTimeout || 30)) {
        this.endSession();
        this.startNewSession();
      }
    }, 60000); // 每分钟检查一次
  }

  private getOrCreateSessionId(): string {
    let sessionId = sessionStorage.getItem('behavior_session_id');
    if (!sessionId) {
      sessionId = uuidv4();
      sessionStorage.setItem('behavior_session_id', sessionId);
    }
    return sessionId;
  }

  private startNewSession(): void {
    this.sessionId = uuidv4();
    this.sessionStartTime = Date.now();
    sessionStorage.setItem('behavior_session_id', this.sessionId);

    // 发送会话开始事件
    this.track('login', {
      action: 'session_start',
    });
  }

  private endSession(): void {
    this.trackPageDuration();
    this.flush();
  }

  private getUserAgent(): string {
    return navigator.userAgent;
  }

  private extractModule(url: string): string {
    const parts = url.split('/').filter(Boolean);
    return parts[0] || 'unknown';
  }

  private extractElementInfo(element: HTMLElement): {
    type: string;
    id?: string;
    text?: string;
    name?: string;
  } {
    const info: { type: string; id?: string; text?: string; name?: string } = {
      type: element.tagName.toLowerCase(),
    };

    if (element.id) {
      info.id = element.id;
    }
    if (element.getAttribute('name')) {
      info.name = element.getAttribute('name') || undefined;
    }
    if (element.textContent && element.textContent.trim().length < 50) {
      info.text = element.textContent.trim();
    }

    return info;
  }

  // 公共方法

  /**
   * 追踪页面浏览
   */
  trackPageView(): void {
    const url = window.location.pathname + window.location.search;
    const title = document.title;

    // 如果页面变化，发送前一个页面的停留时长
    if (this.currentPage !== url) {
      this.trackPageDuration();
      this.currentPage = url;
    }

    this.track('page_view', {
      page_url: url,
      page_title: title,
      referrer: document.referrer,
      module: this.extractModule(url),
    });

    this.pageViewStartTime = Date.now();
  }

  /**
   * 追踪页面停留时长
   */
  private trackPageDuration(): void {
    const duration = (Date.now() - this.pageViewStartTime) / 1000;
    if (duration > 1) {
      this.queue.push({
        user_id: this.config.userId,
        tenant_id: this.config.tenantId,
        session_id: this.sessionId,
        behavior_type: 'page_view',
        page_url: this.currentPage,
        duration: duration,
      });
    }
  }

  /**
   * 追踪点击事件
   */
  trackClick(element: HTMLElement): void {
    const info = this.extractElementInfo(element);

    // 忽略无意义的点击
    if (info.type === 'body' || info.type === 'html') {
      return;
    }

    this.track('click', {
      action: info.text || info.name || info.type,
      target_type: info.type,
      target_id: info.id,
      metadata: info,
    });
  }

  /**
   * 追踪表单提交
   */
  trackFormSubmit(form: HTMLFormElement): void {
    const formId = form.id || form.name || 'unknown';

    this.track('form_submit', {
      action: 'form_submit',
      target_type: 'form',
      target_id: formId,
    });
  }

  /**
   * 通用追踪方法
   */
  track(
    behaviorType: BehaviorType,
    data: Partial<BehaviorEvent> = {}
  ): void {
    // 采样率检查
    if (Math.random() > (this.config.sampleRate || 1)) {
      return;
    }

    const event: BehaviorEvent = {
      user_id: this.config.userId,
      tenant_id: this.config.tenantId,
      session_id: this.sessionId,
      behavior_type: behaviorType,
      page_url: this.currentPage,
      page_title: document.title,
      referrer: document.referrer,
      module: this.extractModule(this.currentPage),
      metadata: {
        user_agent: this.getUserAgent(),
        screen_width: window.screen.width,
        screen_height: window.screen.height,
        viewport_width: window.innerWidth,
        viewport_height: window.innerHeight,
        ...data.metadata,
      },
      ...data,
    };

    this.queue.push(event);
  }

  /**
   * 发送队列中的数据
   */
  private async flush(): Promise<void> {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    try {
      const response = await fetch(`${this.config.apiBaseUrl}/api/v1/behaviors/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          events: events,
          tenant_id: this.config.tenantId,
        }),
        keepalive: true, // 确保页面卸载时也能发送
      });

      if (!response.ok) {
        // 失败时重新加入队列
        this.queue.unshift(...events);
      }
    } catch (error) {
      console.error('Failed to send behavior events:', error);
      // 失败时重新加入队列
      this.queue.unshift(...events);
    }
  }

  /**
   * 设置用户ID
   */
  setUserId(userId: string): void {
    this.config.userId = userId;
  }

  /**
   * 设置租户ID
   */
  setTenantId(tenantId: string): void {
    this.config.tenantId = tenantId;
  }

  /**
   * 手动追踪自定义事件
   */
  trackCustomEvent(
    eventType: string,
    properties: Record<string, any> = {}
  ): void {
    this.track('api_call' as BehaviorType, {
      action: eventType,
      metadata: properties,
    });
  }

  /**
   * 追踪登录
   */
  trackLogin(method: string = 'password'): void {
    this.track('login', {
      action: 'login',
      metadata: { login_method: method },
    });
  }

  /**
   * 追踪登出
   */
  trackLogout(): void {
    this.track('logout', {
      action: 'logout',
    });
    this.endSession();
  }

  /**
   * 追踪下载
   */
  trackDownload(fileName: string, fileType: string): void {
    this.track('download', {
      action: 'download',
      metadata: { file_name: fileName, file_type: fileType },
    });
  }

  /**
   * 追踪导出
   */
  trackExport(exportType: string, recordCount: number): void {
    this.track('export', {
      action: 'export',
      metadata: { export_type: exportType, record_count: recordCount },
    });
  }

  /**
   * 追踪数据查询
   */
  trackDataQuery(queryType: string, tableName?: string): void {
    this.track('data_query', {
      action: 'data_query',
      metadata: { query_type: queryType, table_name: tableName },
    });
  }

  /**
   * 销毁追踪器
   */
  destroy(): void {
    this.endSession();

    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    if (this.sessionTimer) {
      clearInterval(this.sessionTimer);
    }
    if (this.visibilityTimer) {
      clearTimeout(this.visibilityTimer);
    }

    this.isInitialized = false;
  }
}

// 单例模式
let trackerInstance: BehaviorTracker | null = null;

/**
 * 初始化行为追踪器
 */
export function initBehaviorTracker(config: BehaviorTrackerConfig): BehaviorTracker {
  if (!trackerInstance) {
    trackerInstance = new BehaviorTracker(config);
  }
  return trackerInstance;
}

/**
 * 获取行为追踪器实例
 */
export function getBehaviorTracker(): BehaviorTracker | null {
  return trackerInstance;
}

export default BehaviorTracker;
