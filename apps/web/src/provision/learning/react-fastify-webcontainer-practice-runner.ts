import type { FileSystemTree, WebContainer, WebContainerProcess } from '@webcontainer/api'

import { AppError } from '@/core/errors/app-error'
import type {
  ReactFastifyPracticeEvent,
  ReactFastifyPracticeHttpRequest,
  ReactFastifyPracticeHttpResponse,
  ReactFastifyPracticeProject,
  ReactFastifyPracticeRunner,
  ReactFastifyPracticeStatus,
} from '@/core/learning/react-fastify-practice-runner'
import type { ReactPracticeFile } from '@/core/learning/react-practice-runner'

const MAX_SOURCE_BYTES = 256 * 1024
const MAX_TERMINAL_BYTES = 1024 * 1024
const INSTALL_TIMEOUT_MS = 180_000
const START_TIMEOUT_MS = 30_000
const HTTP_TIMEOUT_MS = 10_000
const RESERVED_FILES =
  /^(?:package(?:-lock)?\.json|(?:pnpm|yarn|bun).*lock.*|(?:vite|tsconfig|jsconfig|webpack|eslint|postcss|tailwind)\..*|index\.html|node_modules)$/i
const METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
const HTTP_CLIENT_SOURCE = `
import { request as requestHttp } from 'node:http';
const request = JSON.parse(Buffer.from(process.argv[1], 'base64').toString('utf8'));
const result = await new Promise((resolve, reject) => {
  const headers = { connection: 'close' };
  if (request.body !== undefined) {
    headers['content-type'] = 'application/json';
    headers['content-length'] = Buffer.byteLength(request.body, 'utf8');
  }
  const client = requestHttp({
    hostname: '127.0.0.1', port: 3000, path: request.path,
    method: request.method, headers, agent: false
  }, response => {
    const chunks = []; let size = 0; let settled = false;
    function finish(truncated) {
      if (settled) return;
      settled = true;
      clearTimeout(deadline);
      const contentType = response.headers['content-type'];
      resolve({ status: response.statusCode,
        headers: typeof contentType === 'string' ? [{name: 'Content-Type', value: contentType}] : [],
        body: Buffer.concat(chunks, size).toString('utf8'), truncated });
    }
    response.on('data', chunk => {
      const available = 1048576 - size;
      chunks.push(chunk.subarray(0, available));
      size += Math.min(chunk.length, available);
      if (chunk.length > available) { finish(true); response.destroy(); client.destroy(); }
    });
    response.on('end', () => finish(false));
    response.on('error', error => { clearTimeout(deadline); reject(error); });
  });
  const deadline = setTimeout(() => { client.destroy(); reject('timeout'); }, 10000);
  client.on('error', error => { clearTimeout(deadline); reject(error); });
  client.end(request.body);
});
console.log(JSON.stringify(result));
`

