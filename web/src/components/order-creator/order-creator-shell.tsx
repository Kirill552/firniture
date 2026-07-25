'use client'

import React from 'react'

interface OrderCreatorShellProps {
  mode: string
  children: React.ReactNode
  chatPanel?: React.ReactNode
}

export function OrderCreatorShell({ mode, children, chatPanel }: OrderCreatorShellProps) {
  const isClarify = mode === 'clarify'

  return (
    <div className="min-h-[100dvh] bg-[#f3f6f8] text-[#171a1d] py-8 md:py-12 px-4 transition-all duration-300">
      {/* Outer flex container to center the active composition */}
      <div className="w-full flex justify-center">
        <div 
          className={`w-full transition-all duration-300 ${
            isClarify 
              ? 'max-w-[1120px] grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6' 
              : 'max-w-[720px]'
          }`}
        >
          {/* Left Column: Headings, params review cards, manual forms */}
          <div className="w-full max-w-[720px] mx-auto flex flex-col">
            {children}
          </div>

          {/* Right Column: AI Chat Panel (desktop inline, mobile below content) */}
          {isClarify && chatPanel && (
            <div className="w-full lg:w-[360px] flex flex-col">
              {chatPanel}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
