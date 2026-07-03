import React, { useState, useEffect, useRef, useCallback } from 'react';

interface ScrambledTextProps {
  text: string;
  className?: string;
  style?: React.CSSProperties;
  chars?: string;
  trigger?: 'hover' | 'always' | boolean;
}

const DEFAULT_CHARS = '!@#$%^&*():;-+=~_[]{}|\\/0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export const ScrambledText: React.FC<ScrambledTextProps> = ({
  text,
  className = '',
  style = {},
  chars = DEFAULT_CHARS,
  trigger = 'hover',
}) => {
  const [displayText, setDisplayText] = useState(text);
  const [isScrambling, setIsScrambling] = useState(false);
  const animationRef = useRef<number | null>(null);
  const frameRef = useRef<number>(0);

  const startScramble = useCallback(() => {
    if (isScrambling && trigger === 'hover') return;
    setIsScrambling(true);

    let iteration = 0;
    const maxIterations = text.length;

    const animate = () => {
      frameRef.current++;
      
      // Update text on every frame or throttled by speed
      setDisplayText(
        text
          .split('')
          .map((char, index) => {
            if (char === ' ') return ' ';
            if (index < iteration) {
              return text[index];
            }
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join('')
      );

      if (iteration >= maxIterations) {
        setIsScrambling(false);
        setDisplayText(text);
        if (animationRef.current) cancelAnimationFrame(animationRef.current);
        return;
      }

      // Progress forward roughly every 2-3 frames
      if (frameRef.current % 2 === 0) {
        iteration += 1 / 2;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    frameRef.current = 0;
    animationRef.current = requestAnimationFrame(animate);
  }, [text, chars, isScrambling, trigger]);

  useEffect(() => {
    if (trigger === 'always' || trigger === true) {
      startScramble();
    }
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [text, trigger]);

  return (
    <span
      className={className}
      style={{ display: 'inline-block', fontVariantNumeric: 'tabular-nums', ...style }}
      onMouseEnter={() => {
        if (trigger === 'hover') startScramble();
      }}
    >
      {displayText}
    </span>
  );
};
