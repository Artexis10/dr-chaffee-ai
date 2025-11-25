/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Note: Environment variables are loaded from frontend/.env.local (dev) or Coolify (prod)
  // Server-side API routes access process.env directly - no need to expose here
  eslint: {
    // Allow builds to succeed with pre-existing lint warnings
    // TODO: Fix lint issues in a dedicated cleanup PR
    ignoreDuringBuilds: true,
  },
}

module.exports = nextConfig
