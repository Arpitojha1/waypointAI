import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import { Canvas, useThree } from '@react-three/fiber';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight } from 'lucide-react';
import ServerStackModel from './ServerStackModel';
import type { ServerStackHandle } from './ServerStackModel';
import './RackAssemblyScroll.css';

gsap.registerPlugin(ScrollTrigger);

// Guarantees exact camera positioning and lookAt(0,0,0) per Checkpoint 1
const CameraSetup: React.FC = () => {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(2.4, 0.8, 2.7);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
  }, [camera]);
  return null;
};

export const RackAssemblyScroll: React.FC = () => {
  const navigate = useNavigate();
  const sectionRef = useRef<HTMLElement | null>(null);
  const modelRef = useRef<ServerStackHandle | null>(null);
  const [modelReady, setModelReady] = useState(false);

  // 2D Card and CTA refs
  const card1Ref = useRef<HTMLDivElement | null>(null);
  const card2Ref = useRef<HTMLDivElement | null>(null);
  const card3Ref = useRef<HTMLDivElement | null>(null);
  const ctaRef = useRef<HTMLDivElement | null>(null);

  const handleModelReady = useCallback(() => {
    setModelReady(true);
  }, []);

  useEffect(() => {
    if (!modelReady) return;
    const section = sectionRef.current;
    if (!section) return;

    let ctx = gsap.context(() => {
      const bottom = modelRef.current?.bottom;
      const middle = modelRef.current?.middle;
      const top = modelRef.current?.top;
      const bezels = modelRef.current?.bezels;

      if (!bottom || !middle || !top || !bezels) {
        return;
      }

      // --- 1. Initial Scatter Positions (t = 0.00) per Checkpoint 1 & 2 ---
      gsap.set(bottom.position, { x: -0.20, y: -0.45, z: 0.00 });
      gsap.set(middle.position, { x: 0.25, y: 0.00, z: -0.20 });
      gsap.set(top.position, { x: -0.15, y: 0.45, z: 0.00 });
      gsap.set(bezels.position, { x: 0.00, y: 0.10, z: 0.30 });

      // Initialize bezel materials to transparent & opacity 0
      bezels.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach((m) => { m.transparent = true; m.opacity = 0; });
          } else if (mesh.material) {
            mesh.material.transparent = true;
            mesh.material.opacity = 0;
          }
        }
      });

      // Initial 2D Card & CTA states
      if (card1Ref.current) gsap.set(card1Ref.current, { opacity: 1, borderColor: 'var(--color-job-blue)' });
      if (card2Ref.current) gsap.set(card2Ref.current, { opacity: 0.35, borderColor: 'var(--color-olive-stone)' });
      if (card3Ref.current) gsap.set(card3Ref.current, { opacity: 0.35, borderColor: 'var(--color-olive-stone)' });
      if (ctaRef.current) gsap.set(ctaRef.current, { opacity: 0, y: 20, pointerEvents: 'none' });

      // --- 2. ScrollTrigger Timeline per Checkpoint 2 ---
      const tl = gsap.timeline({ paused: true });

      // Phase 1 (t = 0.00 -> 0.24): Bottom Unit Docks
      tl.to(bottom.position, { x: 0, y: 0, z: 0, ease: 'power2.out', duration: 0.24 }, 0.00);

      // Phase 2 (t = 0.24 -> 0.48): Middle Unit Docks & Card 2 reveals
      tl.to(middle.position, { x: 0, y: 0, z: 0, ease: 'power2.out', duration: 0.24 }, 0.24);
      if (card1Ref.current) tl.to(card1Ref.current, { opacity: 0.35, borderColor: 'var(--color-olive-stone)', duration: 0.05 }, 0.24);
      if (card2Ref.current) tl.to(card2Ref.current, { opacity: 1, borderColor: 'var(--color-issue-green)', duration: 0.05 }, 0.24);

      // Phase 3 (t = 0.48 -> 0.70): Top Unit Docks & Card 3 reveals
      tl.to(top.position, { x: 0, y: 0, z: 0, ease: 'power2.out', duration: 0.22 }, 0.48);
      if (card2Ref.current) tl.to(card2Ref.current, { opacity: 0.35, borderColor: 'var(--color-olive-stone)', duration: 0.05 }, 0.48);
      if (card3Ref.current) tl.to(card3Ref.current, { opacity: 1, borderColor: 'var(--color-hackathon-orange)', duration: 0.05 }, 0.48);

      // Phase 4 (t = 0.65 -> 0.78): Bezels Snap & Fade In
      tl.to(bezels.position, { x: 0, y: 0, z: 0, ease: 'power2.out', duration: 0.13 }, 0.65);
      const bezelProxy = { opacity: 0 };
      tl.to(
        bezelProxy,
        {
          opacity: 1,
          duration: 0.13,
          onUpdate: () => {
            bezels.traverse((child) => {
              if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                if (Array.isArray(mesh.material)) {
                  mesh.material.forEach((m) => { m.opacity = bezelProxy.opacity; });
                } else if (mesh.material) {
                  mesh.material.opacity = bezelProxy.opacity;
                }
              }
            });
          },
        },
        0.65
      );

      // Phase 5 (t = 0.75 -> 0.82): CTA Reveal
      if (ctaRef.current) {
        tl.to(ctaRef.current, { opacity: 1, y: 0, pointerEvents: 'auto', ease: 'power2.out', duration: 0.07 }, 0.75);
      }

      // Phase 6 (t = 0.82 -> 1.00): Lock timeline duration exactly to 1.00 per Checkpoint 2
      tl.to({}, { duration: 0.01 }, 1.00);

      ScrollTrigger.create({
        trigger: section,
        pin: true,
        start: 'top top',
        end: () => `+=${section.offsetHeight * 2}`,
        scrub: 1,
        onUpdate: (self) => {
          const progress = self.progress;
          if (progress <= 0.85) {
            tl.progress(progress / 0.85);
          } else {
            tl.progress(1);
          }
        },
      });

      ScrollTrigger.refresh();
    }, section);

    return () => {
      ctx.revert();
    };
  }, [modelReady]);

  const handleCtaClick = () => {
    try {
      navigate('/dashboard');
    } catch {
      window.location.href = '/dashboard';
    }
  };

  return (
    <section ref={sectionRef} className="rack-assembly-section">
      <div className="rack-assembly-sticky">
        {/* Left column: 40% width, plain 2D DOM cards & CTA per Checkpoint 1 & 5 */}
        <div className="rack-assembly-left">
          <div className="rack-assembly-cards">
            {/* Card 1: Profile */}
            <div ref={card1Ref} className="rack-card rack-card-profile">
              <span className="rack-card-badge">PROFILE</span>
              <h3 className="rack-card-title">Deep Skill-Gap Diff</h3>
              <p className="rack-card-desc">
                Analyze your GitHub commits, projects, and resume against real AI market demands to reveal exact technical blind spots.
              </p>
            </div>

            {/* Card 2: Opportunity */}
            <div ref={card2Ref} className="rack-card rack-card-opportunity">
              <span className="rack-card-badge">OPPORTUNITY</span>
              <h3 className="rack-card-title">Verified AI Matched Roles</h3>
              <p className="rack-card-desc">
                Surface live open-source issues, hackathons, and roles tailored to your exact capability tier and verified skill stack.
              </p>
            </div>

            {/* Card 3: Roadmap */}
            <div ref={card3Ref} className="rack-card rack-card-roadmap">
              <span className="rack-card-badge">ROADMAP</span>
              <h3 className="rack-card-title">Adaptive Memory Roadmap</h3>
              <p className="rack-card-desc">
                A dynamic career path that reorders and evolves in real time as you complete projects, ship commits, and gain skills.
              </p>
            </div>

            {/* CTA Button */}
            <div ref={ctaRef} className="rack-cta-container">
              <button type="button" className="btn-rack-cta" onClick={handleCtaClick}>
                <span>Configure My Profile</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Right column: 60% width, holds 3D Canvas per Checkpoint 1 */}
        <div className="rack-assembly-right">
          <Canvas className="rack-assembly-canvas" camera={{ position: [2.4, 0.8, 2.7], fov: 45 }}>
            <CameraSetup />
            {/* Bright, multi-angle lighting for clean metallic rendering without black screen */}
            <ambientLight intensity={1.2} />
            <directionalLight position={[5, 5, 5]} intensity={2.5} />
            <directionalLight position={[-5, 5, 5]} intensity={1.5} />
            <directionalLight position={[0, -5, -5]} intensity={0.8} />

            {/* Recentering offset vector applied to parent group per Checkpoint 1 */}
            <group position={[-0.2919, -0.0483, 0.7034]}>
              <ServerStackModel ref={modelRef} onReady={handleModelReady} />
            </group>
          </Canvas>
        </div>
      </div>
    </section>
  );
};

export default RackAssemblyScroll;
