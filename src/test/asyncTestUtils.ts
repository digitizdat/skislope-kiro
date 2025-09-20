/**
 * Async Operation Test Utilities
 * Provides utilities for handling Promise-based operations, timeout management,
 * and controlling timing and execution order in async tests
 * 
 * Requirements: 3.1, 3.2, 3.3
 */

import { vi } from 'vitest';

/**
 * Configuration for async test utilities
 */
export interface AsyncTestConfig {
  /** Default timeout for async operations in test environment (ms) */
  defaultTimeout: number;
  /** Timeout for CI environments (ms) */
  ciTimeout: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Base delay for exponential backoff (ms) */
  baseDelay: number;
  /** Whether to use fake timers by default */
  useFakeTimers: boolean;
}

/**
 * Default configuration optimized for test environment
 */
export const DEFAULT_ASYNC_CONFIG: AsyncTestConfig = {
  defaultTimeout: 5000,     // 5 seconds for local tests
  ciTimeout: 15000,         // 15 seconds for CI environment
  maxRetries: 3,
  baseDelay: 100,
  useFakeTimers: false,
};

/**
 * Get timeout value based on environment
 */
export function getTestTimeout(config: Partial<AsyncTestConfig> = {}): number {
  const mergedConfig = { ...DEFAULT_ASYNC_CONFIG, ...config };
  const isCI = process.env.CI === 'true' || process.env.NODE_ENV === 'ci';
  return isCI ? mergedConfig.ciTimeout : mergedConfig.defaultTimeout;
}

/**
 * Promise-based operation utilities
 */
export class AsyncTestUtils {
  private static config: AsyncTestConfig = DEFAULT_ASYNC_CONFIG;
  private static timersInstalled = false;

  /**
   * Configure async test utilities
   */
  static configure(config: Partial<AsyncTestConfig>): void {
    AsyncTestUtils.config = { ...DEFAULT_ASYNC_CONFIG, ...config };
  }

  /**
   * Wait for a condition to become true with timeout
   */
  static async waitFor(
    condition: () => boolean | Promise<boolean>,
    options: {
      timeout?: number;
      interval?: number;
      message?: string;
    } = {}
  ): Promise<void> {
    const timeout = options.timeout ?? getTestTimeout();
    const interval = options.interval ?? 50;
    const message = options.message ?? 'Condition was not met within timeout';

    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      try {
        const result = await condition();
        if (result) {
          return;
        }
      } catch (error) {
        // Continue waiting if condition throws
      }

      await AsyncTestUtils.delay(interval);
    }

