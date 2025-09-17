import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json()

    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 })
    }

    const apiKey = process.env.YANDEX_API_KEY
    if (!apiKey) {
      return NextResponse.json({ error: 'Yandex API key not configured' }, { status: 500 })
    }

    const prompt = `Ты - AI-поисковик в системе Мебель-ИИ. Обработай запрос: "${query}". Найди релевантные заказы, фурнитуру или другие элементы. Ответь на русском, в формате JSON: {"results": [{"title": "Название", "description": "Описание", "url": "/path"}]}`

    const response = await fetch('https://llm.api.cloud.yandex.net/foundationModels/v1/completion', {
      method: 'POST',
      headers: {
        'Authorization': `Api-Key ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        modelUri: 'gpt://api.cloud.yandex.net/foundation-models/yandexgpt-lite',
        completionOptions: {
          stream: false,
          temperature: 0.6,
          maxTokens: 1000,
        },
        messages: [
          {
            role: 'user',
            text: prompt,
          },
        ],
      }),
    })

    if (!response.ok) {
      throw new Error(`Yandex API error: ${response.statusText}`)
    }

    const data = await response.json()
    const aiResponse = data.result[0]?.message?.text || 'No results'

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