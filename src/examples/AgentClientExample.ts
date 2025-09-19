/**
 * Agent Client Usage Examples
 * Requirements: 8.1, 8.2, 8.5 - Demonstrate agent communication, error handling, health checks
 */

import { agentClient, createAgentClient } from '../services/AgentClient';
import { 
  createDevelopmentAgentClient, 
  testAgentConnectivity, 
  AgentMonitor 
} from '../utils/AgentUtils';
import { AgentType } from '../models/AgentTypes';
import { GridSize } from '../models/TerrainData';
import { PREDEFINED_SKI_AREAS } from '../models/SkiArea';

/**
 * Example ski area for testing (using Chamonix from predefined areas)
 */
const exampleSkiArea = PREDEFINED_SKI_AREAS[0]; // Chamonix

/**
 * Example 1: Basic hill metrics request
 */
async function exampleHillMetricsRequest(): Promise<void> {
  console.log('Example 1: Hill Metrics Request');
  
  try {
    const response = await agentClient.callHillMetricsAgent({
      area: exampleSkiArea,
      gridSize: GridSize.MEDIUM,
      includeAnalysis: true
    });

    console.log('Hill metrics received:');
    console.log('- Grid resolution:', response.metadata.gridResolution);
    console.log('- Processing time:', response.metadata.processingTime, 'ms');
    console.log('- Data source:', response.metadata.dataSource);
    console.log('- Elevation data points:', response.data.elevationData.length);
  } catch (error) {
    console.error('Hill metrics request failed:', error);
  }
}

/**
 * Example 2: Weather data with fallback
 */
async function exampleWeatherRequest(): Promise<void> {
  console.log('\nExample 2: Weather Request with Fallback');
  
  try {
    const response = await agentClient.callWeatherAgent({
      area: exampleSkiArea,
      includeForecast: true,
      forecastHours: 24
    });

    console.log('Weather data received:');
    console.log('- Temperature:', response.current.temperature, '°C');
    console.log('- Wind speed:', response.current.windSpeed, 'km/h');
    console.log('- Snow conditions:', response.current.snowConditions);
    console.log('- Data source:', response.metadata.source);
    console.log('- Accuracy:', response.metadata.accuracy);
    
    if (response.forecast) {
      console.log('- Forecast points:', response.forecast.length);
    }
  } catch (error) {
    console.error('Weather request failed:', error);
  }
}

/**
 * Example 3: Equipment data request
 */
async function exampleEquipmentRequest(): Promise<void> {
  console.log('\nExample 3: Equipment Request');
  
  try {
    const response = await agentClient.callEquipmentAgent({
      area: exampleSkiArea,
      includeStatus: true,
      equipmentTypes: ['lifts', 'trails', 'facilities']
    });

    console.log('Equipment data received:');
    console.log('- Lifts:', response.data.lifts?.length || 0);
    console.log('- Trails:', response.data.trails?.length || 0);
    console.log('- Facilities:', response.data.facilities?.length || 0);
    console.log('- Last updated:', response.metadata.lastUpdated);
    console.log('- Status accuracy:', response.metadata.statusAccuracy);
  } catch (error) {
    console.error('Equipment request failed:', error);
  }
}

/**
 * Example 4: Health checks for all agents
 */
async function exampleHealthChecks(): Promise<void> {
  console.log('\nExample 4: Agent Health Checks');
  
  const agents = [AgentType.HILL_METRICS, AgentType.WEATHER, AgentType.EQUIPMENT];
  
  for (const agentType of agents) {
    try {
      const health = await agentClient.healthCheck(agentType);
      console.log(`${agentType} agent:`, {
        status: health.status,
        responseTime: health.responseTime + 'ms',
        version: health.version,
        uptime: health.metrics?.uptime ? Math.round(health.metrics.uptime / 3600) + 'h' : 'unknown'
      });
    } catch (error) {
      console.error(`${agentType} health check failed:`, error);
    }
  }
}

/**
 * Example 5: Batch requests
 */
