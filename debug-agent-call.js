// Simple test to debug the agent call issue
const request = {
  jsonrpc: '2.0',
  method: 'getHillMetrics',
  params: {
    bounds: {
      north: 46.0,
      south: 45.9,
      east: 7.1,
      west: 7.0
    },
    grid_size: '64x64',
    include_surface_classification: true
  },
  id: 'debug-test'
};

console.log('Making request to hill metrics agent...');
console.log('Request:', JSON.stringify(request, null, 2));

fetch('http://localhost:8001/jsonrpc', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(request)
})
.then(response => {
  console.log('Response status:', response.status);
  console.log('Response ok:', response.ok);
  console.log('Response headers:', Object.fromEntries(response.headers.entries()));
  return response.text();
})
.then(text => {
  console.log('Response text length:', text.length);
  console.log('Response text (first 500 chars):', text.substring(0, 500));
  if (text.length > 0) {
    try {
      const json = JSON.parse(text);
      console.log('Parsed JSON keys:', Object.keys(json));
      console.log('Has result:', 'result' in json);
      console.log('Has error:', 'error' in json);
    } catch (e) {
      console.error('JSON parse error:', e);
    }
  }
})
.catch(error => {
  console.error('Fetch error:', error);
});