import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Tuning Auth Status - Check if user has tuning dashboard access
 * 
 * This endpoint checks the tuning_auth cookie set by /api/tuning/auth/verify.
 * It does NOT call the backend - it's a fast, local check.
 * 
 * Used by:
 * - useTuningAuth hook in the tuning layout to gate access
 * - Any component that needs to check tuning auth status
 * 
 * Returns:
 * - { hasAccess: true } if tuning_auth cookie is valid
 * - { hasAccess: false } if not authenticated
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check for tuning_auth cookie (set by /api/tuning/auth/verify)
  const tuningAuth = req.cookies.tuning_auth;
  const hasAccess = tuningAuth === 'authenticated';

  // Log for debugging (can be removed in production)
  if (!hasAccess) {
    console.log('[Tuning Auth Status] No valid tuning_auth cookie found');
  }

  return res.status(200).json({ hasAccess });
}
