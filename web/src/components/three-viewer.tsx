'use client'

import { Suspense } from 'react'
import { Blurhash } from './ui/blurhash'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Html, Center, Grid } from '@react-three/drei'
import { DXFLoader } from 'three-dxf-loader'

interface DxfModelProps {
  url: string
}

function DxfModel({ url }: DxfModelProps) {
  const dxf = useLoader(DXFLoader as any, url)
  return (
    <Center>
        <primitive object={dxf} />
    </Center>
  )
}

export function ThreeViewer({ fileUrl = '/sample.dxf' }: { fileUrl?: string }) {
  return (
    <div className="w-full h-full bg-gray-100 dark:bg-gray-900">
      <Canvas camera={{ position: [0, 100, 200] }}>
        <ambientLight intensity={0.7} />
        <hemisphereLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <Suspense fallback={
          <Html center>
            <div className="w-64 h-64 flex items-center justify-center">
              <Blurhash
                hash="L6PZfSi_.AyE_3t7F_oeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoeNFoe"
                width={256}
                height={256}
                resolutionX={32}
                resolutionY={32}
                punch={1}
                className="rounded-lg"
              />
              <p className="absolute text-sm text-gray-500 dark:text-gray-400">Загрузка модели...</p>
            </div>
          </Html>
        }>
          <DxfModel url={fileUrl} />
        </Suspense>
        <OrbitControls makeDefault minDistance={10} maxDistance={500} />
        <Grid infiniteGrid cellSize={10} cellThickness={1} sectionSize={100} sectionThickness={1.5} fadeDistance={1000} />
      </Canvas>
    </div>
  )
}
