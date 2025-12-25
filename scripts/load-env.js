#!/usr/bin/env node
/**
 * Environment loader script
 *
 * This script loads the root .env file and prints validation status.
 * Can be used to verify environment before starting services.
 *
 * Usage:
 *   node scripts/load-env.js
 */

const { resolve } = require('path');
const { existsSync, readFileSync } = require('fs');

// Simple .env parser (no external dependency)
function parseEnv(content) {
  const result = {};
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;
    const key = trimmed.substring(0, eqIndex).trim();
    let value = trimmed.substring(eqIndex + 1).trim();
    // Remove quotes if present
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    result[key] = value;
  }
  return result;
}

const rootDir = resolve(__dirname, '..');
const envPath = resolve(rootDir, '.env');

console.log('🔧 Environment Configuration');
console.log('============================');
console.log(`📁 Root directory: ${rootDir}`);
console.log(`📄 .env file: ${envPath}`);

if (!existsSync(envPath)) {
  console.error('❌ ERROR: .env file not found!');
  console.error(`   Please create ${envPath} with your configuration.`);
  console.error(`   You can copy from .env.example as a starting point.`);
  process.exit(1);
}

// Parse .env file
const envContent = readFileSync(envPath, 'utf-8');
const envVars = parseEnv(envContent);

// Set environment variables
for (const [key, value] of Object.entries(envVars)) {
  process.env[key] = value;
}

console.log('✅ .env file loaded successfully\n');

// Check required variables
const required = {
  'Database (Supabase)': [
    'SUPABASE_HOST',
    'SUPABASE_PASSWORD',
  ],
  'Frontend (NEXT_PUBLIC_*)': [
    'NEXT_PUBLIC_API_URL',
    'NEXT_PUBLIC_SUPABASE_URL',
    'NEXT_PUBLIC_SUPABASE_ANON_KEY',
    'NEXT_PUBLIC_VAPI_API_KEY',
    'NEXT_PUBLIC_VAPI_ASSISTANT_ID',
  ],
  'Backend (VAPI)': [
    'VAPI_API_KEY',
    'VAPI_ASSISTANT_ID',
  ],
  'Backend (OpenRouter)': [
    'OPENROUTER_API_KEY',
  ],
};

let allValid = true;

for (const [category, vars] of Object.entries(required)) {
  console.log(`${category}:`);
  for (const v of vars) {
    const value = process.env[v];
    if (value) {
      // Mask sensitive values
      const masked = v.includes('KEY') || v.includes('PASSWORD')
        ? value.substring(0, 8) + '...'
        : value;
      console.log(`  ✅ ${v}: ${masked}`);
    } else {
      console.log(`  ❌ ${v}: NOT SET`);
      allValid = false;
    }
  }
  console.log('');
}

if (allValid) {
  console.log('✅ All required environment variables are set!');
} else {
  console.log('⚠️  Some environment variables are missing. Check above.');
}
