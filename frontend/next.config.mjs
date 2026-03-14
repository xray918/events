/** @type {import('next').NextConfig} */
const nextConfig = {
  // 使用 SWC 压缩（比 Terser 快 7 倍）
  swcMinify: true,
  // 生产构建不生成 source map，减少磁盘 I/O
  productionBrowserSourceMaps: false,
  // 开启增量静态缓存
  experimental: {
    workerThreads: true,
    cpus: 2,
  },
};

export default nextConfig;
