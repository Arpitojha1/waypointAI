import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
  User,
  Radar,
  Layers,
  Sparkles,
  ArrowRight,
  GitCommit,
} from 'lucide-react';
import { Footer } from '../components/Footer';
import './LandingPage.css';

gsap.registerPlugin(ScrollTrigger);

export interface LandingPageProps {
  onGetStarted?: () => void;
}

interface StopData {
  side: 'left' | 'right';
  color: string;
  Icon: React.FC<{ size?: number; className?: string; style?: React.CSSProperties }>;
  headline: string;
  description: string;
  badgeText: string;
  isMemify?: boolean;
}

const STOPS_DATA: StopData[] = [
  {
    side: 'left',
    color: 'var(--color-cream-glow)',
    Icon: User,
    headline: 'Tell us your skills',
    description: 'Describe your background, skills, and goals — Waypoint uses this to find what actually fits you.',
    badgeText: '01 / profile',
  },
  {
    side: 'right',
    color: 'var(--color-job-blue)',
    Icon: Radar,
    headline: 'We surface real opportunities',
    description: 'Jobs, hackathons, and open-source issues — matched to your skills, not keyword spam.',
    badgeText: '02 / matching',
  },
  {
    side: 'left',
    color: 'var(--color-cream-glow)',
    Icon: Layers,
    headline: 'We build your roadmap',
    description: 'A step-by-step path to get you there — ordered by what matters most for your goal.',
    badgeText: '03 / roadmap',
  },
  {
    side: 'right',
    color: 'var(--color-memify-violet)',
    Icon: Sparkles,
    headline: 'It adapts as you go',
    description: 'Give feedback and Waypoint reorders your roadmap in real time — this step should visually reuse the existing Memify pulse/glow treatment already defined in design.md.',
    badgeText: '04 / cognee memory active',
    isMemify: true,
  },
];

