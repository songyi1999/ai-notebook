import React from 'react';
import { Layout } from 'antd';
import { Resizable } from 'react-resizable';
import 'react-resizable/css/styles.css';

const { Sider } = Layout;

interface ResizableSiderProps {
  width: number;
  onResize: (width: number) => void;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const ResizableSider: React.FC<ResizableSiderProps> = ({ width, onResize, children, style }) => {
  return (
    <Resizable
      width={width}
      height={0} // We only want to resize width
      onResize={(_, { size }) => onResize(size.width)}
      handle={<div className="react-resizable-handle" />}
      draggableOpts={{ enableUserSelectHack: true }}
    >
      <Sider
        width={width}
        style={{ height: '100%', background: '#fff', ...style }}
        theme="light"
      >
        {children}
      </Sider>
    </Resizable>
  );
};

export default ResizableSider; 