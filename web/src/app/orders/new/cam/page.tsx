"use client"

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Download } from 'lucide-react';

type Artifact = {
  name: string;
  type: 'DXF' | 'G-code';
  size: string;
  url: string;
};

export default function NewOrderCamPage() {
  const [dxfJobStatus, setDxfJobStatus] = useState<'idle' | 'running' | 'completed'>('idle');
  const [gcodeJobStatus, setGcodeJobStatus] = useState<'idle' | 'running' | 'completed'>('idle');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  const handleDxfGeneration = () => {
    setDxfJobStatus('running');
    // Simulate API call
    setTimeout(() => {
      setDxfJobStatus('completed');
      setArtifacts((prev) => [...prev, { name: 'cabinet.dxf', type: 'DXF', size: '1.2 MB', url: '#' }]);
    }, 3000);
  };

  const handleGcodeGeneration = () => {
    setGcodeJobStatus('running');
    // Simulate API call
    setTimeout(() => {
      setGcodeJobStatus('completed');
      setArtifacts((prev) => [...prev, { name: 'parts.nc', type: 'G-code', size: '5.6 MB', url: '#' }]);
    }, 5000);
  };

  return (
    <div className="p-6 w-full">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>CAM-задачи</CardTitle>
          <CardDescription>Шаг 4: Запустите генерацию файлов для станков</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-4 items-center">
            <Button onClick={handleDxfGeneration} disabled={dxfJobStatus !== 'idle'}>
              {dxfJobStatus === 'running' ? 'Генерация DXF...' : 'Сгенерировать DXF'}
            </Button>
            <Button onClick={handleGcodeGeneration} disabled={gcodeJobStatus !== 'idle' || dxfJobStatus !== 'completed'}>
              {gcodeJobStatus === 'running' ? 'Генерация G-code...' : 'Сгенерировать G-code'}
            </Button>
            <span
              role="status"
              aria-live="polite"
              className="text-sm text-muted-foreground"
            >
              {dxfJobStatus === 'running' && 'Идет генерация DXF...'}
              {gcodeJobStatus === 'running' && ' Идет генерация G-code...'}
            </span>
          </div>

          {artifacts.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Готовые артефакты:</h3>
              <div className="space-y-2">
                {artifacts.map((artifact) => (
                  <div key={artifact.name} className="flex items-center justify-between p-2 border rounded-md">
                    <div className="flex items-center gap-2">
                      <FileText className="h-6 w-6" />
                      <div>
                        <p className="font-medium">{artifact.name}</p>
                        <p className="text-sm text-gray-500">{artifact.type} - {artifact.size}</p>
                      </div>
                    </div>
                    <Button variant="outline" size="icon" asChild>
                      <a href={artifact.url} download>
                        <Download className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
