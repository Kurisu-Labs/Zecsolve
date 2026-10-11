// The landing scene: a "shielded pool" of square particles. As the reader scrolls,
// one note's particles leave the pool and assemble into the zecsolve mark (the output
// a receipt discloses) while everything else dithers away. Points render as squares,
// echoing the logo's dissolving pixels.

import {
  BufferAttribute,
  BufferGeometry,
  Color,
  NormalBlending,
  OrthographicCamera,
  Points,
  Scene,
  ShaderMaterial,
  Vector2,
  WebGLRenderer,
} from 'three'

const vertexShader = /* glsl */ `
  attribute vec3 aPool;
  attribute vec3 aTarget;
  attribute float aSel;
  attribute float aSeed;

  uniform float uTime;
  uniform float uProgress;   // 0 pool → 1 note assembled
  uniform float uRelease;    // 0 assembled → 1 handed to the case card
  uniform vec2 uPointer;
  uniform float uSize;
  uniform float uAspect;

  varying float vAlpha;
  varying float vSel;
  varying float vGlow;

  void main() {
    float t = uTime * 0.18;
    vec3 pool = aPool;
    // Slow, non-uniform drift: two incommensurate waves per particle.
    pool.x += sin(t + aSeed * 6.2831 + aPool.y * 2.3) * 0.045;
    pool.y += cos(t * 0.8 + aSeed * 4.1 + aPool.x * 1.7) * 0.035;

    // Particles leave the pool at slightly different moments.
    float k = clamp((uProgress * 1.35) - aSeed * 0.35, 0.0, 1.0);
    k = k * k * (3.0 - 2.0 * k);
    vec3 p = mix(pool, aTarget, k * aSel);

    // Release: the right edge of the mark breaks into drifting squares, like the logo.
    float edge = smoothstep(-0.1, 0.5, (aTarget.x - uAspect * 0.2));
    p.x += uRelease * aSel * (0.25 + aSeed * 0.9) * edge;
    p.y += uRelease * aSel * (aSeed - 0.5) * 0.15 * edge;

    // The pointer is a probe: it pushes the pool apart a little.
    vec2 d = p.xy - uPointer;
    float dist = length(d);
    p.xy += (d / max(dist, 0.0001)) * 0.07 * exp(-dist * 9.0) * (1.0 - aSel * k);

    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);

    float poolAlpha = 0.55 + 0.35 * fract(aSeed * 13.37);
    float unselectedFade = mix(poolAlpha, 0.12, smoothstep(0.0, 0.8, uProgress));
    float selectedAlpha = mix(poolAlpha, 1.0, k) * (1.0 - uRelease * edge * 0.85);
    vAlpha = mix(unselectedFade, selectedAlpha, aSel);
    vSel = aSel * k;
    vGlow = exp(-dist * 6.0);
    gl_PointSize = uSize * mix(1.0, 1.35, vSel);
  }
`

const fragmentShader = /* glsl */ `
  precision highp float;
  uniform vec3 uDim;
  uniform vec3 uZec;
  varying float vAlpha;
  varying float vSel;
  varying float vGlow;

  // 4x4 Bayer threshold: fades become ordered dither instead of soft transparency.
  float bayer4(vec2 p) {
    vec2 q = mod(floor(p), 4.0);
    float i = q.x + q.y * 4.0;
    float m[16];
    m[0]=0.0; m[1]=8.0; m[2]=2.0; m[3]=10.0;
    m[4]=12.0; m[5]=4.0; m[6]=14.0; m[7]=6.0;
    m[8]=3.0; m[9]=11.0; m[10]=1.0; m[11]=9.0;
    m[12]=15.0; m[13]=7.0; m[14]=13.0; m[15]=5.0;
    float v = 0.0;
    for (int j = 0; j < 16; j++) { if (float(j) == i) v = m[j]; }
    return (v + 0.5) / 16.0;
  }

  void main() {
    if (vAlpha < bayer4(gl_FragCoord.xy)) discard;
    vec3 col = mix(uDim, uZec, vSel);
    col = mix(col, vec3(1.0), vGlow * 0.25 * (1.0 - vSel));
    gl_FragColor = vec4(col, 1.0);
  }
`

export interface PixelFieldOptions {
  canvas: HTMLCanvasElement
  markUrl: string
  /** Where the assembled mark sits, in view units (x scaled by aspect). */
  layout?: () => { x: number; y: number; scale: number }
}

export interface PixelField {
  setProgress(value: number): void
  setRelease(value: number): void
  resize(): void
  start(): void
  stop(): void
  dispose(): void
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.decoding = 'async'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`Could not load ${url}`))
    img.src = url
  })
}

/** Sample opaque pixels of the mark into normalised [-0.5, 0.5] coordinates. */
function sampleMark(img: HTMLImageElement, step: number): Float32Array {
  const w = Math.round(img.naturalWidth)
  const h = Math.round(img.naturalHeight)
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return new Float32Array()
  ctx.drawImage(img, 0, 0)
  const data = ctx.getImageData(0, 0, w, h).data
  const pts: number[] = []
  const s = Math.max(w, h)
  for (let y = 0; y < h; y += step) {
    for (let x = 0; x < w; x += step) {
      const a = data[(y * w + x) * 4 + 3] ?? 0
      if (a > 140) pts.push((x - w / 2) / s, -(y - h / 2) / s)
    }
  }
  return new Float32Array(pts)
}