export const LandingPage: React.FC<LandingPageProps> = ({ onGetStarted }) => {
  const navigate = useNavigate();
  const [activeStopIndex, setActiveStopIndex] = useState<number>(0);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const timelineRef = useRef<HTMLDivElement | null>(null);
  const pathRef = useRef<SVGPathElement | null>(null);
  const stopsRef = useRef<(HTMLDivElement | null)[]>([]);
  const nodesRef = useRef<(HTMLDivElement | null)[]>([]);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  const handleGetStarted = useCallback(() => {
    if (onGetStarted) {
      onGetStarted();
    } else {
      try {
        navigate('/dashboard');
      } catch {
        window.location.href = '/dashboard';
      }
    }
  }, [onGetStarted, navigate]);

  // Section 1: Hero Interactive Canvas Grid Distortion
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || window.innerWidth);
    let height = (canvas.height = canvas.parentElement?.clientHeight || window.innerHeight);

    const cellSize = 50;
    let cols = Math.ceil(width / cellSize) + 1;
    let rows = Math.ceil(height / cellSize) + 1;

    interface Point {
      x: number;
      y: number;
      baseX: number;
      baseY: number;
      vx: number;
      vy: number;
    }

    let points: Point[][] = [];
    const initPoints = () => {
      points = [];
      for (let r = 0; r < rows; r++) {
        const row: Point[] = [];
        for (let c = 0; c < cols; c++) {
          const x = c * cellSize;
          const y = r * cellSize;
          row.push({ x, y, baseX: x, baseY: y, vx: 0, vy: 0 });
        }
        points.push(row);
      }
    };
    initPoints();

    let mouseX = -1000;
    let mouseY = -1000;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouseX = -1000;
      mouseY = -1000;
    };

    const handleResize = () => {
      width = canvas.width = canvas.parentElement?.clientWidth || window.innerWidth;
      height = canvas.height = canvas.parentElement?.clientHeight || window.innerHeight;
      cols = Math.ceil(width / cellSize) + 1;
      rows = Math.ceil(height / cellSize) + 1;
      initPoints();
      if (prefersReducedMotion) drawGrid();
    };

    window.addEventListener('resize', handleResize);
    canvas.parentElement?.addEventListener('mousemove', handleMouseMove);
    canvas.parentElement?.addEventListener('mouseleave', handleMouseLeave);

    const drawGrid = () => {
      ctx.clearRect(0, 0, width, height);

      if (!prefersReducedMotion) {
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const p = points[r][c];
            const dx = p.x - mouseX;
            const dy = p.y - mouseY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            let targetX = p.baseX;
            let targetY = p.baseY;

            if (dist < 180 && dist > 0) {
              const force = ((180 - dist) / 180) * 32;
              const angle = Math.atan2(dy, dx);
              targetX = p.baseX + Math.cos(angle) * force;
              targetY = p.baseY + Math.sin(angle) * force;
            }

            const ax = (targetX - p.x) * 0.12;
            const ay = (targetY - p.y) * 0.12;
            p.vx = (p.vx + ax) * 0.78;
            p.vy = (p.vy + ay) * 0.78;
            p.x += p.vx;
            p.y += p.vy;
          }
        }
      }

      ctx.strokeStyle = 'rgba(14, 16, 15, 0.16)';
      ctx.lineWidth = 1;
      ctx.beginPath();

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const p = points[r][c];
          if (c === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
      }

      for (let c = 0; c < cols; c++) {
        for (let r = 0; r < rows; r++) {
          const p = points[r][c];
          if (r === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
      }
      ctx.stroke();

      ctx.fillStyle = 'rgba(14, 16, 15, 0.3)';
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const p = points[r][c];
          ctx.fillRect(p.x - 1, p.y - 1, 2, 2);
        }
      }
    };

    if (prefersReducedMotion) {
      drawGrid();
    } else {
      const renderLoop = () => {
        drawGrid();
        animationFrameId = requestAnimationFrame(renderLoop);
      };
      renderLoop();
    }

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      canvas.parentElement?.removeEventListener('mousemove', handleMouseMove);
      canvas.parentElement?.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  // Section 3: Branch Narrative GSAP ScrollTrigger Animations
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const path = pathRef.current;
    const timeline = timelineRef.current;
    if (!path || !timeline) return;

    if (prefersReducedMotion) {
      path.style.strokeDasharray = 'none';
      path.style.strokeDashoffset = '0';
      return;
    }

    const ctx = gsap.context(() => {
      const length = path.getTotalLength();
      path.style.strokeDasharray = `${length}`;
      path.style.strokeDashoffset = `${length}`;

      gsap.to(path, {
        strokeDashoffset: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: timeline,
          start: 'top 65%',
          end: 'bottom 45%',
          scrub: true,
        },
      });

      STOPS_DATA.forEach((_, index) => {
        const stopEl = stopsRef.current[index];
        const nodeEl = nodesRef.current[index];
        const cardEl = cardsRef.current[index];

        if (!stopEl || !nodeEl || !cardEl) return;

        gsap.fromTo(
          nodeEl,
          { scale: 0, opacity: 0 },
          {
            scale: 1,
            opacity: 1,
            duration: 0.6,
            ease: 'back.out(1.7)',
            scrollTrigger: {
              trigger: stopEl,
              start: 'top 75%',
              toggleActions: 'play none none none',
              onEnter: () => setActiveStopIndex(index),
              onEnterBack: () => setActiveStopIndex(index),
            },
          }
        );

        const headline = cardEl.querySelector('.card-headline');
        const desc = cardEl.querySelector('.card-description');
        const badge = cardEl.querySelector('.card-stop-label');
        const icon = cardEl.querySelector('.card-icon-badge');

        const staggerTargets = [badge, icon, headline, desc].filter(Boolean);

        gsap.fromTo(
          staggerTargets,
          { opacity: 0, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            stagger: 0.1,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: stopEl,
              start: 'top 75%',
              toggleActions: 'play none none none',
            },
          }
        );
      });
    }, timeline);

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <div className="landing-page">
      {/* Section 1: Hero */}
      <section className="landing-hero">
        <canvas ref={canvasRef} className="hero-grid-canvas" />

        <header className="hero-nav">
          <div className="hero-nav-brand" onClick={() => navigate('/')}>
            <div className="hero-nav-logo-icon">W</div>
            <span>Waypoint AI</span>
          </div>
          <div className="hero-nav-actions">
            <button type="button" className="btn-hero-nav" onClick={handleGetStarted}>
              Launch Copilot
            </button>
          </div>
        </header>

        <div className="hero-content">
          <div className="hero-badge">
            <span className="hero-badge-pulse" />
            <span>AI Career Copilot & Adaptive Roadmap Engine</span>
          </div>

          <h1 className="hero-headline">Your AI Career Copilot</h1>
          <p className="hero-subheadline">
            Stop sending 500 applications into the void. Waypoint builds an adaptive roadmap, surfaces matched opportunities, and guides you from where you are to where you want to be.
          </p>

          <button type="button" className="btn-hero-cta" onClick={handleGetStarted}>
            <span>Get Started</span>
            <ArrowRight size={20} className="btn-hero-cta-icon" />
          </button>
        </div>

        {/* Trunk Starting Node bleeding into Section 2 */}
        <div className="trunk-start-node" />
      </section>

      {/* Section 2: Transition */}
      <section className="landing-transition">
        <svg className="transition-seam-svg" viewBox="0 0 1440 70" preserveAspectRatio="none">
          <polygon points="0,70 1440,0 1440,70" className="transition-seam-polygon" />
        </svg>
      </section>

      {/* Section 3: Branch Narrative */}
      <section className="landing-narrative">
        <div className="narrative-header">
          <span className="narrative-eyebrow">How Waypoint Works</span>
          <h2 className="narrative-title">An intelligent branch down your career trajectory</h2>
          <p className="narrative-subtitle">
            From initial skill profiling to dynamic roadmap reordering, your personalized career copilot evolves at every commit.
          </p>
        </div>

        <div className="narrative-timeline-container" ref={timelineRef}>
          <div className="timeline-trunk-wrapper">
            <svg className="timeline-trunk-svg" viewBox="0 0 4 1000" preserveAspectRatio="none">
              <path ref={pathRef} d="M 2 0 L 2 1000" className="trunk-path" />
            </svg>
          </div>

          <div className="timeline-stops">
            {STOPS_DATA.map((stop, index) => {
              const isActive = activeStopIndex === index;
              const isPast = activeStopIndex > index;

              return (
                <div
                  key={index}
                  ref={(el) => {
                    stopsRef.current[index] = el;
                  }}
                  className={`timeline-stop stop-${stop.side}`}
                >
                  <div className="stop-node-wrapper">
                    <div
                      ref={(el) => {
                        nodesRef.current[index] = el;
                      }}
                      className={`commit-node ${activeStopIndex >= index ? 'node-active' : ''} ${stop.isMemify ? 'memify-node' : ''}`}
                      style={{ borderColor: stop.color, color: stop.color }}
                    >
                      <div className="node-inner-dot" />
                    </div>
                  </div>

                  <div className="stop-card-container">
                    <div
                      ref={(el) => {
                        cardsRef.current[index] = el;
                      }}
                      className={`feature-card ${isActive ? 'is-active' : ''} ${isPast ? 'is-past' : ''} ${stop.isMemify ? 'memify-card-pulse' : ''}`}
                      style={{ color: stop.color }}
                    >
                      <div className="card-icon-badge" style={{ borderColor: stop.color, color: stop.color }}>
                        <stop.Icon size={26} />
                      </div>

                      <span className="card-stop-label" style={{ color: stop.color }}>
                        {stop.badgeText}
                      </span>

                      <h3 className="card-headline">{stop.headline}</h3>
                      <p className="card-description">{stop.description}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Section 4: CTA / End State */}
      <section className="landing-end-state">
        <div className="end-state-container">
          <div className="final-flourish-container">
            <div className="flourish-ring flourish-ring-1" />
            <div className="flourish-ring flourish-ring-2" />
            <div className="flourish-center-node">
              <GitCommit size={24} />
            </div>
          </div>

          <div className="end-state-box">
            <h2 className="end-state-title">Ready to Navigate Your AI Career Roadmap?</h2>
            <p className="end-state-subtitle">
              Ready to break out of tutorial hell and application black holes? Launch your personalized career copilot and get matched with what actually fits you.
            </p>

            <button type="button" className="btn-end-cta" onClick={handleGetStarted}>
              <span>Build My Roadmap</span>
              <ArrowRight size={20} />
            </button>
          </div>

          <Footer />
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
