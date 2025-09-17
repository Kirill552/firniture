declare module 'three-dxf-loader' {
  import * as THREE from 'three';
  
  export class DXFLoader extends THREE.Loader {
    constructor(manager?: THREE.LoadingManager);
    load(
      url: string,
      onLoad: (dxf: THREE.Group) => void,
      onProgress?: (progress: ProgressEvent) => void,
      onError?: (event: ErrorEvent) => void
    ): void;
    parse(text: string): THREE.Group;
    setPath(value: string): void;
  }
  
  export interface LoaderOptions {
    layer?: string | string[];
    skipConstructionGeometry?: boolean;
  }
}