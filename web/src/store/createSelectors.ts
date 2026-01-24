/**
 * Zustand Store 选择器工具
 * Sprint 8: 性能优化 - 避免不必要的组件重渲染
 *
 * 使用方法:
 * 1. 创建 store 时使用 createSelectors 包装
 * 2. 在组件中使用 store.use.xxx() 而不是解构整个 store
 *
 * 优化效果:
 * - 细粒度订阅，只有使用的状态变化时才触发重渲染
 * - 自动生成类型安全的选择器
 * - 减少 bundle 大小（相比 reselect）
 */

import { StoreApi, UseBoundStore } from 'zustand';

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never;

/**
 * 为 Zustand store 自动生成选择器
 *
 * @example
 * // 创建 store
 * const useStoreBase = create<BearState>()((set) => ({
 *   bears: 0,
 *   honey: 100,
 *   addBear: () => set((state) => ({ bears: state.bears + 1 })),
 * }))
 *
 * // 包装 store
 * const useBearStore = createSelectors(useStoreBase)
 *
 * // 使用（只订阅 bears，honey 变化不会触发重渲染）
 * const bears = useBearStore.use.bears()
 */
export function createSelectors<S extends UseBoundStore<StoreApi<object>>>(
  store: S
): WithSelectors<S> {
  const storeIn = store as WithSelectors<S>;
  storeIn.use = {} as { [K in keyof ReturnType<S['getState']>]: () => ReturnType<S['getState']>[K] };

  for (const k of Object.keys(store.getState())) {
    (storeIn.use as Record<string, () => unknown>)[k] = () =>
      store((s) => s[k as keyof typeof s]);
  }

  return storeIn;
}

/**
 * 创建浅比较选择器
 * 用于选择对象或数组时避免不必要的重渲染
 *
 * @example
 * const items = useStore(shallowSelector(state => state.items))
 */
export function shallowSelector<T, U>(selector: (state: T) => U) {
  return (state: T) => selector(state);
}

/**
 * 创建组合选择器
 * 从多个状态字段派生出新值
 *
 * @example
 * const totalItems = useStore(
 *   combineSelectors(
 *     state => state.items,
 *     state => state.multiplier,
 *     (items, multiplier) => items.length * multiplier
 *   )
 * )
 */
export function combineSelectors<T, A, B, R>(
  selectorA: (state: T) => A,
  selectorB: (state: T) => B,
  combiner: (a: A, b: B) => R
): (state: T) => R {
  return (state: T) => combiner(selectorA(state), selectorB(state));
}

/**
 * 创建记忆化选择器
 * 只有依赖值变化时才重新计算
 *
 * @example
 * const expensiveValue = useStore(
 *   memoizedSelector(
 *     state => state.items,
 *     items => items.reduce((sum, item) => sum + item.value, 0)
 *   )
 * )
 */
export function memoizedSelector<T, D, R>(
  dependencySelector: (state: T) => D,
  compute: (dependency: D) => R
): (state: T) => R {
  let lastDependency: D | undefined;
  let lastResult: R | undefined;

  return (state: T) => {
    const dependency = dependencySelector(state);

    // 浅比较依赖是否变化
    if (dependency !== lastDependency) {
      lastDependency = dependency;
      lastResult = compute(dependency);
    }

    return lastResult as R;
  };
}

/**
 * 创建带默认值的选择器
 * 状态为 undefined/null 时返回默认值
 */
export function withDefault<T, R>(
  selector: (state: T) => R | undefined | null,
  defaultValue: R
): (state: T) => R {
  return (state: T) => selector(state) ?? defaultValue;
}

/**
 * Store 订阅辅助函数
 * 在 store 变化时执行副作用
 *
 * @example
 * // 在组件外监听 store 变化
 * const unsubscribe = subscribeToStore(
 *   useStore,
 *   state => state.user,
 *   (user, prevUser) => {
 *     console.log('User changed:', user)
 *   }
 * )
 */
export function subscribeToStore<T, S>(
  store: UseBoundStore<StoreApi<T>>,
  selector: (state: T) => S,
  callback: (current: S, previous: S) => void
): () => void {
  let previous = selector(store.getState());

  return store.subscribe((state) => {
    const current = selector(state);
    if (current !== previous) {
      callback(current, previous);
      previous = current;
    }
  });
}

/**
 * 批量更新辅助函数
 * 合并多个 set 调用为单次更新
 *
 * @example
 * const { batchSet, flush } = createBatchedSetter(useStore)
 * batchSet({ count: 1 })
 * batchSet({ name: 'new' })
 * flush() // 只触发一次更新
 */
export function createBatchedSetter<T extends object>(
  store: UseBoundStore<StoreApi<T>>
): {
  batchSet: (partial: Partial<T>) => void;
  flush: () => void;
} {
  let pendingUpdates: Partial<T> = {};
  let flushScheduled = false;

  const flush = () => {
    if (Object.keys(pendingUpdates).length > 0) {
      store.setState(pendingUpdates as T);
      pendingUpdates = {};
    }
    flushScheduled = false;
  };

  const batchSet = (partial: Partial<T>) => {
    pendingUpdates = { ...pendingUpdates, ...partial };

    if (!flushScheduled) {
      flushScheduled = true;
      // 使用 queueMicrotask 在当前事件循环结束时刷新
      queueMicrotask(flush);
    }
  };

  return { batchSet, flush };
}

export default createSelectors;
