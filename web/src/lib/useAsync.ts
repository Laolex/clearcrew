import { useEffect, useState } from 'react'

/** Load once. An error is surfaced, never swallowed — a blank panel that might
 *  mean "nothing happened" or might mean "the request failed" is a lie either way. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setData(null)
    setError(null)
    fn()
      .then((d) => live && setData(d))
      .catch((e: Error) => live && setError(e.message))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, error, loading: !data && !error }
}
