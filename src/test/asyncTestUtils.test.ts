/**
 * Tests for async operation test utilities
 * Verifies Promise-based operations, timeout management, and timing control
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  AsyncTestUtils,
  TimingController,
  AsyncTestPatterns,
  waitFor,
  waitForPromise,
  flushPromises,
  delay,
  retry,
  withTimeout,
  expectToCompleteWithin,
  expectToEventuallySucceed,
  testConcurrency,
  createTimingController,
  getTestTimeout,
  configureAsyncTests,
  DEFAULT_ASYNC_CONFIG
} from './asyncTestUtils';

describe('AsyncTestUtils', () => {
  beforeEach(() => {
    // Reset configuration before each test
    AsyncTestUtils.configure(DEFAULT_ASYNC_CONFIG);
    AsyncTestUtils.restoreTimers();
  });

  afterEach(() => {
    AsyncTestUtils.restoreTimers();
    AsyncTestUtils.clearAllTimers();
  });

  describe('waitFor', () => {
    it('should wait for condition to become true', async () => {
      let counter = 0;
      const condition = () => {
        counter++;
        return counter >= 3;
      };

      await waitFor(condition, { timeout: 1000, interval: 10 });
      expect(counter).toBeGreaterThanOrEqual(3);
    });

    it('should timeout if condition never becomes true', async () => {
      const condition = () => false;

      await expect(
        waitFor(condition, { timeout: 100, interval: 10 })
      ).rejects.toThrow('Condition was not met within timeout');
    });

    it('should work with async conditions', async () => {
      let counter = 0;
      const condition = async () => {
        await delay(10);
        counter++;
        return counter >= 2;
      };

      await waitFor(condition, { timeout: 1000, interval: 50 });
      expect(counter).toBeGreaterThanOrEqual(2);
    });

    it('should provide custom error message', async () => {
      const condition = () => false;
      const customMessage = 'Custom timeout message';

      await expect(
        waitFor(condition, { timeout: 100, message: customMessage })
      ).rejects.toThrow(customMessage);
    });
  });

  describe('waitForPromise', () => {
    it('should resolve when promise resolves within timeout', async () => {
      const promise = delay(50).then(() => 'success');
      const result = await waitForPromise(promise, 200);
      expect(result).toBe('success');
    });

    it('should reject when promise takes too long', async () => {
      const promise = delay(200).then(() => 'success');
      
      await expect(
        waitForPromise(promise, 100)
      ).rejects.toThrow('Promise did not resolve within 100ms');
    });

    it('should provide custom timeout message', async () => {
      const promise = delay(200).then(() => 'success');
      const customMessage = 'Custom promise timeout';
      
      await expect(
        waitForPromise(promise, 100, customMessage)
      ).rejects.toThrow(customMessage);
    });
  });

  describe('waitForAll', () => {
    it('should wait for all promises to resolve', async () => {
      const promises = [
        { promise: delay(50).then(() => 'first') },
        { promise: delay(100).then(() => 'second') },
        { promise: delay(75).then(() => 'third') }
      ];

      const results = await AsyncTestUtils.waitForAll(promises);
      expect(results).toEqual(['first', 'second', 'third']);
    });

    it('should handle individual timeouts', async () => {
      const promises = [
        { promise: delay(50).then(() => 'fast'), timeout: 100 },
        { promise: delay(200).then(() => 'slow'), timeout: 150 }
      ];

      await expect(
        AsyncTestUtils.waitForAll(promises)
      ).rejects.toThrow('Promise 1 timed out');
    });

    it('should handle global timeout', async () => {
      const promises = [
        { promise: delay(100).then(() => 'first') },
        { promise: delay(200).then(() => 'second') }
      ];

      await expect(
        AsyncTestUtils.waitForAll(promises, { globalTimeout: 150 })
      ).rejects.toThrow('Global timeout of 150ms exceeded');
    });

    it('should handle failures gracefully when allowFailures is false', async () => {
      const promises = [
        { promise: Promise.resolve('success') },
        { promise: Promise.reject(new Error('failure')) }
      ];

      await expect(
        AsyncTestUtils.waitForAll(promises, { failFast: false })
      ).rejects.toThrow('Some promises failed');
    });
  });

  describe('flushPromises', () => {
    it('should flush pending promises', async () => {
      let resolved = false;
      Promise.resolve().then(() => {
        resolved = true;
      });

      expect(resolved).toBe(false);
      await flushPromises();
      expect(resolved).toBe(true);
    });

    it('should flush all nested promises', async () => {
      let counter = 0;
      
      Promise.resolve().then(() => {
        counter++;
        return Promise.resolve().then(() => {
          counter++;
          return Promise.resolve().then(() => {
            counter++;
          });
        });
      });

      expect(counter).toBe(0);
      await AsyncTestUtils.flushAllPromises();
      expect(counter).toBe(3);
    });
  });

  describe('retry', () => {
    it('should succeed on first attempt', async () => {
      const operation = vi.fn().mockResolvedValue('success');
      const result = await retry(operation);
      
      expect(result).toBe('success');
      expect(operation).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure and eventually succeed', async () => {
      const operation = vi.fn()
        .mockRejectedValueOnce(new Error('fail 1'))
        .mockRejectedValueOnce(new Error('fail 2'))
        .mockResolvedValue('success');

      const result = await retry(operation, { maxAttempts: 3, baseDelay: 10 });
      
      expect(result).toBe('success');
      expect(operation).toHaveBeenCalledTimes(3);
    });

    it('should fail after max attempts', async () => {
      const operation = vi.fn().mockRejectedValue(new Error('persistent failure'));

      await expect(
        retry(operation, { maxAttempts: 2, baseDelay: 10 })
      ).rejects.toThrow('persistent failure');
      
      expect(operation).toHaveBeenCalledTimes(2);
    });

    it('should respect shouldRetry condition', async () => {
      const operation = vi.fn().mockRejectedValue(new Error('non-retryable'));
      const shouldRetry = vi.fn().mockReturnValue(false);

      await expect(
        retry(operation, { shouldRetry, baseDelay: 10 })
      ).rejects.toThrow('non-retryable');
      
      expect(operation).toHaveBeenCalledTimes(1);
      expect(shouldRetry).toHaveBeenCalledWith(expect.any(Error), 1);
    });
  });

  describe('withTimeout', () => {
    it('should resolve when promise resolves before timeout', async () => {
      const promise = delay(50).then(() => 'success');
      const result = await withTimeout(promise, 100);
      expect(result).toBe('success');
    });

    it('should reject when timeout is exceeded', async () => {
      const promise = delay(200).then(() => 'success');
      
      await expect(
        withTimeout(promise, 100)
      ).rejects.toThrow('Operation timed out after 100ms');
    });
  });

  describe('fake timers', () => {
    it('should install and restore fake timers', () => {
      expect(AsyncTestUtils.getTimerCount()).toBe(0);
      
      AsyncTestUtils.installFakeTimers();
      
      setTimeout(() => {}, 1000);
      expect(AsyncTestUtils.getTimerCount()).toBe(1);
      
      AsyncTestUtils.restoreTimers();
    });

    it('should advance timers', async () => {
      AsyncTestUtils.installFakeTimers();
      
      let executed = false;
      setTimeout(() => {
        executed = true;
      }, 1000);

      expect(executed).toBe(false);
      await AsyncTestUtils.advanceTimers(1000);
      expect(executed).toBe(true);
      
      AsyncTestUtils.restoreTimers();
    });

    it('should run all timers', async () => {
      AsyncTestUtils.installFakeTimers();
      
      const results: number[] = [];
      setTimeout(() => results.push(1), 100);
      setTimeout(() => results.push(2), 200);
      setTimeout(() => results.push(3), 300);

      expect(results).toEqual([]);
      await AsyncTestUtils.runAllTimers();
      expect(results).toEqual([1, 2, 3]);
      
      AsyncTestUtils.restoreTimers();
    });
  });
});

describe('TimingController', () => {
  let controller: TimingController;

  beforeEach(() => {
    controller = createTimingController();
  });

  it('should execute operations in dependency order', async () => {
    const results: string[] = [];

    controller.addOperation('first', async () => {
      await delay(10);
      results.push('first');
      return 'first-result';
    });

    controller.addOperation('second', async () => {
      await delay(10);
      results.push('second');
      return 'second-result';
    }, ['first']);

    controller.addOperation('third', async () => {
      await delay(10);
      results.push('third');
      return 'third-result';
    }, ['first', 'second']);

    const operationResults = await controller.executeAll();

    expect(results).toEqual(['first', 'second', 'third']);
    expect(operationResults.get('first')).toBe('first-result');
    expect(operationResults.get('second')).toBe('second-result');
    expect(operationResults.get('third')).toBe('third-result');
  });

  it('should handle operations without dependencies', async () => {
    const results: string[] = [];

    controller.addOperation('a', async () => {
      results.push('a');
      return 'a';
    });

    controller.addOperation('b', async () => {
      results.push('b');
      return 'b';
    });

    await controller.executeAll();

    expect(results).toHaveLength(2);
    expect(results).toContain('a');
    expect(results).toContain('b');
  });

  it('should detect circular dependencies', async () => {
    controller.addOperation('a', async () => 'a', ['b']);
    controller.addOperation('b', async () => 'b', ['a']);

    await expect(controller.executeAll()).rejects.toThrow('Circular dependency');
  });

  it('should provide execution status', () => {
    controller.addOperation('op1', async () => 'result1');
    controller.addOperation('op2', async () => 'result2', ['op1']);

    const status = controller.getStatus();
    expect(status.total).toBe(2);
    expect(status.completed).toBe(0);
    expect(status.pending).toEqual(['op1', 'op2']);
    expect(status.failed).toEqual([]);
  });
});

describe('AsyncTestPatterns', () => {
  describe('expectToCompleteWithin', () => {
    it('should pass when operation completes within time limit', async () => {
      const operation = () => delay(50).then(() => 'success');
      const result = await expectToCompleteWithin(operation, 100);
      expect(result).toBe('success');
    });

    it('should fail when operation takes too long', async () => {
      const operation = () => delay(200).then(() => 'success');
      
      await expect(
        expectToCompleteWithin(operation, 100)
      ).rejects.toThrow('Operation should complete within 100ms');
    });
  });

  describe('expectToEventuallySucceed', () => {
    it('should succeed when operation eventually works', async () => {
      let attempts = 0;
      const operation = async () => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Not ready yet');
        }
        return 'success';
      };

      const result = await expectToEventuallySucceed(operation, {
        timeout: 1000,
        interval: 50
      });
      
      expect(result).toBe('success');
      expect(attempts).toBe(3);
    });

    it('should fail with unexpected errors', async () => {
      const operation = async () => {
        throw new Error('Unexpected error');
      };

      const expectedErrors = (error: Error) => error.message === 'Expected error';

      await expect(
        expectToEventuallySucceed(operation, {
          timeout: 200,
          interval: 50,
          expectedErrors
        })
      ).rejects.toThrow('Unexpected error');
    });
  });

  describe('testConcurrency', () => {
    it('should run operations concurrently', async () => {
      const startTime = Date.now();
      const operations = [
        () => delay(100).then(() => 'first'),
        () => delay(100).then(() => 'second'),
        () => delay(100).then(() => 'third')
      ];

      const results = await testConcurrency(operations);
      const duration = Date.now() - startTime;

      expect(results).toEqual(['first', 'second', 'third']);
      expect(duration).toBeLessThan(200); // Should be much less than 300ms if truly concurrent
    });

    it('should verify same results when expected', async () => {
      const operations = [
        () => Promise.resolve('same'),
        () => Promise.resolve('same'),
        () => Promise.resolve('same')
      ];

      const results = await testConcurrency(operations, { expectSameResult: true });
      expect(results).toEqual(['same', 'same', 'same']);
    });

    it('should fail when results differ and same result expected', async () => {
      const operations = [
        () => Promise.resolve('different1'),
        () => Promise.resolve('different2')
      ];

      await expect(
        testConcurrency(operations, { expectSameResult: true })
      ).rejects.toThrow('Concurrent operations produced different results');
    });
  });
});

describe('Configuration', () => {
  it('should use default configuration', () => {
    const timeout = getTestTimeout();
    expect(timeout).toBe(DEFAULT_ASYNC_CONFIG.defaultTimeout);
  });

  it('should use CI timeout in CI environment', () => {
    const originalEnv = process.env.CI;
    process.env.CI = 'true';
    
    const timeout = getTestTimeout();
    expect(timeout).toBe(DEFAULT_ASYNC_CONFIG.ciTimeout);
    
    process.env.CI = originalEnv;
  });

  it('should allow custom configuration', () => {
    const customConfig = { defaultTimeout: 2000, ciTimeout: 8000 };
    configureAsyncTests(customConfig);
    
    const timeout = getTestTimeout(customConfig);
    expect(timeout).toBe(2000);
  });
});