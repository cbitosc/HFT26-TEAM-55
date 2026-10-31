import React, { useEffect, useRef } from 'react';

export const GeometricBackground: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rafIdRef = useRef<number | null>(null);

  useEffect(() => {
    // Check for user's reduced-motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mediaQuery.matches) {
      return;
    }

    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      // Normalize mouse to [-1, 1] relative to viewport center
      targetX = (e.clientX / window.innerWidth) * 2 - 1;
      targetY = (e.clientY / window.innerHeight) * 2 - 1;
    };

    const updateParallax = () => {
      // Smooth lerp (linear interpolation) for cinematic lag
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;

      if (containerRef.current) {
        containerRef.current.style.setProperty('--mouse-x', currentX.toFixed(4));
        containerRef.current.style.setProperty('--mouse-y', currentY.toFixed(4));
      }

      rafIdRef.current = requestAnimationFrame(updateParallax);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    rafIdRef.current = requestAnimationFrame(updateParallax);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  return (
    <div ref={containerRef} className="geometric-bg-container" aria-hidden="true">
      {/* 1. Deep Midnight Navy Base Canvas with Layered Radial Gradients */}
      <div className="bg-canvas-gradient" />

      {/* 2. Rich Ambient Lighting Orbs (Cyan, Violet, Royal Blue) */}
      <div className="ambient-glow glow-blue-left" />
      <div className="ambient-glow glow-violet-right" />
      <div className="ambient-glow glow-cyan-bottom" />
      <div className="ambient-glow glow-core-center" />

      {/* 3. 3D Perspective Cyber-Grid Horizon */}
      <div className="perspective-grid-floor" />
      <div className="bg-architectural-grid" />
      <div className="bg-vignette-overlay" />

      {/* 4. Floating 3D Geometric Objects with Parallax Tiers */}

      {/* Tier 1: Deep Background (Subtle negative parallax) */}
      <div className="parallax-tier tier-deep">
        {/* Isometric Faceted Polyhedron */}
        <svg className="geo-shape geo-iso-triangle" viewBox="0 0 200 200">
          <defs>
            <linearGradient id="facetLeftGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#1e3a8a" stopOpacity="0.05" />
            </linearGradient>
            <linearGradient id="facetRightGrad" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#172554" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <polygon points="100,20 20,160 100,135" fill="url(#facetLeftGrad)" stroke="#3b82f6" strokeWidth="1.2" />
          <polygon points="100,20 180,160 100,135" fill="url(#facetRightGrad)" stroke="#60a5fa" strokeWidth="1.2" />
          <polygon points="20,160 180,160 100,135" fill="rgba(15, 23, 42, 0.5)" stroke="#2563eb" strokeWidth="1" />
        </svg>

        {/* Floating Diamond Octahedron Wireframe */}
        <svg className="geo-shape geo-octahedron" viewBox="0 0 160 160">
          <polygon points="80,15 145,80 80,145 15,80" fill="rgba(139, 92, 246, 0.06)" stroke="#a78bfa" strokeWidth="1.2" />
          <line x1="15" y1="80" x2="145" y2="80" stroke="#a78bfa" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
          <line x1="80" y1="15" x2="80" y2="145" stroke="#a78bfa" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
          <circle cx="80" cy="15" r="3" fill="#c4b5fd" />
          <circle cx="145" cy="80" r="3" fill="#c4b5fd" />
          <circle cx="80" cy="145" r="3" fill="#c4b5fd" />
          <circle cx="15" cy="80" r="3" fill="#c4b5fd" />
        </svg>
      </div>

      {/* Tier 2: Midground (Real CSS 3D Rotating Cube & Faceted Shapes) */}
      <div className="parallax-tier tier-mid">
        {/* Real CSS 3D Rotating Cube / Tesseract in Cyan */}
        <div className="cube-3d-wrapper">
          <div className="cube-3d">
            <div className="cube-3d-face cube-front" />
            <div className="cube-3d-face cube-back" />
            <div className="cube-3d-face cube-right" />
            <div className="cube-3d-face cube-left" />
            <div className="cube-3d-face cube-top" />
            <div className="cube-3d-face cube-bottom" />
          </div>
        </div>

        {/* 3D Wireframe Tetrahedron in Cyan */}
        <svg className="geo-shape geo-tetrahedron-cyan" viewBox="0 0 220 220">
          <defs>
            <linearGradient id="tetraGradCyan" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#0891b2" stopOpacity="0.06" />
            </linearGradient>
          </defs>
          <polygon points="110,25 200,175 20,175" fill="url(#tetraGradCyan)" stroke="#22d3ee" strokeWidth="1.4" />
          <line x1="110" y1="25" x2="110" y2="125" stroke="#38bdf8" strokeWidth="1.4" />
          <line x1="20" y1="175" x2="110" y2="125" stroke="#38bdf8" strokeWidth="1.4" />
          <line x1="200" y1="175" x2="110" y2="125" stroke="#38bdf8" strokeWidth="1.4" />
          <circle cx="110" cy="125" r="3.5" fill="#22d3ee" />
          <circle cx="110" cy="25" r="2.5" fill="#38bdf8" />
          <circle cx="20" cy="175" r="2.5" fill="#38bdf8" />
          <circle cx="200" cy="175" r="2.5" fill="#38bdf8" />
        </svg>

        {/* 3D Faceted Hexagonal Prism in Violet */}
        <svg className="geo-shape geo-prism-violet" viewBox="0 0 240 240">
          <defs>
            <linearGradient id="prismVioletGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#c084fc" stopOpacity="0.38" />
              <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.08" />
            </linearGradient>
          </defs>
          <polygon points="120,20 205,70 205,170 120,220 35,170 35,70" fill="url(#prismVioletGrad)" stroke="#a855f7" strokeWidth="1.4" />
          <polygon points="120,60 170,90 170,150 120,180 70,150 70,90" fill="rgba(168, 85, 247, 0.1)" stroke="#c084fc" strokeWidth="1.2" />
          <line x1="120" y1="20" x2="120" y2="60" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="205" y1="70" x2="170" y2="90" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="205" y1="170" x2="170" y2="150" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="120" y1="220" x2="120" y2="180" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="35" y1="170" x2="70" y2="150" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="35" y1="70" x2="70" y2="90" stroke="#a855f7" strokeWidth="1.2" strokeDasharray="2 2" />
        </svg>
      </div>

      {/* Tier 3: Foreground (Micro-Crystals & Light Shards) */}
      <div className="parallax-tier tier-foreground">
        {/* Floating Faceted Shard */}
        <svg className="geo-shape geo-shard-tri" viewBox="0 0 140 140">
          <polygon points="70,15 125,115 15,90" fill="rgba(34, 211, 238, 0.12)" stroke="#22d3ee" strokeWidth="1.4" />
          <line x1="70" y1="15" x2="70" y2="70" stroke="#38bdf8" strokeWidth="1.2" strokeDasharray="3 3" />
          <circle cx="70" cy="15" r="2.5" fill="#67e8f9" />
        </svg>

        {/* Micro 3D Triangle Shard */}
        <svg className="geo-shape geo-micro-poly" viewBox="0 0 90 90">
          <polygon points="45,10 80,75 10,75" fill="rgba(192, 132, 252, 0.16)" stroke="#c084fc" strokeWidth="1.2" />
          <line x1="45" y1="10" x2="45" y2="52" stroke="#a855f7" strokeWidth="1" />
        </svg>
      </div>
    </div>
  );
};
