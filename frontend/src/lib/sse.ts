/** 解析 OpenAI 兼容 SSE（Coze Integration / 本地 /llm/chat/stream） */

export async function consumeSseDeltas(
  response: Response,
  onDelta: (delta: string) => void,
): Promise<void> {
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `HTTP ${response.status}`)
  }
  const reader = response.body?.getReader()
  if (!reader) throw new Error('响应不支持流式读取')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const payload = trimmed.slice(5).trim()
      if (!payload || payload === '[DONE]') continue
      try {
        const data = JSON.parse(payload) as { delta?: string; error?: string }
        if (data.error) throw new Error(data.error)
        if (data.delta) onDelta(data.delta)
      } catch (e) {
        if (e instanceof SyntaxError) continue
        throw e
      }
    }
  }
}