async function exampleBatchRequest(): Promise<void> {
  console.log('\nExample 5: Batch Request');
  
  try {
    const batchResponse = await agentClient.batchRequest({
      requests: [
        {
          area: exampleSkiArea,
          gridSize: GridSize.SMALL
        },
        {
          area: exampleSkiArea,
          timestamp: new Date()
        }
      ],
      parallel: true,
      timeout: 15000
    });

    console.log('Batch request completed:');
    console.log('- Total time:', batchResponse.metadata.totalTime, 'ms');
    console.log('- Successful requests:', batchResponse.metadata.successCount);
    console.log('- Failed requests:', batchResponse.metadata.errorCount);
    console.log('- Responses received:', batchResponse.responses.length);
  } catch (error) {
    console.error('Batch request failed:', error);
  }
}

/**
 * Example 6: Agent connectivity testing
 */
async function exampleConnectivityTest(): Promise<void> {
  console.log('\nExample 6: Agent Connectivity Test');
  
  const connectivity = await testAgentConnectivity(agentClient);
  
  console.log('Agent connectivity status:');
  console.log('- Hill Metrics:', connectivity.hillMetrics ? '✓ Connected' : '✗ Disconnected');
  console.log('- Weather:', connectivity.weather ? '✓ Connected' : '✗ Disconnected');
  console.log('- Equipment:', connectivity.equipment ? '✓ Connected' : '✗ Disconnected');
}

/**
 * Example 7: Agent monitoring
 */
async function exampleAgentMonitoring(): Promise<void> {
  console.log('\nExample 7: Agent Monitoring');
  
  const monitor = new AgentMonitor(agentClient);
  
  // Set up status change callback
  monitor.onStatusChange((status) => {
    console.log('Agent status update:', {
      hillMetrics: status.hillMetrics,
      weather: status.weather,
      equipment: status.equipment,
      timestamp: status.timestamp.toISOString()
    });
  });
  
  // Start monitoring every 10 seconds
  monitor.startMonitoring(10000);
  
  console.log('Agent monitoring started (will run for 30 seconds)...');
  
  // Stop monitoring after 30 seconds
  setTimeout(() => {
    monitor.stopMonitoring();
    console.log('Agent monitoring stopped');
  }, 30000);
}

/**
 * Example 8: Development vs Production clients
 */
async function exampleClientConfigurations(): Promise<void> {
  console.log('\nExample 8: Client Configurations');
  
  // Development client with fallback data
  const devClient = createDevelopmentAgentClient();
  console.log('Development client created with fallback data');
  
  // Custom client with specific configuration
  const customClient = createAgentClient({
    hillMetrics: {
      endpoint: 'https://api.example.com/hill-metrics',
      timeout: 20000,
      retryAttempts: 5,
      protocol: 'mcp'
    },
    weather: {
      endpoint: 'https://api.example.com/weather',
      cacheDuration: 600000, // 10 minutes
      protocol: 'jsonrpc'
    }
  }, {
    maxAttempts: 5,
    baseDelay: 2000,
    maxDelay: 30000,
    backoffMultiplier: 2.5,
    retryableErrors: [-32603, -32001, -32004]
  });
  
  console.log('Custom client created with specific configuration');
  
  // Test connectivity with development client
  const devConnectivity = await testAgentConnectivity(devClient);
  console.log('Development client connectivity:', devConnectivity);
  
  // Avoid unused variable warning
  console.log('Custom client endpoint:', customClient.constructor.name);
}

/**
 * Run all examples
 */
export async function runAllExamples(): Promise<void> {
  console.log('=== Agent Client Examples ===\n');
  
  try {
    await exampleHillMetricsRequest();
    await exampleWeatherRequest();
    await exampleEquipmentRequest();
    await exampleHealthChecks();
    await exampleBatchRequest();
    await exampleConnectivityTest();
    await exampleClientConfigurations();
    
    // Note: Agent monitoring example runs for 30 seconds, so we'll skip it in the batch run
    console.log('\nAll examples completed successfully!');
    console.log('Note: Run exampleAgentMonitoring() separately to see monitoring in action.');
  } catch (error) {
    console.error('Example execution failed:', error);
  }
}

// Export individual examples for separate use
export {
  exampleHillMetricsRequest,
  exampleWeatherRequest,
  exampleEquipmentRequest,
  exampleHealthChecks,
  exampleBatchRequest,
  exampleConnectivityTest,
  exampleAgentMonitoring,
  exampleClientConfigurations
};