    throw new Error(`${message} (timeout: ${timeout}ms)`);
  }

  /**
   * Wait for a Promise to resolve with timeout
   */
  static async waitForPromise<T>(
    promise: Promise<T>,
    timeout?: number,
    message?: string
  ): Promise<T> {
    const timeoutMs = timeout ?? getTestTimeout();
    const timeoutMessage = message ?? `Promise did not resolve within ${timeoutMs}ms`;

    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(timeoutMessage));
      }, timeoutMs);

      promise
        .then((result) => {
          clearTimeout(timer);
          resolve(result);
        })
        .catch((error) => {
          clearTimeout(timer);
          reject(error);
        });
    });
  }

  /**
   * Wait for multiple promises with individual timeouts
   */
  static async waitForAll<T>(
    promises: Array<{
      promise: Promise<T>;
      timeout?: number;
      name?: string;
    }>,
    options: {
      failFast?: boolean;
      globalTimeout?: number;
    } = {}
  ): Promise<T[]> {
    const { failFast = true, globalTimeout } = options;

    const wrappedPromises = promises.map(({ promise, timeout, name }, index) => {
      const promiseName = name ?? `Promise ${index}`;
      const promiseTimeout = timeout ?? getTestTimeout();
      
      return AsyncTestUtils.waitForPromise(promise, promiseTimeout, `${promiseName} timed out`);
    });

    if (globalTimeout) {
      const globalTimeoutPromise = AsyncTestUtils.delay(globalTimeout).then(() => {
        throw new Error(`Global timeout of ${globalTimeout}ms exceeded`);
      });

      if (failFast) {
        return Promise.race([
          Promise.all(wrappedPromises),
          globalTimeoutPromise
        ]) as Promise<T[]>;
      } else {
        return Promise.race([
          Promise.allSettled(wrappedPromises).then(results => {
            const values: T[] = [];
            const errors: Error[] = [];

            results.forEach((result, index) => {
              if (result.status === 'fulfilled') {
                values[index] = result.value;
              } else {
                errors.push(new Error(`${promises[index].name ?? `Promise ${index}`}: ${result.reason}`));
              }
            });

            if (errors.length > 0) {
              throw new AggregateError(errors, 'Some promises failed');
            }

            return values;
          }),
          globalTimeoutPromise
        ]) as Promise<T[]>;
      }
    }

    return failFast ? Promise.all(wrappedPromises) : Promise.allSettled(wrappedPromises).then(results => {
      const values: T[] = [];
      const errors: Error[] = [];

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          values[index] = result.value;
        } else {
          errors.push(new Error(`${promises[index].name ?? `Promise ${index}`}: ${result.reason}`));
        }
      });

      if (errors.length > 0) {
        throw new AggregateError(errors, 'Some promises failed');
      }

      return values;
    });
  }

  /**
   * Flush all pending promises in the microtask queue
   */
  static async flushPromises(): Promise<void> {
    return new Promise(resolve => {
      setTimeout(resolve, 0);
    });
  }

  /**
   * Flush promises multiple times to ensure all nested promises resolve
   */
  static async flushAllPromises(iterations = 3): Promise<void> {
    for (let i = 0; i < iterations; i++) {
      await AsyncTestUtils.flushPromises();
    }
  }

  /**
   * Create a delay with optional fake timer support
   */
  static async delay(ms: number): Promise<void> {
    if (AsyncTestUtils.timersInstalled) {
      // If fake timers are active, we need to advance them
      return new Promise(resolve => {
        setTimeout(resolve, ms);
      });
    } else {
      return new Promise(resolve => {
        setTimeout(resolve, ms);
      });
    }
  }

  /**
   * Retry an async operation with exponential backoff
   */
  static async retry<T>(
    operation: () => Promise<T>,
    options: {
      maxAttempts?: number;
      baseDelay?: number;
      maxDelay?: number;
      backoffFactor?: number;
      shouldRetry?: (error: Error, attempt: number) => boolean;
    } = {}
  ): Promise<T> {
    const {
      maxAttempts = AsyncTestUtils.config.maxRetries,
      baseDelay = AsyncTestUtils.config.baseDelay,
      maxDelay = 5000,
      backoffFactor = 2,
      shouldRetry = () => true
    } = options;

    let lastError: Error;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (attempt === maxAttempts || !shouldRetry(lastError, attempt)) {
          throw lastError;
        }

        const delay = Math.min(baseDelay * Math.pow(backoffFactor, attempt - 1), maxDelay);
        await AsyncTestUtils.delay(delay);
      }
    }

    throw lastError!;
  }

  /**
   * Create a timeout promise that rejects after specified time
   */
  static createTimeout(ms: number, message?: string): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(message ?? `Operation timed out after ${ms}ms`));
      }, ms);
    });
  }

  /**
   * Race a promise against a timeout
   */
  static async withTimeout<T>(
    promise: Promise<T>,
    timeout: number,
    message?: string
  ): Promise<T> {
    return Promise.race([
      promise,
      AsyncTestUtils.createTimeout(timeout, message)
    ]);
  }

  /**
   * Install fake timers for controlling time in tests
   */
  static installFakeTimers(): void {
    if (!AsyncTestUtils.timersInstalled) {
      vi.useFakeTimers();
      AsyncTestUtils.timersInstalled = true;
    }
  }

  /**
   * Restore real timers
   */
  static restoreTimers(): void {
    if (AsyncTestUtils.timersInstalled) {
      vi.useRealTimers();
      AsyncTestUtils.timersInstalled = false;
    }
  }

  /**
   * Advance fake timers by specified amount
   */
  static async advanceTimers(ms: number): Promise<void> {
    if (AsyncTestUtils.timersInstalled) {
      await vi.advanceTimersByTimeAsync(ms);
    } else {
      console.warn('Fake timers not installed. Call installFakeTimers() first.');
    }
  }

  /**
   * Advance timers to next timer
   */
  static async advanceToNextTimer(): Promise<void> {
    if (AsyncTestUtils.timersInstalled) {
      await vi.advanceTimersToNextTimerAsync();
    } else {
      console.warn('Fake timers not installed. Call installFakeTimers() first.');
    }
  }

  /**
   * Run all pending timers
   */
  static async runAllTimers(): Promise<void> {
    if (AsyncTestUtils.timersInstalled) {
      await vi.runAllTimersAsync();
    } else {
      console.warn('Fake timers not installed. Call installFakeTimers() first.');
    }
  }

  /**
   * Get the current timer count
   */
  static getTimerCount(): number {
    if (AsyncTestUtils.timersInstalled) {
      return vi.getTimerCount();
    }
    return 0;
  }

  /**
   * Clear all timers
   */
  static clearAllTimers(): void {
    if (AsyncTestUtils.timersInstalled) {
      vi.clearAllTimers();
    }
  }
}

