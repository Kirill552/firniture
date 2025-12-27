'use client'

import { Suspense, useRef, useState, useEffect, useCallback } from 'react'
import { Blurhash } from './ui/blurhash'
import { Canvas, useLoader, useFrame, ThreeEvent } from '@react-three/fiber'
import { OrbitControls, Html, Center, Grid } from '@react-three/drei'
import * as THREE from 'three'
import { DXFLoader } from 'three-dxf-loader'

interface DxfModelProps {
  url: string
}

function DxfModel({ url }: DxfModelProps) {
  const dxf = useLoader(DXFLoader as any, url)
  const groupRef = useRef<THREE.Group>(null)
  const [hovered, setHovered] = useState<THREE.Object3D | null>(null)
  const idleStart = useRef<number>(Date.now())
  const [autoRotate, setAutoRotate] = useState(true)

  const onPointerOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    setHovered(e.object)
    setAutoRotate(false)
  }
  const onPointerOut = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    setHovered(null)
    idleStart.current = Date.now()
  }

  useFrame((_, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.25
    }
    // Включаем авто-ротацию спустя 3s бездействия
    if (!autoRotate && Date.now() - idleStart.current > 3000) {
      setAutoRotate(true)
    }
    if (hovered) {
      // Пульсация подсвеченного объекта
      const s = 1 + Math.sin(Date.now() * 0.006) * 0.05
      hovered.scale.setScalar(s)
    }
  })

  // Сброс масштаба когда hover снят
  useEffect(() => {
    if (!hovered) return
    return () => { hovered.scale.setScalar(1) }
  }, [hovered])

  // Простая обводка: добавляем emissive для материалов MeshStandardMaterial
  const highlight = useCallback((obj: THREE.Object3D | null, on: boolean) => {
    if (!obj) return
    obj.traverse(child => {
      const mat = (child as any).material as THREE.Material | undefined
      if (mat && 'emissive' in (mat as any)) {
        (mat as any).emissive = on ? new THREE.Color('#ffbf40') : new THREE.Color('#000')
        ;(mat as any).emissiveIntensity = on ? 0.6 : 0
      }
    })
  }, [])

  useEffect(() => {
    highlight(hovered, true)
    return () => highlight(hovered, false)
  }, [hovered, highlight])

  return (
    <Center>
      <group
        ref={groupRef}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
        onPointerMove={() => { /* удерживаем авто-ротацию выключенной пока двигается */ setAutoRotate(false); idleStart.current = Date.now() }}
      >
        <primitive object={dxf} />
      </group>
    </Center>
  )
}

export function ThreeViewer({ fileUrl = '/sample.dxf' }: { fileUrl?: string }) {
  return (
    <div className="w-full h-full bg-gray-100 dark:bg-gray-900 select-none">
      <Canvas camera={{ position: [0, 100, 200], fov: 55 }}>
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
        <OrbitControls makeDefault minDistance={10} maxDistance={500} enableDamping dampingFactor={0.08} rotateSpeed={0.6} />
        <Grid infiniteGrid cellSize={10} cellThickness={1} sectionSize={100} sectionThickness={1.5} fadeDistance={1000} />
      </Canvas>
    </div>
  )
}