export async function createPixelField(options: PixelFieldOptions): Promise<PixelField> {
  const { canvas } = options
  const renderer = new WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: 'high-performance' })
  const small = window.matchMedia('(max-width: 720px)').matches
  const dpr = Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2)
  renderer.setPixelRatio(dpr)
  renderer.setClearColor(0x000000, 0)

  const scene = new Scene()
  const camera = new OrthographicCamera(-1, 1, 1, -1, -10, 10)
  camera.position.z = 5

  const img = await loadImage(options.markUrl)
  const markPts = sampleMark(img, small ? 4 : 3)
  const selectedCount = markPts.length / 2
  const poolCount = small ? 3200 : 7000
  const count = selectedCount + poolCount

  const aPool = new Float32Array(count * 3)
  const aTarget = new Float32Array(count * 3)
  const aSel = new Float32Array(count)
  const aSeed = new Float32Array(count)

  const uniforms = {
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uRelease: { value: 0 },
    uPointer: { value: new Vector2(9, 9) },
    uSize: { value: (small ? 2.4 : 2.6) * dpr },
    uAspect: { value: 1 },
    uDim: { value: new Color('#5c5c5c') },
    uZec: { value: new Color('#fefb30') },
  }

  function layoutTargets(aspect: number): void {
    const place = options.layout?.() ?? (aspect > 1.1 ? { x: aspect * 0.42, y: 0.02, scale: 1.05 } : { x: 0, y: 0.5, scale: Math.min(0.62, aspect * 0.8) })
    for (let i = 0; i < selectedCount; i++) {
      aTarget[i * 3] = place.x + (markPts[i * 2] ?? 0) * place.scale
      aTarget[i * 3 + 1] = place.y + (markPts[i * 2 + 1] ?? 0) * place.scale
      aTarget[i * 3 + 2] = 0
    }
  }

  function scatterPool(aspect: number): void {
    for (let i = 0; i < count; i++) {
      aPool[i * 3] = (Math.random() * 2 - 1) * aspect * 1.08
      aPool[i * 3 + 1] = (Math.random() * 2 - 1) * 1.08
      aPool[i * 3 + 2] = (Math.random() * 2 - 1) * 0.5
    }
  }

  for (let i = 0; i < count; i++) {
    aSel[i] = i < selectedCount ? 1 : 0
    aSeed[i] = Math.random()
  }

  const geometry = new BufferGeometry()
  const poolAttr = new BufferAttribute(aPool, 3)
  const targetAttr = new BufferAttribute(aTarget, 3)
  geometry.setAttribute('position', poolAttr) // bounding volume only; shader uses aPool/aTarget
  geometry.setAttribute('aPool', poolAttr)
  geometry.setAttribute('aTarget', targetAttr)
  geometry.setAttribute('aSel', new BufferAttribute(aSel, 1))
  geometry.setAttribute('aSeed', new BufferAttribute(aSeed, 1))

  const material = new ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms,
    transparent: false,
    depthTest: false,
    blending: NormalBlending,
  })
  const points = new Points(geometry, material)
  points.frustumCulled = false
  scene.add(points)

  let aspect = 1
  function resize(): void {
    const rect = canvas.getBoundingClientRect()
    const width = Math.max(rect.width, 1)
    const height = Math.max(rect.height, 1)
    renderer.setSize(width, height, false)
    const nextAspect = width / height
    const rescatter = Math.abs(nextAspect - aspect) > 0.05
    aspect = nextAspect
    camera.left = -aspect
    camera.right = aspect
    camera.top = 1
    camera.bottom = -1
    camera.updateProjectionMatrix()
    uniforms.uAspect.value = aspect
    if (rescatter) {
      scatterPool(aspect)
      poolAttr.needsUpdate = true
    }
    layoutTargets(aspect)
    targetAttr.needsUpdate = true
    render()
  }

  function render(): void {
    renderer.render(scene, camera)
  }

  const onPointer = (event: PointerEvent) => {
    const rect = canvas.getBoundingClientRect()
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    const y = -(((event.clientY - rect.top) / rect.height) * 2 - 1)
    uniforms.uPointer.value.set(x * aspect, y)
  }
  const onLeave = () => uniforms.uPointer.value.set(9, 9)
  window.addEventListener('pointermove', onPointer, { passive: true })
  document.addEventListener('pointerleave', onLeave)

  let frame = 0
  let running = false
  let last = performance.now()
  const loop = (now: number) => {
    uniforms.uTime.value += Math.min((now - last) / 1000, 0.05)
    last = now
    render()
    frame = requestAnimationFrame(loop)
  }

  const onVisibility = () => {
    if (document.hidden) api.stop()
  }
  document.addEventListener('visibilitychange', onVisibility)

  scatterPool(1)
  resize()
  await renderer.compileAsync(scene, camera)

  const api: PixelField = {
    setProgress(value) {
      uniforms.uProgress.value = value
      if (!running) render()
    },
    setRelease(value) {
      uniforms.uRelease.value = value
      if (!running) render()
    },
    resize,
    start() {
      if (running) return
      running = true
      last = performance.now()
      frame = requestAnimationFrame(loop)
    },
    stop() {
      running = false
      cancelAnimationFrame(frame)
    },
    dispose() {
      api.stop()
      window.removeEventListener('pointermove', onPointer)
      document.removeEventListener('pointerleave', onLeave)
      document.removeEventListener('visibilitychange', onVisibility)
      geometry.dispose()
      material.dispose()
      renderer.dispose()
    },
  }
  return api
}