/**
 * Timing control utilities for deterministic async testing
 */
export class TimingController {
  private executionQueue: Array<{
    id: string;
    operation: () => Promise<any>;
    dependencies: string[];
    completed: boolean;
    result?: any;
    error?: Error;
  }> = [];

  private completedOperations = new Set<string>();

  /**
   * Add an operation to the execution queue
   */
  addOperation<T>(
    id: string,
    operation: () => Promise<T>,
    dependencies: string[] = []
  ): void {
    this.executionQueue.push({
      id,
      operation,
      dependencies,
      completed: false
    });
  }

  /**
   * Execute operations in dependency order
   */
  async executeAll(): Promise<Map<string, any>> {
    const results = new Map<string, any>();
    const maxIterations = this.executionQueue.length * 2; // Prevent infinite loops
    let iterations = 0;

    while (this.executionQueue.some(op => !op.completed) && iterations < maxIterations) {
      iterations++;

      for (const operation of this.executionQueue) {
        if (operation.completed) continue;

        // Check if all dependencies are completed
        const dependenciesMet = operation.dependencies.every(dep => 
          this.completedOperations.has(dep)
        );

        if (dependenciesMet) {
          try {
            operation.result = await operation.operation();
            operation.completed = true;
            this.completedOperations.add(operation.id);
            results.set(operation.id, operation.result);
          } catch (error) {
            operation.error = error instanceof Error ? error : new Error(String(error));
            operation.completed = true;
            this.completedOperations.add(operation.id);
            throw new Error(`Operation ${operation.id} failed: ${operation.error.message}`);
          }
        }
      }

      // Small delay to prevent tight loop
      await AsyncTestUtils.delay(1);
    }

    if (iterations >= maxIterations) {
      const incompleteOps = this.executionQueue
        .filter(op => !op.completed)
        .map(op => `${op.id} (deps: ${op.dependencies.join(', ')})`);
      
      throw new Error(`Circular dependency or unresolvable dependencies detected: ${incompleteOps.join(', ')}`);
    }

    return results;
  }

  /**
   * Reset the timing controller
   */
  reset(): void {
    this.executionQueue = [];
    this.completedOperations.clear();
  }

  /**
   * Get execution status
   */
  getStatus(): {
    total: number;
    completed: number;
    pending: string[];
    failed: string[];
  } {
    const completed = this.executionQueue.filter(op => op.completed && !op.error);
    const failed = this.executionQueue.filter(op => op.error);
    const pending = this.executionQueue.filter(op => !op.completed);

    return {
      total: this.executionQueue.length,
      completed: completed.length,
      pending: pending.map(op => op.id),
      failed: failed.map(op => op.id)
    };
  }
}