export const ReactFastifyWebContainerPracticeRunner = (): ReactFastifyPracticeRunner => {
  const listeners = new Set<(event: ReactFastifyPracticeEvent) => void>()
  const files = new Map<string, string>()
  const processes = new Map<number, WebContainerProcess>()
  const cleanups = new Set<() => void>()
  const requests = new Set<() => void>()
  const updateTimers = new Map<number, ReturnType<typeof setTimeout>>()
  let project: ReactFastifyPracticeProject | null = null
  let container: WebContainer | null = null
  let generation = 0
  let previewRevision = 0
  let disposed = false
  let bootPromise: Promise<void> = Promise.resolve()
  let queue: Promise<void> = Promise.resolve()
  let event: ReactFastifyPracticeEvent = {
    frontendStatus: 'idle',
    apiStatus: 'idle',
    previewUrl: null,
    terminalText: '',
  }

  function emit(update: Partial<ReactFastifyPracticeEvent> = {}) {
    if (disposed) return
    event = { ...event, ...update }
    for (const listener of listeners) listener({ ...event })
  }

  function appendTerminal(text: string) {
    const bytes = new TextEncoder().encode(event.terminalText + text)
    emit({ terminalText: new TextDecoder().decode(bytes.slice(-MAX_TERMINAL_BYTES)) })
  }

  function setStatus(port: number, status: ReactFastifyPracticeStatus) {
    const previousTimer = updateTimers.get(port)
    if (previousTimer) clearTimeout(previousTimer)
    updateTimers.delete(port)
    if (status === 'updating') {
      updateTimers.set(
        port,
        setTimeout(() => {
          updateTimers.delete(port)
          setStatus(port, 'error')
          appendTerminal('\nO servidor não atualizou em 30 segundos. Tente reiniciar.\n')
        }, START_TIMEOUT_MS),
      )
    }
    emit(port === 5173 ? { frontendStatus: status } : { apiStatus: status })
  }

  function isCurrent(current: number) {
    return !disposed && current === generation
  }

  function validatePath(path: string) {
    if (
      path.length > 240 ||
      path
        .split('/')
        .some(
          (segment) =>
            !/^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,63}$/.test(segment) ||
            (RESERVED_FILES.test(segment) && path !== 'index.html'),
        )
    ) {
      throw new AppError('Caminho de prática inválido.')
    }
  }

  function validateFiles(nextFiles: Map<string, string>) {
    let size = 0
    for (const [path, content] of nextFiles) {
      validatePath(path)
      if ([...nextFiles.keys()].some((other) => other.startsWith(`${path}/`))) {
        throw new AppError('Arquivos e diretórios de prática em conflito.')
      }
      size += new TextEncoder().encode(path + content).length
    }
    if (size > MAX_SOURCE_BYTES) throw new AppError('O projeto excede 256 KiB.')
  }

  function validateProject(next: ReactFastifyPracticeProject) {
    const nextFiles = new Map(next.files.map((file) => [file.path, file.content]))
    validateFiles(nextFiles)
    if (
      nextFiles.size !== next.files.length ||
      !nextFiles.has(next.frontendEntrypoint) ||
      !nextFiles.has(next.apiEntrypoint) ||
      next.frontendEntrypoint === next.apiEntrypoint ||
      !['react', 'react-dom', 'vite', 'fastify'].every((name) =>
        next.fixedDependencies.some((dependency) => dependency.name === name),
      )
    ) {
      throw new AppError('Projeto integrado inválido.')
    }
    const names = new Set<string>()
    for (const dependency of next.fixedDependencies) {
      if (
        !/^(?:@[a-z0-9_.-]+\/)?[a-z0-9_.-]+$/.test(dependency.name) ||
        !/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(dependency.version) ||
        names.has(dependency.name)
      ) {
        throw new AppError('Dependência de prática inválida.')
      }
      names.add(dependency.name)
    }
    const ids = new Set<string>()
    for (const command of next.permittedCommands) {
      if (
        ids.has(command.id) ||
        command.executable !== 'npm' ||
        command.arguments.length !== 2 ||
        command.arguments[0] !== 'run' ||
        !['dev:web', 'dev:api'].includes(command.arguments[1] ?? '')
      ) {
        throw new AppError('Comando de prática não autorizado.')
      }
      ids.add(command.id)
    }
    if (
      next.frontendCommandId === next.apiCommandId ||
      !next.permittedCommands.some(
        (command) =>
          command.id === next.frontendCommandId && command.arguments[1] === 'dev:web',
      ) ||
      !next.permittedCommands.some(
        (command) =>
          command.id === next.apiCommandId && command.arguments[1] === 'dev:api',
      )
    ) {
      throw new AppError('Comandos de inicialização inválidos.')
    }
    const policy = next.additionalFilePolicy
    if (
      policy &&
      (!Number.isInteger(policy.maxFiles) || policy.maxFiles < 1 || policy.maxFiles > 32)
    ) {
      throw new AppError('Política de arquivos inválida.')
    }
    return nextFiles
  }

  function toTree(): FileSystemTree {
    if (!project) throw new AppError('Projeto indisponível.')
    const tree: FileSystemTree = Object.create(null)
    for (const [path, content] of files) {
      const segments = path.split('/')
      let branch = tree
      for (const segment of segments.slice(0, -1)) {
        if (!branch[segment]) branch[segment] = { directory: Object.create(null) }
        branch = (branch[segment] as { directory: FileSystemTree }).directory
      }
      branch[segments.at(-1) as string] = { file: { contents: content } }
    }
    tree['package.json'] = {
      file: {
        contents: JSON.stringify({
          private: true,
          type: 'module',
          dependencies: Object.fromEntries(
            project.fixedDependencies.map(({ name, version }) => [name, version]),
          ),
          scripts: {
            'dev:web': 'vite --host 0.0.0.0 --port 5173 --strictPort',
            'dev:api': `node --watch './${project.apiEntrypoint}'`,
          },
        }),
      },
    }
    tree['index.html'] = {
      file: {
        contents: `<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Prática integrada</title></head><body><div id="root"></div><script type="module" src="/${project.frontendEntrypoint}"></script></body></html>`,
      },
    }
    tree['.practice-origin.json'] = { file: { contents: 'null' } }
    tree['vite.config.js'] = {
      file: {
        contents: `
import { readFileSync } from 'node:fs';
export default {
  plugins: [{ name: 'isolated-practice', configureServer(server) {
    server.middlewares.use((request, response, next) => {
      const origin = request.headers.origin;
      let confirmedOrigin = null;
      try { confirmedOrigin = JSON.parse(readFileSync('.practice-origin.json', 'utf8')); } catch {}
      if (confirmedOrigin && origin === confirmedOrigin) {
        response.setHeader('Access-Control-Allow-Origin', origin);
        response.setHeader('Vary', 'Origin');
        if (request.method === 'OPTIONS' && request.url.startsWith('/api')) {
          response.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS');
          response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
          response.statusCode = 204; response.end(); return;
        }
      }
      delete request.headers.cookie; delete request.headers.authorization;
      next();
    });
  }}],
  server: { host: '0.0.0.0', port: 5173, strictPort: true, cors: false,
    proxy: { '/api': { target: 'http://127.0.0.1:3000', followRedirects: false,
      configure(proxy) {
        proxy.on('proxyReq', request => { request.removeHeader('cookie'); request.removeHeader('authorization'); });
        proxy.on('proxyRes', (response, request) => {
          delete response.headers['set-cookie']; delete response.headers['access-control-allow-credentials'];
          delete response.headers['access-control-allow-origin'];
          let confirmedOrigin = null;
          try { confirmedOrigin = JSON.parse(readFileSync('.practice-origin.json', 'utf8')); } catch {}
          const origin = request.headers.origin;
          if (confirmedOrigin && origin === confirmedOrigin) response.headers['access-control-allow-origin'] = origin;
        });
      }
    }}
  }
};
`,
      },
    }
    return tree
  }

  async function streamOutput(process: WebContainerProcess, current: number) {
    const reader = process.output.getReader()
    try {
      while (isCurrent(current)) {
        const { done, value } = await reader.read()
        if (done) break
        if (isCurrent(current)) appendTerminal(value)
      }
    } catch {
      if (isCurrent(current)) appendTerminal('\nSaída de prática interrompida.\n')
    } finally {
      reader.releaseLock()
    }
  }

  function cleanup() {
    for (const timer of updateTimers.values()) clearTimeout(timer)
    updateTimers.clear()
    for (const cancel of requests) cancel()
    requests.clear()
    for (const cancel of cleanups) cancel()
    cleanups.clear()
    for (const process of processes.values()) process.kill()
    processes.clear()
    container?.teardown()
    container = null
  }

  async function launch(port: number, current: number) {
    const deadline = Date.now() + START_TIMEOUT_MS
    const activeContainer = container
    if (!project || !activeContainer || !isCurrent(current)) return
    const commandId = port === 5173 ? project.frontendCommandId : project.apiCommandId
    const command = project.permittedCommands.find(({ id }) => id === commandId)
    if (!command) throw new AppError('Comando não autorizado.')
    const previous = processes.get(port)
    processes.delete(port)
    previous?.kill()
    if (previous) {
      let timer: ReturnType<typeof setTimeout> | undefined
      try {
        await Promise.race([
          previous.exit,
          new Promise<never>((_resolve, reject) => {
            timer = setTimeout(
              () =>
                reject(
                  new AppError('O processo anterior não encerrou. Reinicie a prática.'),
                ),
              2_000,
            )
          }),
        ])
      } catch (error) {
        cleanup()
        emit({ frontendStatus: 'error', apiStatus: 'error', previewUrl: null })
        throw error
      } finally {
        if (timer) clearTimeout(timer)
      }
    }
    if (!isCurrent(current)) return
    setStatus(port, 'starting')
    if (port === 5173) emit({ previewUrl: null })
    // Expand only the two validated generated scripts, without an npm parent shell.
    const args =
      port === 5173
        ? [
            'node_modules/vite/bin/vite.js',
            '--host',
            '0.0.0.0',
            '--port',
            '5173',
            '--strictPort',
          ]
        : ['--watch', `./${project.apiEntrypoint}`]
    const process = await activeContainer.spawn('node', args)
    if (!isCurrent(current)) {
      process.kill()
      return
    }
    processes.set(port, process)
    void streamOutput(process, current)
    const timer = setTimeout(
      () => {
        if (
          isCurrent(current) &&
          processes.get(port) === process &&
          (port === 5173 ? event.frontendStatus : event.apiStatus) !== 'ready'
        ) {
          processes.delete(port)
          process.kill()
          setStatus(port, 'error')
          appendTerminal('\nO servidor não iniciou em 30 segundos. Tente reiniciar.\n')
        }
      },
      Math.max(0, deadline - Date.now()),
    )
    function clearTimer() {
      clearTimeout(timer)
      cleanups.delete(clearTimer)
    }
    cleanups.add(clearTimer)
    void process.exit.then(() => {
      clearTimer()
      if (isCurrent(current) && processes.get(port) === process) {
        processes.delete(port)
        setStatus(port, 'error')
        if (port === 5173) emit({ previewUrl: null })
      }
    })
  }

  async function boot(current: number) {
    if (
      typeof window === 'undefined' ||
      !window.isSecureContext ||
      !window.crossOriginIsolated
    ) {
      emit({ frontendStatus: 'unavailable', apiStatus: 'unavailable' })
      appendTerminal(
        'Prática indisponível neste navegador. Continue editando e avaliando.\n',
      )
      return
    }
    try {
      const { WebContainer: Runtime } = await import('@webcontainer/api')
      if (!isCurrent(current)) return
      const runtime = await Runtime.boot()
      if (!isCurrent(current)) {
        runtime.teardown()
        return
      }
      container = runtime
      await runtime.mount(toTree())
      if (!isCurrent(current)) return
      const install = await runtime.spawn('npm', [
        'install',
        '--ignore-scripts',
        '--no-audit',
        '--no-fund',
      ])
      processes.set(0, install)
      void streamOutput(install, current)
      let timer: ReturnType<typeof setTimeout> | undefined
      const installTimeout = new Promise<number>((resolve) => {
        timer = setTimeout(() => {
          install.kill()
          resolve(1)
        }, INSTALL_TIMEOUT_MS)
      })
      function clearTimer() {
        if (timer) clearTimeout(timer)
        cleanups.delete(clearTimer)
      }
      cleanups.add(clearTimer)
      const exitCode = await Promise.race([install.exit, installTimeout])
      clearTimer()
      processes.delete(0)
      if (!isCurrent(current)) return
      if (exitCode !== 0) throw new AppError('Dependências indisponíveis.')
      cleanups.add(
        runtime.on('server-ready', (port, url) => {
          if (!isCurrent(current) || ![3000, 5173].includes(port)) return
          let parsed: URL
          try {
            parsed = new URL(url)
          } catch {
            setStatus(port, 'unavailable')
            return
          }
          if (
            parsed.protocol !== 'https:' ||
            parsed.origin === window.location.origin ||
            !/\.(?:webcontainer|webcontainer-api)\.io$/.test(parsed.hostname) ||
            parsed.username ||
            parsed.password ||
            parsed.port
          ) {
            setStatus(port, 'unavailable')
            return
          }
          setStatus(port, 'ready')
          if (port === 5173) {
            void runtime.fs
              .writeFile('.practice-origin.json', JSON.stringify(parsed.origin))
              .then(() => {
                if (isCurrent(current)) emit({ previewUrl: parsed.toString() })
              })
              .catch(() => {
                if (isCurrent(current)) setStatus(port, 'error')
              })
          }
        }),
      )
      cleanups.add(
        runtime.on('port', (port, type) => {
          if (isCurrent(current) && type === 'close' && processes.has(port))
            setStatus(port, 'updating')
        }),
      )
      await launch(3000, current)
      await launch(5173, current)
    } catch {
      if (!isCurrent(current)) return
      cleanup()
      emit({ frontendStatus: 'error', apiStatus: 'error', previewUrl: null })
      appendTerminal(
        '\nNão foi possível iniciar a prática. Continue editando e avaliando.\n',
      )
    }
  }

  function enqueue(operation: () => Promise<void>) {
    const result = queue.then(operation, operation).catch((error: unknown) => {
      if (error instanceof AppError) throw error
      throw new AppError('Não foi possível atualizar a prática. Tente reiniciar.')
    })
    queue = result.catch(() => undefined)
    return result
  }

  async function writeFile(file: ReactPracticeFile) {
    await bootPromise
    if (disposed || !container) return
    const current = generation
    const directory = file.path.slice(0, file.path.lastIndexOf('/'))
    if (file.path.includes('/')) await container.fs.mkdir(directory, { recursive: true })
    await container.fs.writeFile(file.path, file.content)
    if (!isCurrent(current)) return
    setStatus(5173, 'updating')
    setStatus(3000, 'updating')
    // Vite and Node's watcher own reloads. Never kill their wrapper on each keystroke.
    const runtime = container
    const probe = await runtime.spawn(
      'node',
      [
        '--input-type=module',
        '-e',
        `
      await new Promise(resolve => setTimeout(resolve, 250));
      const deadline = Date.now() + 29000;
      while (Date.now() < deadline) {
        try {
          await Promise.all([5173, 3000].map(port => fetch('http://127.0.0.1:' + port + '/', {
            signal: AbortSignal.timeout(500), redirect: 'manual', credentials: 'omit'
          }).then(response => response.body?.cancel())));
          process.exit(0);
        } catch { await new Promise(resolve => setTimeout(resolve, 100)); }
      }
      process.exit(1);
    `,
      ],
      { output: false },
    )
    if (!isCurrent(current)) {
      probe.kill()
      return
    }
    const cancel = () => probe.kill()
    cleanups.add(cancel)
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      const exitCode = await Promise.race([
        probe.exit,
        new Promise<number>((resolve) => {
          timer = setTimeout(() => {
            probe.kill()
            resolve(1)
          }, START_TIMEOUT_MS)
        }),
      ])
      if (isCurrent(current)) {
        setStatus(5173, exitCode === 0 ? 'ready' : 'error')
        setStatus(3000, exitCode === 0 ? 'ready' : 'error')
        if (exitCode === 0 && event.previewUrl) {
          // Refresh the isolated preview even when its HMR socket is unavailable.
          const refreshed = new URL(event.previewUrl)
          refreshed.searchParams.set('_practiceRevision', String(++previewRevision))
          emit({ previewUrl: refreshed.toString() })
        }
      }
    } finally {
      if (timer) clearTimeout(timer)
      cleanups.delete(cancel)
    }
  }

  function validateRequest(request: ReactFastifyPracticeHttpRequest) {
    let decoded = request.path
    for (let count = 0; count < 4; count++) {
      const next = decodeURIComponent(decoded)
      if (next === decoded) break
      decoded = next
    }
    if (
      !METHODS.has(request.method) ||
      !/^\/api(?:\/|\?|$)/.test(decoded) ||
      /[\\#]/.test(decoded) ||
      [...decoded].some(
        (character) => character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127,
      ) ||
      /%[0-9a-f]{2}/i.test(decoded) ||
      decoded
        .split('?')[0]
        ?.split('/')
        .some((part) => part === '.' || part === '..') ||
      decoded.startsWith('//') ||
      ((request.method === 'GET' || request.method === 'HEAD') &&
        request.body !== undefined) ||
      new TextEncoder().encode(request.body ?? '').length > 64 * 1024
    ) {
      throw new AppError('Requisição de prática inválida.')
    }
  }

  async function requestHttp(
    request: ReactFastifyPracticeHttpRequest,
    signal?: AbortSignal,
  ): Promise<ReactFastifyPracticeHttpResponse> {
    try {
      validateRequest(request)
    } catch {
      throw new AppError('Requisição de prática inválida.')
    }
    await queue
    if (!container || event.apiStatus !== 'ready' || disposed || signal?.aborted)
      throw new AppError('API de prática indisponível.')
    const runtime = container
    const current = generation
    const pending: { process: WebContainerProcess | null } = { process: null }
    let isCancelled = false
    let rejectCancellation: (error: AppError) => void = () => undefined
    const cancellation = new Promise<never>((_resolve, reject) => {
      rejectCancellation = reject
    })
    function cancel() {
      isCancelled = true
      pending.process?.kill()
      rejectCancellation(
        new AppError('Requisição cancelada ou tempo de espera excedido.'),
      )
    }
    const timer = setTimeout(cancel, HTTP_TIMEOUT_MS)
    requests.add(cancel)
    signal?.addEventListener('abort', cancel, { once: true })
    try {
      const operation = async () => {
        const spawned = await runtime.spawn('node', [
          '--input-type=module',
          '-e',
          HTTP_CLIENT_SOURCE,
          btoa(
            Array.from(new TextEncoder().encode(JSON.stringify(request)), (byte) =>
              String.fromCharCode(byte),
            ).join(''),
          ),
        ])
        pending.process = spawned
        if (isCancelled || !isCurrent(current) || signal?.aborted) {
          spawned.kill()
          throw new AppError('Requisição cancelada.')
        }
        const reader = spawned.output.getReader()
        let output = ''
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            output += value
            if (output.length > 8 * 1024 * 1024) {
              spawned.kill()
              throw new AppError('Resposta de prática inválida.')
            }
          }
        } finally {
          reader.releaseLock()
        }
        if ((await spawned.exit) !== 0)
          throw new AppError('Não foi possível consultar a API.')
        const result: ReactFastifyPracticeHttpResponse = JSON.parse(output)
        if (
          !isCurrent(current) ||
          signal?.aborted ||
          !Number.isInteger(result.status) ||
          result.status < 100 ||
          result.status > 599 ||
          typeof result.body !== 'string' ||
          typeof result.truncated !== 'boolean' ||
          !Array.isArray(result.headers)
        )
          throw new AppError('Resposta de prática inválida.')
        const bodyBytes = new TextEncoder().encode(result.body)
        return {
          status: result.status,
          body: new TextDecoder().decode(bodyBytes.slice(0, 1024 * 1024)),
          truncated: result.truncated || bodyBytes.length > 1024 * 1024,
          headers: result.headers
            .filter(
              (header) =>
                header &&
                typeof header.name === 'string' &&
                header.name.toLowerCase() === 'content-type' &&
                typeof header.value === 'string',
            )
            .map((header) => ({ name: 'Content-Type', value: header.value })),
        }
      }
      return await Promise.race([operation(), cancellation])
    } catch {
      throw new AppError('Não foi possível consultar a API de prática. Tente novamente.')
    } finally {
      clearTimeout(timer)
      requests.delete(cancel)
      signal?.removeEventListener('abort', cancel)
      pending.process?.kill()
    }
  }

  return {
    start(nextProject) {
      return enqueue(async () => {
        if (disposed) return
        cleanup()
        const current = ++generation
        try {
          const nextFiles = validateProject(nextProject)
          project = nextProject
          files.clear()
          for (const [path, content] of nextFiles) files.set(path, content)
          emit({
            frontendStatus: 'starting',
            apiStatus: 'starting',
            previewUrl: null,
            terminalText: 'Iniciando prática React + Fastify…\n',
          })
          bootPromise = boot(current)
          await bootPromise
        } catch {
          emit({
            frontendStatus: 'unavailable',
            apiStatus: 'unavailable',
            previewUrl: null,
          })
        }
      })
    },
    updateFile(path, content) {
      return enqueue(async () => {
        if (path === 'index.html' || !files.has(path) || disposed)
          throw new AppError('Arquivo de prática indisponível.')
        const next = new Map(files).set(path, content)
        validateFiles(next)
        files.set(path, content)
        await writeFile({ path, content })
      })
    },
    addFile(file) {
      return enqueue(async () => {
        const policy = project?.additionalFilePolicy
        const additionalCount = [...files.keys()].filter(
          (path) => !project?.files.some((initial) => initial.path === path),
        ).length
        const extension = file.path.slice(file.path.lastIndexOf('.')).toLowerCase()
        if (
          disposed ||
          file.path === 'index.html' ||
          !policy ||
          files.has(file.path) ||
          additionalCount >= policy.maxFiles ||
          !policy.allowedDirectories.some((directory) =>
            file.path.startsWith(`${directory}/`),
          ) ||
          !policy.allowedExtensions.some((allowed) => allowed.toLowerCase() === extension)
        )
          throw new AppError('Arquivo adicional não autorizado.')
        validateFiles(new Map(files).set(file.path, file.content))
        files.set(file.path, file.content)
        await writeFile(file)
      })
    },
    request: requestHttp,
    runCommand(commandId) {
      return enqueue(async () => {
        await bootPromise
        if (!project?.permittedCommands.some(({ id }) => id === commandId))
          throw new AppError('Comando não autorizado.')
        if (!container && !disposed) {
          const current = ++generation
          emit({ frontendStatus: 'starting', apiStatus: 'starting', previewUrl: null })
          bootPromise = boot(current)
          await bootPromise
          return
        }
        const command = project.permittedCommands.find(({ id }) => id === commandId)
        await launch(command?.arguments[1] === 'dev:web' ? 5173 : 3000, generation)
      })
    },
    restart() {
      return enqueue(async () => {
        if (!project || disposed) return
        cleanup()
        const current = ++generation
        emit({ frontendStatus: 'starting', apiStatus: 'starting', previewUrl: null })
        bootPromise = boot(current)
        await bootPromise
      })
    },
    subscribe(listener) {
      listeners.add(listener)
      listener({ ...event })
      return () => listeners.delete(listener)
    },
    dispose() {
      if (disposed) return
      disposed = true
      generation++
      cleanup()
      listeners.clear()
    },
  }
}
