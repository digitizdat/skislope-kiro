#!/usr/bin/env node

/**
 * Frontend Test Runner Script
 * 
 * Provides consistent test execution across local and CI environments
 * with proper error handling, artifact collection, and reporting.
 */

import { spawn } from 'child_process'
import { existsSync, mkdirSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

// Test configuration
const config = {
  testResultsDir: join(projectRoot, 'test-results'),
  coverageDir: join(projectRoot, 'coverage'),
  isCI: process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true',
  verbose: process.argv.includes('--verbose') || process.env.VERBOSE === 'true'
}

// Ensure directories exist
function ensureDirectories() {
  if (!existsSync(config.testResultsDir)) {
    mkdirSync(config.testResultsDir, { recursive: true })
  }
  if (!existsSync(config.coverageDir)) {
    mkdirSync(config.coverageDir, { recursive: true })
  }
}

// Log function with timestamp
function log(message, level = 'INFO') {
  const timestamp = new Date().toISOString()
  const prefix = config.isCI ? `[${level}]` : `🧪 [${level}]`
  console.log(`${timestamp} ${prefix} ${message}`)
}

// Execute command with proper error handling
function executeCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    log(`Executing: ${command} ${args.join(' ')}`)
    
    const child = spawn(command, args, {
      stdio: config.verbose ? 'inherit' : 'pipe',
      cwd: projectRoot,
      env: {
        ...process.env,
        NODE_ENV: 'test',
        VITEST: 'true',
        ...options.env
      }
    })
    
    let stdout = ''
    let stderr = ''
    
    if (!config.verbose) {
      child.stdout?.on('data', (data) => {
        stdout += data.toString()
      })
      
      child.stderr?.on('data', (data) => {
        stderr += data.toString()
      })
    }
    
    child.on('close', (code) => {
      if (code === 0) {
        log(`Command completed successfully`)
        resolve({ code, stdout, stderr })
      } else {
        log(`Command failed with exit code ${code}`, 'ERROR')
        if (!config.verbose) {
          console.error('STDOUT:', stdout)
          console.error('STDERR:', stderr)
        }
        reject(new Error(`Command failed with exit code ${code}`))
      }
    })
    
    child.on('error', (error) => {
      log(`Command error: ${error.message}`, 'ERROR')
      reject(error)
    })
  })
}

// Test execution functions
async function runUnitTests() {
  log('Running unit tests...')
  return executeCommand('npm', ['run', 'test:unit'])
}

async function runIntegrationTests() {
  log('Running integration tests...')
  return executeCommand('npm', ['run', 'test:integration'])
}

async function runCoverageTests() {
  log('Running tests with coverage...')
  return executeCommand('npm', ['run', 'test:coverage:threshold'])
}

async function runPerformanceTests() {
  log('Running performance tests...')
  return executeCommand('npm', ['run', 'test:performance'])
}

async function validateTestSetup() {
  log('Validating test setup...')
  return executeCommand('npm', ['run', 'test:setup:validate'])
}

async function validateMocks() {
  log('Validating mock infrastructure...')
  return executeCommand('npm', ['run', 'test:mocks:validate'])
}

async function runCITests() {
  log('Running CI test suite...')
  return executeCommand('npm', ['run', 'test:ci'])
}

// Artifact collection
async function collectArtifacts() {
  log('Collecting test artifacts...')
  
  const artifactInfo = {
    timestamp: new Date().toISOString(),
    environment: config.isCI ? 'ci' : 'local',
    nodeVersion: process.version,
    platform: process.platform,
    testResultsDir: config.testResultsDir,
    coverageDir: config.coverageDir
  }
  
  const artifactPath = join(config.testResultsDir, 'artifact-info.json')
  writeFileSync(artifactPath, JSON.stringify(artifactInfo, null, 2))
  
  log(`Artifacts collected in: ${config.testResultsDir}`)
}

// Main execution function
async function main() {
  const command = process.argv[2] || 'all'
  
  try {
    ensureDirectories()
    
    log(`Starting test execution: ${command}`)
    log(`Environment: ${config.isCI ? 'CI' : 'Local'}`)
    log(`Node version: ${process.version}`)
    log(`Platform: ${process.platform}`)
    
    switch (command) {
      case 'unit':
        await runUnitTests()
        break
        
      case 'integration':
        await runIntegrationTests()
        break
        
      case 'coverage':
        await runCoverageTests()
        break
        
      case 'performance':
        await runPerformanceTests()
        break
        
      case 'validate':
        await validateTestSetup()
        await validateMocks()
        break
        
      case 'ci':
        await runCITests()
        break
        
      case 'all':
        await validateTestSetup()
        await validateMocks()
        await runUnitTests()
        await runIntegrationTests()
        await runCoverageTests()
        break
        
      case 'full':
        await validateTestSetup()
        await validateMocks()
        await runUnitTests()
        await runIntegrationTests()
        await runCoverageTests()
        await runPerformanceTests()
        break
        
      default:
        throw new Error(`Unknown command: ${command}`)
    }
    
    await collectArtifacts()
    log('All tests completed successfully! ✅')
    
  } catch (error) {
    log(`Test execution failed: ${error.message}`, 'ERROR')
    await collectArtifacts()
    process.exit(1)
  }
}

// Handle process signals
process.on('SIGINT', () => {
  log('Test execution interrupted', 'WARN')
  process.exit(130)
})

process.on('SIGTERM', () => {
  log('Test execution terminated', 'WARN')
  process.exit(143)
})

// Execute main function
main().catch((error) => {
  console.error('Unhandled error:', error)
  process.exit(1)
})