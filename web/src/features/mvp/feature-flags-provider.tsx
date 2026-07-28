'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

interface FeatureFlagsContextType {
  machineFeaturesEnabled: boolean
  factoryFeaturesEnabled: boolean
  isLoading: boolean
}

const FeatureFlagsContext = createContext<FeatureFlagsContextType>({
  machineFeaturesEnabled: false,
  factoryFeaturesEnabled: false,
  isLoading: true,
})
 

export function FeatureFlagsProvider({ children }: { children: React.ReactNode }) {
  const [machineFeaturesEnabled, setMachineFeaturesEnabled] = useState(false)
  const [factoryFeaturesEnabled, setFactoryFeaturesEnabled] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    const fetchFlags = async () => {
      try {
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''
        const res = await fetch(`${API_BASE_URL}/api/v1/features`)
        if (res.ok) {
          const data = await res.json()
          if (active) {
            setMachineFeaturesEnabled(!!data.machine_features_enabled)
            setFactoryFeaturesEnabled(!!data.factory_features_enabled)
          }
        }
      } catch (err) {
        console.error('Failed to load feature flags, falling back to fail-closed defaults', err)
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }
    fetchFlags()
    return () => {
      active = false
    }
  }, [])

  return (
    <FeatureFlagsContext.Provider value={{ machineFeaturesEnabled, factoryFeaturesEnabled, isLoading }}>
      {children}
    </FeatureFlagsContext.Provider>
  )
}

export function useFeatureFlags() {
  return useContext(FeatureFlagsContext)
}
