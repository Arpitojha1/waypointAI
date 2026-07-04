import React, { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
  ArrowRight,
  GitCommit,
} from 'lucide-react';
import { Footer } from '../components/Footer';
import RackAssemblyScroll from '../components/landing/RackAssemblyScroll';
import './LandingPage.css';

gsap.registerPlugin(ScrollTrigger);

export interface LandingPageProps {
  onGetStarted?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onGetStarted }) => {
  const navigate = useNavigate();

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

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
      </section>

      {/* Section 2: Rack Assembly Scroll */}
      <RackAssemblyScroll />

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
