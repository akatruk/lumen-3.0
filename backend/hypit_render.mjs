/**
 * Run Hypit's local HyperFrames capture. Hypit source stays in HYPIT_ROOT.
 * License: Apache 2.0 with Hypit's additional conditions. This process does not
 * surface the Hypit CLI, so the logo clause does not apply.
 */
import { access, readFile } from 'node:fs/promises'
import { constants } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const root = process.env.HYPIT_ROOT
if (!root) {
  console.error('hypit_unavailable')
  process.exit(2)
}

const provider = resolve(root, 'packages/provider-hyperframes-local/src')
await import(pathToFileURL(resolve(provider, 'capture-bootstrap.ts')).href)
const browser = await import(pathToFileURL(resolve(provider, 'browser.ts')).href)
const { captureStagedVisual } = await import(pathToFileURL(resolve(provider, 'capture.ts')).href)
const { resolveExecutionOptions } = await import(pathToFileURL(resolve(provider, 'render.ts')).href)

async function exists(path) {
  try {
    await access(path, constants.X_OK)
    return true
  } catch {
    return false
  }
}

async function chromePath() {
  if (process.env.HYPIT_CHROME) return process.env.HYPIT_CHROME
  const candidates = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ]
  for (const path of candidates) {
    if (await exists(path)) return path
  }
  let managed
  try {
    managed = browser.browserExecutablePath({})
  } catch (error) {
    if (!process.argv.includes('--prepare')) throw error
    managed = undefined
  }
  if (managed && await exists(managed)) return managed
  if (!process.argv.includes('--prepare')) {
    console.error('hypit_unavailable')
    process.exit(2)
  }
  await browser.installRenderBrowser(browser.browserCacheDirectory({}), browser.recommendedBrowserVersion)
  return browser.browserExecutablePath({})
}

if (process.argv.includes('--prepare')) {
  const path = await chromePath()
  process.stdout.write(`${path}\n`)
  process.exit(0)
}

const jobPath = process.argv[2]
if (!jobPath) {
  console.error('hypit_unavailable')
  process.exit(2)
}

const job = JSON.parse(await readFile(jobPath, 'utf8'))
const chrome = await chromePath()
const engineRoot = resolve(root, 'packages/provider-hyperframes-local/node_modules/@hyperframes')
const engineModule = pathToFileURL(resolve(engineRoot, 'engine/dist/index.js')).href
const producerModule = pathToFileURL(resolve(engineRoot, 'producer/dist/index.js')).href
const frameCount = job.frameCount
const controller = new AbortController()
const config = {
  ...resolveExecutionOptions({
    workers: 1,
    maxWorkers: 1,
    quality: 'standard',
    browserGpu: 'software',
    chromePath: chrome,
    ffmpegPath: 'ffmpeg',
    ffprobePath: 'ffprobe',
    maxDecodedSourceBytes: 512 * 1024 * 1024,
  }),
  chromePath: chrome,
}
await captureStagedVisual({
  document: {
    frameRate: { numerator: job.fpsNum, denominator: job.fpsDen },
    frameCount,
    canvas: { width: job.width, height: job.height },
  },
  range: { startFrame: 0, endFrameExclusive: frameCount },
  config,
  directory: job.directory,
  engineModule,
  producerModule,
}, controller, () => {})
