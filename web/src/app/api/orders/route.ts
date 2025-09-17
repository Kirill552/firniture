import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/v1/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}), // Empty body for now
    });

    if (!response.ok) {
      throw new Error(`Failed to create order: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json({ orderId: data.id });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ message: 'Failed to create order' }, { status: 500 });
  }
}
