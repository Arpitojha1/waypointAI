import * as THREE from 'three'
import { forwardRef, useImperativeHandle, useRef, useEffect } from 'react'
import type { JSX } from 'react'
import { useGLTF } from '@react-three/drei'
import type { GLTF } from 'three-stdlib'
import serverStackGlb from '../../assets/server-stack.glb'

// Raw node graph from the .glb — every named Blender object/group is present here,
// not just meshes. gltfjsx's auto-typing only surfaces mesh nodes, so this type
// is hand-extended to include the 4 group nodes we actually animate.
type ServerStackGLTF = GLTF & {
  nodes: {
    ServerStack_Root: THREE.Group
    Group_Bezels: THREE.Group
    Group_Unit_Bottom: THREE.Group
    Group_Unit_Middle: THREE.Group
    Group_Unit_Top: THREE.Group
  }
  materials: {
    ['Material.008']: THREE.MeshStandardMaterial // bezels
  }
}

export type ServerStackHandle = {
  bezels: THREE.Group | null
  bottom: THREE.Group | null
  middle: THREE.Group | null
  top: THREE.Group | null
}

export type ServerStackModelProps = JSX.IntrinsicElements['group'] & {
  onReady?: () => void
}

/**
 * Loads server-stack.glb and exposes the 4 top-level groups (bezels, bottom
 * unit, middle unit, top unit) as refs so a parent scroll-driver can animate
 * each piece independently. Materials/geometry stay attached exactly as
 * exported — nothing is flattened or re-parented here.
 */
const ServerStackModel = forwardRef<ServerStackHandle, ServerStackModelProps>(
  function ServerStackModel(props, ref) {
    const { nodes, materials } = useGLTF(serverStackGlb) as unknown as ServerStackGLTF
    const { onReady, ...groupProps } = props

    const bezelsRef = useRef<THREE.Group>(null)
    const bottomRef = useRef<THREE.Group>(null)
    const middleRef = useRef<THREE.Group>(null)
    const topRef = useRef<THREE.Group>(null)

    // Bezels fade in via opacity — give them their own material instance so
    // toggling opacity never touches anything else (Material.008 is only
    // used by the 4 bezel meshes in this file, but clone defensively).
    const bezelMaterial = useRef<THREE.MeshStandardMaterial>(undefined)
    if (!bezelMaterial.current && materials['Material.008']) {
      bezelMaterial.current = materials['Material.008'].clone()
      bezelMaterial.current.transparent = true
    }

    useImperativeHandle(ref, () => ({
      get bezels() { return bezelsRef.current },
      get bottom() { return bottomRef.current },
      get middle() { return middleRef.current },
      get top() { return topRef.current },
    }))

    useEffect(() => {
      if (onReady && bezelsRef.current && bottomRef.current && middleRef.current && topRef.current) {
        onReady()
      }
    }, [onReady])

    return (
      <group {...groupProps} dispose={null}>
        {nodes.Group_Bezels && <primitive ref={bezelsRef} object={nodes.Group_Bezels} />}
        {nodes.Group_Unit_Bottom && <primitive ref={bottomRef} object={nodes.Group_Unit_Bottom} />}
        {nodes.Group_Unit_Middle && <primitive ref={middleRef} object={nodes.Group_Unit_Middle} />}
        {nodes.Group_Unit_Top && <primitive ref={topRef} object={nodes.Group_Unit_Top} />}
      </group>
    )
  }
)

export default ServerStackModel
useGLTF.preload(serverStackGlb)
