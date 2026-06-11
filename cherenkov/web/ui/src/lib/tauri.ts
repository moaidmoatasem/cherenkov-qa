/**
 * Bridge to the Tauri desktop shell.
 *
 * The dashboard is served over HTTP by the engine sidecar in both browser and
 * desktop modes, so the shell's IPC is reached through the global injected by
 * `app.withGlobalTauri` rather than a bundled @tauri-apps/api. Every helper
 * no-ops gracefully when running in a plain browser.
 */

export interface HardwareInfo {
  device_class: string;
  os: string;
  arch: string;
  cpu_cores: number;
  has_adb: boolean;
  has_maestro: boolean;
  has_node: boolean;
  has_python: boolean;
  has_ollama: boolean;
}

interface TauriGlobal {
  core: {
    invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
  };
  event: {
    listen: (
      event: string,
      handler: (e: { payload: unknown }) => void,
    ) => Promise<() => void>;
  };
}

function tauri(): TauriGlobal | null {
  return (window as unknown as { __TAURI__?: TauriGlobal }).__TAURI__ ?? null;
}

/** True when the dashboard is hosted inside the CHERENKOV desktop shell. */
export function isDesktop(): boolean {
  return tauri() !== null;
}

/**
 * Invoke a desktop shell command. Returns null in browser mode or when the
 * command fails, so callers can fall back to their HTTP path.
 */
export async function invokeDesktop<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T | null> {
  const t = tauri();
  if (!t) return null;
  try {
    return await t.core.invoke<T>(cmd, args);
  } catch (err) {
    console.warn(`[desktop] invoke ${cmd} failed:`, err);
    return null;
  }
}

/**
 * Subscribe to a desktop shell event (engine-ready, engine-demo-mode, …).
 * Returns an unsubscribe function; a no-op one in browser mode.
 */
export async function listenDesktop(
  event: string,
  handler: (payload: unknown) => void,
): Promise<() => void> {
  const t = tauri();
  if (!t) return () => {};
  return t.event.listen(event, (e) => handler(e.payload));
}