/**
 * Async test utilities for common testing patterns
 */
export class AsyncTestPatterns {
  /**
   * Test that an async operation completes within expected time
   */
  static async expectToCompleteWithin<T>(
    operation: () => Promise<T>,
    maxTime: number,
    message?: string
  ): Promise<T> {
    const start = Date.now();
    const result = await AsyncTestUtils.withTimeout(
      operation(),
      maxTime,
      message ?? `Operation should complete within ${maxTime}ms`
    );
    const duration = Date.now() - start;

    if (duration > maxTime) {
      throw new Error(`Operation took ${duration}ms, expected <= ${maxTime}ms`);
    }

    return result;
  }

  /**
   * Test that an async operation takes at least a minimum time
   */
  static async expectToTakeAtLeast<T>(
    operation: () => Promise<T>,
    minTime: number,
    message?: string
  ): Promise<T> {
    const start = Date.now();
    const result = await operation();
    const duration = Date.now() - start;

    if (duration < minTime) {
      throw new Error(
        message ?? `Operation took ${duration}ms, expected >= ${minTime}ms`
      );
    }

    return result;
  }

  /**
   * Test that an async operation eventually succeeds after initial failures
   */
  static async expectToEventuallySucceed<T>(
    operation: () => Promise<T>,
    options: {
      timeout?: number;
      interval?: number;
      expectedErrors?: (error: Error) => boolean;
    } = {}
  ): Promise<T> {
    const { timeout = getTestTimeout(), interval = 100, expectedErrors } = options;
    const start = Date.now();

    while (Date.now() - start < timeout) {
      try {
        return await operation();
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        
        if (expectedErrors && !expectedErrors(err)) {
          throw err; // Unexpected error, fail immediately
        }

        await AsyncTestUtils.delay(interval);
      }
    }

    throw new Error(`Operation did not succeed within ${timeout}ms`);
  }

  /**
   * Test concurrent operations for race conditions
   */
  static async testConcurrency<T>(
    operations: Array<() => Promise<T>>,
    options: {
      expectSameResult?: boolean;
      allowFailures?: boolean;
      timeout?: number;
    } = {}
  ): Promise<T[]> {
    const { expectSameResult = false, allowFailures = false, timeout } = options;

    const promises = operations.map(op => 
      timeout ? AsyncTestUtils.withTimeout(op(), timeout) : op()
    );

    let results: T[];

    if (allowFailures) {
      const settledResults = await Promise.allSettled(promises);
      results = settledResults
        .filter((result): result is PromiseFulfilledResult<T> => result.status === 'fulfilled')
        .map(result => result.value);
    } else {
      results = await Promise.all(promises);
    }

    if (expectSameResult && results.length > 1) {
      const firstResult = JSON.stringify(results[0]);
      const allSame = results.every(result => JSON.stringify(result) === firstResult);
      
      if (!allSame) {
        throw new Error('Concurrent operations produced different results');
      }
    }

    return results;
  }
}

/**
 * Export convenience functions for common use cases
 */
export const {
  waitFor,
  waitForPromise,
  waitForAll,
  flushPromises,
  flushAllPromises,
  delay,
  retry,
  withTimeout,
  installFakeTimers,
  restoreTimers,
  advanceTimers,
  advanceToNextTimer,
  runAllTimers,
  getTimerCount,
  clearAllTimers
} = AsyncTestUtils;

export const {
  expectToCompleteWithin,
  expectToTakeAtLeast,
  expectToEventuallySucceed,
  testConcurrency
} = AsyncTestPatterns;

/**
 * Create a new timing controller for orchestrating async operations
 */
export function createTimingController(): TimingController {
  return new TimingController();
}

/**
 * Configure async test utilities globally
 */
export function configureAsyncTests(config: Partial<AsyncTestConfig>): void {
  AsyncTestUtils.configure(config);
}