import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../../utils/env';

/**
 * Discord Auth Status - Check if Discord OAuth is configured
 * 
 * Returns whether Discord login should be shown on the login page.
 * This checks both the frontend env var and the backend configuration.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check frontend env var first
  const frontendEnabled = process.env.DISCORD_LOGIN_ENABLED === 'true';
  
  if (!frontendEnabled) {
    return res.status(200).json({ enabled: false, reason: 'disabled_in_frontend' });
  }

  try {
    // Check backend configuration
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(`${BACKEND_API_URL}/api/auth/discord/status`, {
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      const data = await response.json();
      
      // Discord is enabled only if both frontend and backend are configured
      return res.status(200).json({ 
        enabled: data.configured === true,
        reason: data.configured ? 'configured' : 'backend_not_configured'
      });
    } else {
      return res.status(200).json({ enabled: false, reason: 'backend_error' });
    }
  } catch (error) {
    console.error('[Discord Status] Error checking backend:', error);
    return res.status(200).json({ enabled: false, reason: 'backend_unreachable' });
  }
}
