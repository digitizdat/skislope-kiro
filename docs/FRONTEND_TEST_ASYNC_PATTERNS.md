# Frontend Test Async Testing Best Practices

## Overview

This guide provides comprehensive best practices for testing asynchronous operations in the Alpine Ski Simulator frontend test environment. It covers patterns for handling Promises, timeouts, race conditions, and complex async workflows.

## Table of Contents

1. [Async Testing Fundamentals](#async-testing-fundamentals)
2. [Promise-based Testing Patterns](#promise-based-testing-patterns)
3. [Timeout Management](#timeout-management)
4. [Race Condition Testing](#race-condition-testing)
5. [Event-driven Async Testing](#event-driven-async-testing)
6. [Timer and Scheduling Testing](#timer-and-scheduling-testing)
7. [Error Handling in Async Tests](#error-handling-in-async-tests)
8. [Performance Testing Async Operations](#performance-testing-async-operations)
9. [Complex Async Workflow Testing](#complex-async-workflow-testing)
10. [Debugging Async Test Issues](#debugging-async-test-issues)

## Async Testing Fundamentals

### Basic Async Test Structure

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { initializeTestEnvironment } from '../test/testSetup';
import { waitFor, delay, withTimeout } from '../test/asyncTestUtils';

describe('Async Testing Fundamentals', () => {
  beforeEach(async () => {
    await initializeTestEnvironment();
  });

  it('should handle basic async operations', async () => {
    const asyncOperation = async () => {
      await delay(100);
      return 'completed';
    };

    const result = await asyncOperation();
    expect(result).toBe('completed');
  });

  it('should use proper async/await patterns', async () => {
    const service = new TerrainService();
    
    // Always await async operations
    const data = await service.loadTerrainData('test-run');
    
    expect(data).toBeDefined();
    expect(data.elevation).toBeInstanceOf(Array);
  });
});
```

### Common Async Testing Mistakes

```typescript
describe('Common Async Mistakes', () => {
  it('❌ WRONG: Missing await', () => {
    // This test will pass even if the operation fails
    const promise = asyncOperation();
    expect(promise).toBeInstanceOf(Promise);
  });

  it('✅ CORRECT: Proper await', async () => {
    const result = await asyncOperation();
    expect(result).toBe('expected-value');
  });

  it('❌ WRONG: Not returning promise', () => {
    // Test completes before async operation
    asyncOperation().then(result => {
      expect(result).toBe('expected-value');
    });
  });

  it('✅ CORRECT: Return promise or use async/await', async () => {
    const result = await asyncOperation();
    expect(result).toBe('expected-value');
  });
});
```

## Promise-based Testing Patterns

### Testing Promise Resolution

```typescript
describe('Promise Resolution Patterns', () => {
  it('should test promise resolution', async () => {
    const promise = new Promise(resolve => {
      setTimeout(() => resolve('success'), 100);
    });

    const result = await promise;
    expect(result).toBe('success');
  });

  it('should test promise rejection', async () => {
    const promise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('failure')), 100);
    });

    await expect(promise).rejects.toThrow('failure');
  });

  it('should test promise with timeout', async () => {
    const slowPromise = new Promise(resolve => {
      setTimeout(() => resolve('slow'), 5000);
    });

    // Use timeout to prevent test hanging
    await expect(
      withTimeout(slowPromise, 1000, 'Promise timeout')
    ).rejects.toThrow('Promise timeout');
  });
});
```

### Testing Multiple Promises

```typescript
describe('Multiple Promise Patterns', () => {
  it('should test Promise.all', async () => {
    const promises = [
      delay(50).then(() => 'first'),
      delay(100).then(() => 'second'),
      delay(75).then(() => 'third')
    ];

    const results = await Promise.all(promises);
    
    expect(results).toEqual(['first', 'second', 'third']);
  });

  it('should test Promise.allSettled', async () => {
    const promises = [
      Promise.resolve('success'),
      Promise.reject(new Error('failure')),
      delay(50).then(() => 'delayed')
    ];

    const results = await Promise.allSettled(promises);
    
    expect(results[0].status).toBe('fulfilled');
    expect(results[0].value).toBe('success');
    expect(results[1].status).toBe('rejected');
    expect(results[1].reason.message).toBe('failure');
    expect(results[2].status).toBe('fulfilled');
    expect(results[2].value).toBe('delayed');
  });

  it('should test Promise.race', async () => {
    const promises = [
      delay(100).then(() => 'slow'),
      delay(50).then(() => 'fast'),
      delay(200).then(() => 'slowest')
    ];

    const result = await Promise.race(promises);
    expect(result).toBe('fast');
  });
});
```

### Testing Promise Chains

```typescript
describe('Promise Chain Patterns', () => {
  it('should test promise chains', async () => {
    const result = await Promise.resolve(1)
      .then(x => x * 2)
      .then(x => x + 1)
      .then(x => `result: ${x}`);

    expect(result).toBe('result: 3');
  });

  it('should test error propagation in chains', async () => {
    const promise = Promise.resolve(1)
      .then(x => x * 2)
      .then(() => {
        throw new Error('chain error');
      })
      .then(x => `result: ${x}`)
      .catch(error => `caught: ${error.message}`);

    const result = await promise;
    expect(result).toBe('caught: chain error');
  });
});
```

## Timeout Management

### Environment-aware Timeouts

```typescript
import { getTestTimeout } from '../test/asyncTestUtils';

describe('Timeout Management', () => {
  it('should use environment-appropriate timeouts', async () => {
    const timeout = getTestTimeout(); // Adjusts for CI vs local
    
    const operation = async () => {
      await delay(timeout / 2); // Use half the timeout
      return 'completed';
    };

    const result = await withTimeout(
      operation(),
      timeout,
      'Operation should complete within environment timeout'
    );

    expect(result).toBe('completed');
  });

  it('should handle different timeout scenarios', async () => {
    const fastOperation = () => delay(10).then(() => 'fast');
    const slowOperation = () => delay(1000).then(() => 'slow');

    // Fast operation should complete quickly
    const fastResult = await withTimeout(fastOperation(), 100);
    expect(fastResult).toBe('fast');

    // Slow operation should timeout
    await expect(
      withTimeout(slowOperation(), 100, 'Slow operation timeout')
    ).rejects.toThrow('Slow operation timeout');
  });
});
```

### Custom Timeout Utilities

```typescript
describe('Custom Timeout Patterns', () => {
  it('should create custom timeout wrapper', async () => {
    const createTimeoutWrapper = <T>(
      promise: Promise<T>,
      timeoutMs: number,
      errorMessage?: string
    ): Promise<T> => {
      return Promise.race([
        promise,
        new Promise<never>((_, reject) => {
          setTimeout(() => {
            reject(new Error(errorMessage || `Timeout after ${timeoutMs}ms`));
          }, timeoutMs);
        })
      ]);
    };

    const slowOperation = () => delay(500).then(() => 'completed');

    await expect(
      createTimeoutWrapper(slowOperation(), 100, 'Custom timeout')
    ).rejects.toThrow('Custom timeout');
  });

  it('should handle timeout with cleanup', async () => {
    let cleanupCalled = false;
    
    const operationWithCleanup = async () => {
      try {
        await delay(1000);
        return 'completed';
      } finally {
        cleanupCalled = true;
      }
    };

    await expect(
      withTimeout(operationWithCleanup(), 100, 'Cleanup timeout')
    ).rejects.toThrow('Cleanup timeout');

    // Wait a bit for cleanup to run
    await delay(50);
    expect(cleanupCalled).toBe(true);
  });
});
```

## Race Condition Testing

### Testing Concurrent Operations

```typescript
describe('Race Condition Testing', () => {
  it('should test concurrent cache operations', async () => {
    const mockCacheManager = createMockCacheManager();
    await mockCacheManager.initialize();

    const operations = [];
    const testData = { elevation: [1, 2, 3] };

    // Start multiple concurrent operations
    for (let i = 0; i < 10; i++) {
      operations.push(
        mockCacheManager.cacheTerrainData(
          testData,
          { id: `run-${i}`, skiAreaId: 'test-area' },
          'medium'
        )
      );
    }

    // All operations should complete successfully
    await Promise.all(operations);

    expect(mockCacheManager.getTerrainCacheSize()).toBe(10);
  });

  it('should test race condition with shared resource', async () => {
    let sharedCounter = 0;
    const incrementCounter = async () => {
      const current = sharedCounter;
      await delay(10); // Simulate async operation
      sharedCounter = current + 1;
    };

    // Start multiple concurrent increments
    const operations = Array(5).fill(0).map(() => incrementCounter());
    await Promise.all(operations);

    // Due to race condition, final value may be less than 5
    expect(sharedCounter).toBeLessThanOrEqual(5);
    expect(sharedCounter).toBeGreaterThan(0);
  });

  it('should test proper synchronization', async () => {
    let sharedCounter = 0;
    const mutex = { locked: false };

    const synchronizedIncrement = async () => {
      // Wait for mutex
      while (mutex.locked) {
        await delay(1);
      }
      
      mutex.locked = true;
      try {
        const current = sharedCounter;
        await delay(10);
        sharedCounter = current + 1;
      } finally {
        mutex.locked = false;
      }
    };

    const operations = Array(5).fill(0).map(() => synchronizedIncrement());
    await Promise.all(operations);

    expect(sharedCounter).toBe(5);
  });
});
```

### Testing Order Dependencies

```typescript
describe('Order Dependency Testing', () => {
  it('should test operations that must run in order', async () => {
    const results = [];
    
    const orderedOperation = async (id: number, delay: number) => {
      await delay(delay);
      results.push(id);
      return id;
    };

    // Start operations with different delays
    const promises = [
      orderedOperation(1, 100),
      orderedOperation(2, 50),
      orderedOperation(3, 75)
    ];

    await Promise.all(promises);

    // Results should be in completion order, not start order
    expect(results).toEqual([2, 3, 1]);
  });

  it('should enforce sequential execution', async () => {
    const results = [];
    
    const sequentialOperation = async (id: number) => {
      await delay(50);
      results.push(id);
      return id;
    };

    // Execute operations sequentially
    for (let i = 1; i <= 3; i++) {
      await sequentialOperation(i);
    }

    expect(results).toEqual([1, 2, 3]);
  });
});
```

## Event-driven Async Testing

### Testing Event Emitters

```typescript
describe('Event-driven Async Testing', () => {
  it('should test event-based async operations', async () => {
    const eventTarget = new EventTarget();
    let eventData = null;

    const eventPromise = new Promise(resolve => {
      eventTarget.addEventListener('data-loaded', (event) => {
        eventData = event.detail;
        resolve(event.detail);
      });
    });

    // Simulate async event emission
    setTimeout(() => {
      eventTarget.dispatchEvent(new CustomEvent('data-loaded', {
        detail: { message: 'data loaded' }
      }));
    }, 50);

    const result = await eventPromise;
    
    expect(result).toEqual({ message: 'data loaded' });
    expect(eventData).toEqual({ message: 'data loaded' });
  });

  it('should test multiple event listeners', async () => {
    const eventTarget = new EventTarget();
    const results = [];

    const createListener = (id: string) => {
      return new Promise(resolve => {
        eventTarget.addEventListener('test-event', (event) => {
          results.push(`${id}: ${event.detail.message}`);
          resolve(id);
        });
      });
    };

    const listeners = [
      createListener('listener1'),
      createListener('listener2'),
      createListener('listener3')
    ];

    // Emit event
    eventTarget.dispatchEvent(new CustomEvent('test-event', {
      detail: { message: 'hello' }
    }));

    await Promise.all(listeners);

    expect(results).toHaveLength(3);
    expect(results).toContain('listener1: hello');
    expect(results).toContain('listener2: hello');
    expect(results).toContain('listener3: hello');
  });
});
```

### Testing DOM Events

```typescript
describe('DOM Event Testing', () => {
  it('should test async DOM events', async () => {
    const button = document.createElement('button');
    document.body.appendChild(button);

    let clickHandled = false;
    const clickPromise = new Promise(resolve => {
      button.addEventListener('click', async () => {
        await delay(50); // Simulate async handler
        clickHandled = true;
        resolve(true);
      });
    });

    button.click();
    await clickPromise;

    expect(clickHandled).toBe(true);
    
    document.body.removeChild(button);
  });

  it('should test event propagation', async () => {
    const parent = document.createElement('div');
    const child = document.createElement('button');
    parent.appendChild(child);
    document.body.appendChild(parent);

    const events = [];
    
    const parentPromise = new Promise(resolve => {
      parent.addEventListener('click', () => {
        events.push('parent');
        resolve('parent');
      });
    });

    const childPromise = new Promise(resolve => {
      child.addEventListener('click', () => {
        events.push('child');
        resolve('child');
      });
    });

    child.click();
    
    await Promise.all([parentPromise, childPromise]);

    expect(events).toEqual(['child', 'parent']);
    
    document.body.removeChild(parent);
  });
});
```

## Timer and Scheduling Testing

### Testing with Fake Timers

```typescript
import { installFakeTimers, restoreTimers, advanceTimers } from '../test/asyncTestUtils';

describe('Timer Testing', () => {
  beforeEach(() => {
    installFakeTimers();
  });

  afterEach(() => {
    restoreTimers();
  });

  it('should test setTimeout with fake timers', async () => {
    let executed = false;
    
    setTimeout(() => {
      executed = true;
    }, 1000);

    expect(executed).toBe(false);
    
    await advanceTimers(1000);
    
    expect(executed).toBe(true);
  });

  it('should test setInterval with fake timers', async () => {
    let count = 0;
    
    const intervalId = setInterval(() => {
      count++;
    }, 100);

    await advanceTimers(250);
    expect(count).toBe(2);

    await advanceTimers(150);
    expect(count).toBe(4);

    clearInterval(intervalId);
  });

  it('should test complex timer interactions', async () => {
    const events = [];
    
    setTimeout(() => events.push('timeout1'), 100);
    setTimeout(() => events.push('timeout2'), 200);
    
    const intervalId = setInterval(() => {
      events.push('interval');
    }, 150);

    await advanceTimers(100);
    expect(events).toEqual(['timeout1']);

    await advanceTimers(50);
    expect(events).toEqual(['timeout1', 'interval']);

    await advanceTimers(50);
    expect(events).toEqual(['timeout1', 'interval', 'timeout2']);

    clearInterval(intervalId);
  });
});
```

### Testing Animation Frames

```typescript
describe('Animation Frame Testing', () => {
  it('should test requestAnimationFrame', async () => {
    let frameExecuted = false;
    
    const framePromise = new Promise(resolve => {
      requestAnimationFrame(() => {
        frameExecuted = true;
        resolve(true);
      });
    });

    // Simulate frame
    await framePromise;
    
    expect(frameExecuted).toBe(true);
  });

  it('should test animation loop', async () => {
    let frameCount = 0;
    let animationId;
    
    const animate = () => {
      frameCount++;
      if (frameCount < 5) {
        animationId = requestAnimationFrame(animate);
      }
    };

    const animationPromise = new Promise(resolve => {
      const checkComplete = () => {
        if (frameCount >= 5) {
          resolve(frameCount);
        } else {
          setTimeout(checkComplete, 16); // ~60fps
        }
      };
      checkComplete();
    });

    animate();
    
    const finalCount = await animationPromise;
    expect(finalCount).toBe(5);
    
    if (animationId) {
      cancelAnimationFrame(animationId);
    }
  });
});
```

## Error Handling in Async Tests

### Testing Async Error Scenarios

```typescript
describe('Async Error Handling', () => {
  it('should test promise rejection', async () => {
    const failingOperation = async () => {
      await delay(50);
      throw new Error('Operation failed');
    };

    await expect(failingOperation()).rejects.toThrow('Operation failed');
  });

  it('should test error propagation in chains', async () => {
    const chainWithError = Promise.resolve(1)
      .then(x => x * 2)
      .then(() => {
        throw new Error('Chain error');
      })
      .then(x => x + 1); // This won't execute

    await expect(chainWithError).rejects.toThrow('Chain error');
  });

  it('should test error recovery', async () => {
    const operationWithRecovery = async () => {
      try {
        await delay(50);
        throw new Error('Initial failure');
      } catch (error) {
        await delay(25);
        return 'recovered';
      }
    };

    const result = await operationWithRecovery();
    expect(result).toBe('recovered');
  });

  it('should test timeout vs error', async () => {
    const slowFailingOperation = async () => {
      await delay(1000);
      throw new Error('Slow failure');
    };

    // Should timeout before the error occurs
    await expect(
      withTimeout(slowFailingOperation(), 100, 'Timeout error')
    ).rejects.toThrow('Timeout error');
  });
});
```

### Testing Error Boundaries

```typescript
describe('Error Boundary Testing', () => {
  it('should test async error in component', async () => {
    const AsyncComponent = () => {
      const [error, setError] = useState(null);
      
      useEffect(() => {
        const loadData = async () => {
          try {
            await delay(50);
            throw new Error('Async component error');
          } catch (err) {
            setError(err.message);
          }
        };
        
        loadData();
      }, []);

      if (error) {
        throw new Error(error);
      }

      return <div>Loading...</div>;
    };

    const ErrorBoundary = ({ children }) => {
      const [hasError, setHasError] = useState(false);
      
      useEffect(() => {
        const handleError = () => setHasError(true);
        window.addEventListener('error', handleError);
        return () => window.removeEventListener('error', handleError);
      }, []);

      if (hasError) {
        return <div>Error caught</div>;
      }

      return children;
    };

    render(
      <ErrorBoundary>
        <AsyncComponent />
      </ErrorBoundary>
    );

    await waitFor(() => {
      expect(screen.getByText('Error caught')).toBeInTheDocument();
    });
  });
});
```

## Performance Testing Async Operations

### Measuring Async Performance

```typescript
describe('Async Performance Testing', () => {
  it('should measure operation duration', async () => {
    const operation = async () => {
      await delay(100);
      return 'completed';
    };

    const startTime = performance.now();
    const result = await operation();
    const endTime = performance.now();

    const duration = endTime - startTime;
    
    expect(result).toBe('completed');
    expect(duration).toBeGreaterThanOrEqual(100);
    expect(duration).toBeLessThan(150); // Allow some variance
  });

  it('should test concurrent performance', async () => {
    const operation = async (id: number) => {
      await delay(100);
      return `result-${id}`;
    };

    const startTime = performance.now();
    
    const promises = Array(5).fill(0).map((_, i) => operation(i));
    const results = await Promise.all(promises);
    
    const endTime = performance.now();
    const duration = endTime - startTime;

    expect(results).toHaveLength(5);
    expect(duration).toBeLessThan(150); // Should be ~100ms, not 500ms
  });

  it('should test throughput', async () => {
    const operations = [];
    const startTime = performance.now();

    for (let i = 0; i < 100; i++) {
      operations.push(
        delay(10).then(() => `operation-${i}`)
      );
    }

    const results = await Promise.all(operations);
    const endTime = performance.now();

    const duration = endTime - startTime;
    const throughput = results.length / (duration / 1000); // ops per second

    expect(results).toHaveLength(100);
    expect(throughput).toBeGreaterThan(50); // At least 50 ops/sec
  });
});
```

### Memory Usage Testing

```typescript
describe('Async Memory Testing', () => {
  it('should test memory cleanup', async () => {
    const createLargeData = () => {
      return new Array(10000).fill(0).map((_, i) => ({ id: i, data: `item-${i}` }));
    };

    const processData = async (data) => {
      await delay(50);
      return data.length;
    };

    // Create and process large data
    let largeData = createLargeData();
    const result = await processData(largeData);
    
    expect(result).toBe(10000);
    
    // Clear reference to allow garbage collection
    largeData = null;
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    // Test should complete without memory issues
    expect(result).toBe(10000);
  });
});
```

## Complex Async Workflow Testing

### Testing Async State Machines

```typescript
describe('Complex Async Workflows', () => {
  it('should test async state machine', async () => {
    class AsyncStateMachine {
      private state = 'idle';
      private data = null;

      async start() {
        if (this.state !== 'idle') {
          throw new Error('Already started');
        }
        
        this.state = 'loading';
        await delay(50);
        this.data = 'loaded';
        this.state = 'ready';
      }

      async process() {
        if (this.state !== 'ready') {
          throw new Error('Not ready');
        }
        
        this.state = 'processing';
        await delay(75);
        this.data = 'processed';
        this.state = 'complete';
      }

      getState() {
        return this.state;
      }

      getData() {
        return this.data;
      }
    }

    const machine = new AsyncStateMachine();
    
    expect(machine.getState()).toBe('idle');
    
    await machine.start();
    expect(machine.getState()).toBe('ready');
    expect(machine.getData()).toBe('loaded');
    
    await machine.process();
    expect(machine.getState()).toBe('complete');
    expect(machine.getData()).toBe('processed');
  });

  it('should test workflow with dependencies', async () => {
    const workflow = {
      tasks: new Map(),
      
      async addTask(id: string, dependencies: string[], operation: () => Promise<any>) {
        this.tasks.set(id, {
          dependencies,
          operation,
          completed: false,
          result: null
        });
      },
      
      async execute() {
        const completed = new Set();
        const results = new Map();
        
        while (completed.size < this.tasks.size) {
          for (const [id, task] of this.tasks) {
            if (task.completed) continue;
            
            const dependenciesMet = task.dependencies.every(dep => completed.has(dep));
            
            if (dependenciesMet) {
              task.result = await task.operation();
              task.completed = true;
              completed.add(id);
              results.set(id, task.result);
            }
          }
          
          await delay(1); // Prevent tight loop
        }
        
        return results;
      }
    };

    await workflow.addTask('task1', [], async () => {
      await delay(50);
      return 'task1-result';
    });

    await workflow.addTask('task2', ['task1'], async () => {
      await delay(25);
      return 'task2-result';
    });

    await workflow.addTask('task3', ['task1'], async () => {
      await delay(75);
      return 'task3-result';
    });

    await workflow.addTask('task4', ['task2', 'task3'], async () => {
      await delay(10);
      return 'task4-result';
    });

    const results = await workflow.execute();
    
    expect(results.get('task1')).toBe('task1-result');
    expect(results.get('task2')).toBe('task2-result');
    expect(results.get('task3')).toBe('task3-result');
    expect(results.get('task4')).toBe('task4-result');
  });
});
```

### Testing Async Pipelines

```typescript
describe('Async Pipeline Testing', () => {
  it('should test data processing pipeline', async () => {
    const pipeline = {
      async stage1(data: number[]) {
        await delay(25);
        return data.map(x => x * 2);
      },
      
      async stage2(data: number[]) {
        await delay(50);
        return data.filter(x => x > 10);
      },
      
      async stage3(data: number[]) {
        await delay(25);
        return data.reduce((sum, x) => sum + x, 0);
      },
      
      async process(input: number[]) {
        const stage1Result = await this.stage1(input);
        const stage2Result = await this.stage2(stage1Result);
        const stage3Result = await this.stage3(stage2Result);
        return stage3Result;
      }
    };

    const input = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const result = await pipeline.process(input);
    
    // [1,2,3,4,5,6,7,8,9,10] -> [2,4,6,8,10,12,14,16,18,20] -> [12,14,16,18,20] -> 80
    expect(result).toBe(80);
  });

  it('should test parallel pipeline stages', async () => {
    const parallelPipeline = {
      async processParallel(input: number[]) {
        const [doubled, tripled] = await Promise.all([
          this.double(input),
          this.triple(input)
        ]);
        
        return this.combine(doubled, tripled);
      },
      
      async double(data: number[]) {
        await delay(50);
        return data.map(x => x * 2);
      },
      
      async triple(data: number[]) {
        await delay(75);
        return data.map(x => x * 3);
      },
      
      async combine(doubled: number[], tripled: number[]) {
        await delay(25);
        return doubled.map((d, i) => d + tripled[i]);
      }
    };

    const input = [1, 2, 3];
    const startTime = performance.now();
    const result = await parallelPipeline.processParallel(input);
    const endTime = performance.now();
    
    expect(result).toEqual([5, 10, 15]); // [2,4,6] + [3,6,9] = [5,10,15]
    expect(endTime - startTime).toBeLessThan(125); // Should be ~100ms, not 150ms
  });
});
```

## Debugging Async Test Issues

### Common Debugging Techniques

```typescript
describe('Async Debugging Techniques', () => {
  it('should debug hanging promises', async () => {
    const debugPromise = async () => {
      console.log('Promise started');
      
      try {
        await delay(100);
        console.log('Delay completed');
        
        const result = 'success';
        console.log('Result:', result);
        
        return result;
      } catch (error) {
        console.error('Promise error:', error);
        throw error;
      }
    };

    const result = await debugPromise();
    expect(result).toBe('success');
  });

  it('should debug race conditions', async () => {
    let operationCount = 0;
    
    const debugOperation = async (id: string) => {
      console.log(`Operation ${id} started`);
      operationCount++;
      
      await delay(Math.random() * 100);
      
      console.log(`Operation ${id} completed, total: ${operationCount}`);
      return id;
    };

    const operations = ['A', 'B', 'C'].map(id => debugOperation(id));
    const results = await Promise.all(operations);
    
    console.log('All operations completed:', results);
    expect(results).toHaveLength(3);
  });

  it('should debug timeout issues', async () => {
    const debugTimeout = async () => {
      console.log('Starting operation with timeout');
      
      const operation = async () => {
        console.log('Operation started');
        await delay(200);
        console.log('Operation completed');
        return 'success';
      };

      try {
        const result = await withTimeout(
          operation(),
          150,
          'Debug timeout exceeded'
        );
        console.log('Operation succeeded:', result);
        return result;
      } catch (error) {
        console.error('Operation failed:', error.message);
        throw error;
      }
    };

    await expect(debugTimeout()).rejects.toThrow('Debug timeout exceeded');
  });
});
```

### Performance Profiling

```typescript
describe('Async Performance Profiling', () => {
  it('should profile async operations', async () => {
    const profiler = {
      timings: new Map(),
      
      async profile<T>(name: string, operation: () => Promise<T>): Promise<T> {
        const start = performance.now();
        
        try {
          const result = await operation();
          const end = performance.now();
          
          this.timings.set(name, end - start);
          console.log(`${name}: ${end - start}ms`);
          
          return result;
        } catch (error) {
          const end = performance.now();
          this.timings.set(name, end - start);
          console.log(`${name} (failed): ${end - start}ms`);
          throw error;
        }
      },
      
      getReport() {
        const report = Array.from(this.timings.entries())
          .map(([name, time]) => ({ name, time }))
          .sort((a, b) => b.time - a.time);
        
        console.table(report);
        return report;
      }
    };

    await profiler.profile('fast-operation', async () => {
      await delay(50);
      return 'fast';
    });

    await profiler.profile('slow-operation', async () => {
      await delay(150);
      return 'slow';
    });

    await profiler.profile('medium-operation', async () => {
      await delay(100);
      return 'medium';
    });

    const report = profiler.getReport();
    
    expect(report[0].name).toBe('slow-operation');
    expect(report[1].name).toBe('medium-operation');
    expect(report[2].name).toBe('fast-operation');
  });
});
```

## Best Practices Summary

### Do's and Don'ts

#### ✅ Do's

1. **Always use async/await** for async operations in tests
2. **Set appropriate timeouts** for different environments
3. **Clean up async operations** in afterEach hooks
4. **Test both success and failure scenarios**
5. **Use proper error handling** with try/catch or expect().rejects
6. **Profile async operations** to ensure performance
7. **Test race conditions** explicitly
8. **Use fake timers** for deterministic timing tests

#### ❌ Don'ts

1. **Don't forget to await** async operations
2. **Don't use fixed delays** without timeouts
3. **Don't ignore promise rejections**
4. **Don't create hanging promises** in tests
5. **Don't mix real and fake timers** without proper cleanup
6. **Don't assume operation order** in concurrent tests
7. **Don't use setTimeout** for synchronization in tests
8. **Don't ignore memory cleanup** in long-running async tests

### Testing Strategy

1. **Unit Tests**: Mock all async dependencies, use fake timers
2. **Integration Tests**: Use real async operations with appropriate timeouts
3. **E2E Tests**: Test complete async workflows with minimal mocking

### Performance Guidelines

1. **Fast Tests**: < 100ms per test
2. **Medium Tests**: < 1000ms per test
3. **Slow Tests**: < 5000ms per test, use sparingly

This comprehensive guide provides the foundation for effective async testing in the Alpine Ski Simulator frontend test environment. Apply these patterns consistently to create reliable, maintainable async tests.