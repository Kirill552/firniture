import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json()

    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 })
    }

    const apiKey = process.env.AI_API_KEY
    const baseUrl = process.env.AI_BASE_URL || 'https://openrouter.ai/api/v1'
    const model = process.env.AI_CHAT_MODEL || 'deepseek/deepseek-chat-v3-0324'

    if (!apiKey) {
      return NextResponse.json({ error: 'AI_API_KEY не настроен' }, { status: 500 })
    }

    const prompt = `Ты - AI-поисковик в системе АвтоРаскрой. Обработай запрос: "${query}". Найди релевантные заказы, фурнитуру или другие элементы. Ответь на русском, в формате JSON: {"results": [{"title": "Название", "description": "Описание", "url": "/path"}]}`

    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        temperature: 0.6,
        max_tokens: 1000,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      }),
    })

    if (!response.ok) {
      throw new Error(`AI API error: ${response.statusText}`)
    }

    const data = await response.json()
    const aiResponse = data.choices?.[0]?.message?.content || 'No results'

    // Парсим JSON из ответа AI
    let results = []
    try {
      const parsed = JSON.parse(aiResponse)
      results = parsed.results || []
    } catch {
      results = [{ title: 'Результат поиска', description: aiResponse, url: '#' }]
    }

    return NextResponse.json({ results })
  } catch (error) {
    console.error('Search error:', error)
    return NextResponse.json({ error: 'Search failed' }, { status: 500 })
  }
}
