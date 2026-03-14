/** @type {import('next').NextConfig} */
const nextConfig = {
  // SWC 压缩（比 Terser 快 7 倍）
  swcMinify: true,
  // 生产构建不生成 source map
  productionBrowserSourceMaps: false,
  // 构建时跳过 ESLint（由 start.sh 单独在构建前运行）
  eslint: { ignoreDuringBuilds: true },
  // 构建时跳过 TypeScript 类型检查（编译错误 SWC 仍会报）
  typescript: { ignoreBuildErrors: true },
  // 多线程编译
  experimental: {
    workerThreads: true,
    cpus: 2,
  },
};

export default nextConfig;
