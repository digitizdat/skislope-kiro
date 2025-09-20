#!/usr/bin/env node

/**
 * Test Environment Validation Script
 * 
 * Validates that the test environment is properly configured
 * and all required dependencies are available.
 */

import { existsSync, readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { spawn } from 'child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

// Validation results
const results = {
  passed: [],
  failed: [],
  warnings: []
}

function log(message, type = 'info') {
  const prefix = {
    info: '📋',
    success: '✅',
    error: '❌',
    warning: '⚠️'
  }[type] || '📋'
  
  console.log(`${prefix} ${message}`)
}

function addResult(test, passed, message) {
  const result = { test, message }
  if (passed) {
    results.passed.push(result)
    log(`${test}: ${message}`, 'success')
  } else {
    results.failed.push(result)
    log(`${test}: ${message}`, 'error')
  }
}

function addWarning(test, message) {
  results.warnings.push({ test, message })
  log(`${test}: ${message}`, 'warning')
}

// Execute command and return result
function executeCommand(command, args = []) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: 'pipe',
      cwd: projectRoot
    })
    
    let stdout = ''
    let stderr = ''
    
    child.stdout?.on('data', (data) => {
      stdout += data.toString()
    })
    
    child.stderr?.on('data', (data) => {
      stderr += data.toString()
    })
    
    child.on('close', (code) => {
      resolve({ code, stdout, stderr })
    })
    
    child.on('error', (error) => {
      resolve({ code: -1, stdout, stderr: error.message })
    })
  })
}

// Validation functions
async function validateNodeVersion() {
  const version = process.version
  const majorVersion = parseInt(version.slice(1).split('.')[0])
  
  if (majorVersion >= 18) {
    addResult('Node.js Version', true, `${version} (>= 18.0.0)`)
  } else {
    addResult('Node.js Version', false, `${version} (requires >= 18.0.0)`)
  }
}

async function validatePackageJson() {
  const packagePath = join(projectRoot, 'package.json')
  
  if (!existsSync(packagePath)) {
    addResult('package.json', false, 'File not found')
    return
  }
  
  try {
    const packageContent = JSON.parse(readFileSync(packagePath, 'utf8'))
    
    // Check required dependencies
    const requiredDeps = [
      'vitest',
      '@vitest/coverage-v8',
      'jsdom',
      'canvas',
      'fake-indexeddb'
    ]
    
    const missing = requiredDeps.filter(dep => 
      !packageContent.devDependencies?.[dep] && !packageContent.dependencies?.[dep]
    )
    
    if (missing.length === 0) {
      addResult('Required Dependencies', true, 'All test dependencies present')
    } else {
      addResult('Required Dependencies', false, `Missing: ${missing.join(', ')}`)
    }
    
    // Check test scripts
    const requiredScripts = [
      'test',
      'test:coverage',
      'test:integration',
      'test:ci'
    ]
    
    const missingScripts = requiredScripts.filter(script => 
      !packageContent.scripts?.[script]
    )
    
    if (missingScripts.length === 0) {
      addResult('Test Scripts', true, 'All required test scripts present')
    } else {
      addResult('Test Scripts', false, `Missing: ${missingScripts.join(', ')}`)
    }
    
  } catch (error) {
    addResult('package.json', false, `Parse error: ${error.message}`)
  }
}

async function validateVitestConfig() {
  const configPath = join(projectRoot, 'vitest.config.ts')
  
  if (!existsSync(configPath)) {
    addResult('Vitest Config', false, 'vitest.config.ts not found')
    return
  }
  
  try {
    const configContent = readFileSync(configPath, 'utf8')
    
    // Check for required configuration
    const requiredConfig = [
      'environment: \'jsdom\'',
      'setupFiles',
      'coverage',
      'threshold'
    ]
    
    const missing = requiredConfig.filter(config => 
      !configContent.includes(config)
    )
    
    if (missing.length === 0) {
      addResult('Vitest Config', true, 'Configuration appears complete')
    } else {
      addWarning('Vitest Config', `Potentially missing: ${missing.join(', ')}`)
    }
    
  } catch (error) {
    addResult('Vitest Config', false, `Read error: ${error.message}`)
  }
}

