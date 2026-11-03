/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.COORDINATOR_URL 
          ? `${process.env.COORDINATOR_URL}/api/:path*` 
          : "http://localhost:8000/api/:path*",
      },
      {
        source: "/health/:path*",
        destination: process.env.COORDINATOR_URL
          ? `${process.env.COORDINATOR_URL}/health/:path*`
          : "http://localhost:8000/health/:path*",
      },
    ];
  },
};

module.exports = nextConfig;

