import * as React from 'react';

interface BlurhashProps {
  hash: string;
  width: number;
  height: number;
  resolutionX?: number;
  resolutionY?: number;
  punch?: number;
  className?: string;
}

export const Blurhash = React.forwardRef<HTMLDivElement, BlurhashProps>(
  ({ hash, width, height, resolutionX = 32, resolutionY = 32, punch = 1, className }, ref) => {
    const [imageUrl, setImageUrl] = React.useState<string | null>(null);
    const canvasRef = React.useRef<HTMLCanvasElement>(null);

    React.useEffect(() => {
      if (canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          // Simple blurhash decoding (placeholder - in production use proper decoder)
          const imageData = ctx.createImageData(width, height);
          const data = imageData.data;
          
          // Fill with gradient based on hash
          for (let i = 0; i < data.length; i += 4) {
            const x = (i / 4) % width;
            const y = Math.floor((i / 4) / width);
            const gray = Math.floor(128 + Math.sin(x / width * Math.PI) * 64 + Math.sin(y / height * Math.PI) * 64);
            data[i] = gray;     // R
            data[i + 1] = gray; // G
            data[i + 2] = gray; // B
            data[i + 3] = 255;  // A
          }
          
          ctx.putImageData(imageData, 0, 0);
          setImageUrl(canvas.toDataURL());
        }
      }
    }, [hash, width, height]);

    return (
      <div 
        ref={ref}
        className={className}
        style={{ 
          width, 
          height, 
          backgroundImage: imageUrl ? `url(${imageUrl})` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      />
    );
  }
);

Blurhash.displayName = 'Blurhash';