import React, { useEffect, useRef, useState } from 'react';

interface TypewriterTextProps {
  text: string;
  speed?: number; // 打字速度，毫秒
  onComplete?: () => void;
  className?: string;
}

const TypewriterText: React.FC<TypewriterTextProps> = ({ 
  text, 
  speed = 30, 
  onComplete,
  className 
}) => {
  const [displayText, setDisplayText] = useState('');
  const indexRef = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 重置状态
    setDisplayText('');
    indexRef.current = 0;
    
    // 清除之前的定时器
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    const typeNextChar = () => {
      if (indexRef.current < text.length) {
        setDisplayText(text.slice(0, indexRef.current + 1));
        indexRef.current++;
        timeoutRef.current = setTimeout(typeNextChar, speed);
      } else {
        onComplete?.();
      }
    };

    if (text) {
      typeNextChar();
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [text, speed, onComplete]);

  return (
    <span className={className}>
      {displayText}
      {indexRef.current < text.length && (
        <span className="typewriter-cursor">|</span>
      )}
    </span>
  );
};

export default TypewriterText; 