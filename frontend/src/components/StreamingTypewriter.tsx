import React, { useEffect, useRef, useState, useCallback } from 'react';

interface StreamingTypewriterProps {
  content: string;
  isStreaming: boolean;
  speed?: number; // 打字速度，毫秒
  onComplete?: () => void;
  className?: string;
}

const StreamingTypewriter: React.FC<StreamingTypewriterProps> = ({ 
  content, 
  isStreaming,
  speed = 30, 
  onComplete,
  className 
}) => {
  const [displayText, setDisplayText] = useState('');
  const [lastProcessedIndex, setLastProcessedIndex] = useState(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);

  const typeText = useCallback((fromIndex: number, toIndex: number) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    isTypingRef.current = true;
    let currentIndex = fromIndex;

    const typeNextChar = () => {
      if (currentIndex < toIndex) {
        setDisplayText(content.slice(0, currentIndex + 1));
        currentIndex++;
        timeoutRef.current = setTimeout(typeNextChar, speed);
      } else {
        isTypingRef.current = false;
        setLastProcessedIndex(toIndex);
        
        // 如果不在流式传输中且已完成所有内容，调用完成回调
        if (!isStreaming && toIndex >= content.length) {
          onComplete?.();
        }
      }
    };

    typeNextChar();
  }, [content, speed, isStreaming, onComplete]);

  useEffect(() => {
    const newContentLength = content.length;
    
    // 如果有新内容且当前没在打字
    if (newContentLength > lastProcessedIndex && !isTypingRef.current) {
      typeText(lastProcessedIndex, newContentLength);
    }
  }, [content, lastProcessedIndex, typeText]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <span className={className}>
      {displayText}
      {(isStreaming || isTypingRef.current) && (
        <span 
          className="typewriter-cursor"
          style={{
            marginLeft: '2px',
            animation: 'typewriter-blink 1s infinite'
          }}
        >
          |
        </span>
      )}
      <style>{`
        @keyframes typewriter-blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </span>
  );
};

export default StreamingTypewriter; 