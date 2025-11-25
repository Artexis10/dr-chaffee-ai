/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Note: Environment variables are loaded from frontend/.env.local (dev) or Coolify (prod)
  // Server-side API routes access process.env directly - no need to expose here
}

module.exports = nextConfig