async function validateTestSetup() {
  const setupPath = join(projectRoot, 'src/test/setup.ts')
  
  if (!existsSync(setupPath)) {
    addResult('Test Setup', false, 'src/test/setup.ts not found')
    return
  }
  
  try {
    const setupContent = readFileSync(setupPath, 'utf8')
    
    // Check for required setup components
    const requiredSetup = [
      'setupTestEnvironment',
      'WebGL',
      'IndexedDB',
      'beforeAll',
      'afterEach'
    ]
    
    const missing = requiredSetup.filter(setup => 
      !setupContent.includes(setup)
    )
    
    if (missing.length === 0) {
      addResult('Test Setup', true, 'Setup file appears complete')
    } else {
      addWarning('Test Setup', `Potentially missing: ${missing.join(', ')}`)
    }
    
  } catch (error) {
    addResult('Test Setup', false, `Read error: ${error.message}`)
  }
}

async function validateTestDirectories() {
  const requiredDirs = [
    'src/test',
    'test-results',
    'coverage'
  ]
  
  let allExist = true
  const missing = []
  
  for (const dir of requiredDirs) {
    const dirPath = join(projectRoot, dir)
    if (!existsSync(dirPath)) {
      allExist = false
      missing.push(dir)
    }
  }
  
  if (allExist) {
    addResult('Test Directories', true, 'All required directories exist')
  } else {
    addResult('Test Directories', false, `Missing: ${missing.join(', ')}`)
  }
}

async function validateNpmInstall() {
  const result = await executeCommand('npm', ['list', '--depth=0'])
  
  if (result.code === 0) {
    addResult('NPM Dependencies', true, 'All dependencies installed')
  } else {
    addResult('NPM Dependencies', false, 'Some dependencies missing or broken')
  }
}

async function validateVitestExecution() {
  const result = await executeCommand('npx', ['vitest', '--version'])
  
  if (result.code === 0) {
    const version = result.stdout.trim()
    addResult('Vitest Execution', true, `Version ${version}`)
  } else {
    addResult('Vitest Execution', false, 'Cannot execute vitest')
  }
}

async function validateCanvasPackage() {
  try {
    const result = await executeCommand('node', ['-e', 'require("canvas"); console.log("OK")'])
    
    if (result.code === 0) {
      addResult('Canvas Package', true, 'Canvas package working')
    } else {
      addResult('Canvas Package', false, 'Canvas package not working')
    }
  } catch (error) {
    addResult('Canvas Package', false, `Error: ${error.message}`)
  }
}

// Main validation function
async function main() {
  log('Starting test environment validation...', 'info')
  log(`Project root: ${projectRoot}`, 'info')
  log(`Node version: ${process.version}`, 'info')
  log(`Platform: ${process.platform}`, 'info')
  
  console.log('\n' + '='.repeat(50))
  
  await validateNodeVersion()
  await validatePackageJson()
  await validateVitestConfig()
  await validateTestSetup()
  await validateTestDirectories()
  await validateNpmInstall()
  await validateVitestExecution()
  await validateCanvasPackage()
  
  console.log('\n' + '='.repeat(50))
  
  // Summary
  log(`\nValidation Summary:`, 'info')
  log(`✅ Passed: ${results.passed.length}`, 'success')
  log(`❌ Failed: ${results.failed.length}`, 'error')
  log(`⚠️  Warnings: ${results.warnings.length}`, 'warning')
  
  if (results.failed.length > 0) {
    console.log('\nFailed Tests:')
    results.failed.forEach(result => {
      log(`  ${result.test}: ${result.message}`, 'error')
    })
  }
  
  if (results.warnings.length > 0) {
    console.log('\nWarnings:')
    results.warnings.forEach(result => {
      log(`  ${result.test}: ${result.message}`, 'warning')
    })
  }
  
  if (results.failed.length === 0) {
    log('\n🎉 Test environment validation passed!', 'success')
    process.exit(0)
  } else {
    log('\n💥 Test environment validation failed!', 'error')
    log('Please fix the failed tests before running the test suite.', 'error')
    process.exit(1)
  }
}

main().catch((error) => {
  log(`Validation error: ${error.message}`, 'error')
  process.exit(1)
})