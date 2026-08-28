/**
 * 一次性脚本：生成占位应用图标 build/icon.ico（256×256，ICO 内嵌 PNG）。
 * 纯 Node 实现（zlib + 手写 PNG/ICO 打包），无第三方依赖。
 * 设计：蓝色圆角方块 + 白色取景框 + 中央扫描线，寓意“图像检测/定位”。
 * 正式 logo 就绪后直接替换 build/icon.ico 即可。
 */
import zlib from 'node:zlib'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const SIZE = 256
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const outDir = path.join(root, 'build')
const outFile = path.join(outDir, 'icon.ico')

// ---------- 颜色 ----------
const BLUE = [0x2f, 0x6f, 0xed]
const WHITE = [0xff, 0xff, 0xff]

// ---------- 图形覆盖度（SDF 抗锯齿，dist 单位 px） ----------
function roundedRectDist(px, py, x0, y0, x1, y1, r) {
  const cx = (x0 + x1) / 2
  const cy = (y0 + y1) / 2
  const hw = (x1 - x0) / 2
  const hh = (y1 - y0) / 2
  const qx = Math.abs(px - cx) - (hw - r)
  const qy = Math.abs(py - cy) - (hh - r)
  const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0))
  const inside = Math.min(Math.max(qx, qy), 0)
  return outside + inside - r
}

function rectCoverage(px, py, x0, y0, x1, y1, r) {
  return Math.min(1, Math.max(0, 0.5 - roundedRectDist(px, py, x0, y0, x1, y1, r)))
}

function bandCoverage(px, py, y0, y1) {
  const d = Math.min(py - y0, y1 - py)
  return Math.min(1, Math.max(0, 0.5 + d))
}

function pixelColor(x, y) {
  const px = x + 0.5
  const py = y + 0.5

  const bg = rectCoverage(px, py, 0, 0, SIZE - 1, SIZE - 1, 48)

  // 白色取景框（描边圆角矩形）
  const frameOuter = rectCoverage(px, py, 40, 40, 215, 215, 28)
  const frameInner = rectCoverage(px, py, 54, 54, 201, 201, 14)
  const frame = frameOuter * (1 - frameInner)

  // 中央扫描线
  const scan = bandCoverage(px, py, 122, 134) * rectCoverage(px, py, 60, 122, 195, 134, 6)

  if (scan > 0.001) return [WHITE[0], WHITE[1], WHITE[2], Math.round(scan * 255)]
  if (frame > 0.001) return [WHITE[0], WHITE[1], WHITE[2], Math.round(frame * 255)]
  if (bg > 0.001) return [BLUE[0], BLUE[1], BLUE[2], Math.round(bg * 255)]
  return [0, 0, 0, 0]
}

// ---------- PNG 编码 ----------
const crcTable = new Int32Array(256).map((_, n) => {
  let c = n
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
  return c
})

function crc32(buf) {
  let crc = 0xffffffff
  for (let i = 0; i < buf.length; i++) crc = (crc >>> 8) ^ crcTable[(crc ^ buf[i]) & 0xff]
  return (crc ^ 0xffffffff) >>> 0
}

function pngChunk(type, data) {
  const len = Buffer.alloc(4)
  len.writeUInt32BE(data.length)
  const typeBuf = Buffer.from(type, 'ascii')
  const crcBuf = Buffer.alloc(4)
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])))
  return Buffer.concat([len, typeBuf, data, crcBuf])
}

function encodePng(size, rgba) {
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8 // 位深
  ihdr[9] = 6 // 颜色类型：RGBA
  ihdr[10] = 0
  ihdr[11] = 0
  ihdr[12] = 0

  const raw = Buffer.alloc((1 + size * 4) * size)
  for (let y = 0; y < size; y++) {
    const rowStart = y * (1 + size * 4)
    raw[rowStart] = 0 // filter: None
    rgba.copy(raw, rowStart + 1, y * size * 4, (y + 1) * size * 4)
  }

  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    pngChunk('IEND', Buffer.alloc(0)),
  ])
}

// ---------- ICO 打包（内嵌 PNG） ----------
function wrapIco(png) {
  const ico = Buffer.alloc(22 + png.length)
  ico.writeUInt16LE(0, 0) // reserved
  ico.writeUInt16LE(1, 2) // type: icon
  ico.writeUInt16LE(1, 4) // image count
  ico[6] = 0 // width 256 -> 0
  ico[7] = 0 // height 256 -> 0
  ico[8] = 0 // palette
  ico[9] = 0 // reserved
  ico.writeUInt16LE(1, 10) // planes
  ico.writeUInt16LE(32, 12) // bpp
  ico.writeUInt32LE(png.length, 14) // bytes in resource
  ico.writeUInt32LE(22, 18) // image offset
  png.copy(ico, 22)
  return ico
}

// ---------- 主流程 ----------
const rgba = Buffer.alloc(SIZE * SIZE * 4)
for (let y = 0; y < SIZE; y++) {
  for (let x = 0; x < SIZE; x++) {
    const [r, g, b, a] = pixelColor(x, y)
    const o = (y * SIZE + x) * 4
    rgba[o] = r
    rgba[o + 1] = g
    rgba[o + 2] = b
    rgba[o + 3] = a
  }
}

mkdirSync(outDir, { recursive: true })
writeFileSync(outFile, wrapIco(encodePng(SIZE, rgba)))
console.log(`已生成占位图标: ${outFile}`)
