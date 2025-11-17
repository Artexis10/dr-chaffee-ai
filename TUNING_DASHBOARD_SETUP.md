# Tuning Dashboard - Setup & Access Guide

## Overview
The AI Tuning Dashboard is a password-protected admin interface for configuring:
- Custom AI instructions
- Embedding models
- Search parameters
- System statistics

## Access Information

### URL
```
http://localhost:3000/tuning
```

### Default Password
```
chaffee2024
```

### Authorized Users
- Hugo (developer)
- Dr. Chaffee (admin)

## Features

### 1. Custom Instructions Editor
- Create and manage custom instruction sets
- Version history and rollback capability
- Preview merged prompts
- Activate/deactivate instruction sets

### 2. Embedding Models
- View available embedding models
- Switch query models instantly
- See model specifications (dimensions, cost, provider)
- Monitor active models

### 3. Search Configuration
- Adjust `top_k` parameter (default: 20)
- Set similarity threshold (default: 0.0)
- Enable/disable reranker
- Test search functionality

### 4. System Statistics
- Total videos ingested
- Total segments
- Embedding coverage percentage
- Unique speakers
- Embedding dimensions

## Security

### Session-Based Authentication
- Password verified on first access
- Session stored in browser sessionStorage
- Clears when browser closes
- Logout button available in header

### Password Management
- Password stored in `NEXT_PUBLIC_TUNING_PASSWORD` environment variable
- Change password by updating `.env.local`:
  ```
  NEXT_PUBLIC_TUNING_PASSWORD=your-new-password
  ```
- Restart frontend for changes to take effect

## Styling

The dashboard features:
- Dark theme (slate-900 to slate-800 gradient)
- Professional card-based layout
- Blue accent colors (#3b82f6)
- Responsive design (mobile-friendly)
- Lucide React icons
- Smooth transitions and hover effects

## API Endpoints

All endpoints require the backend to be running:

```
GET  /api/tuning/instructions          - List custom instructions
POST /api/tuning/instructions          - Create new instruction set
GET  /api/tuning/instructions/:id      - Get specific instruction
PUT  /api/tuning/instructions/:id      - Update instruction
DELETE /api/tuning/instructions/:id    - Delete instruction
POST /api/tuning/instructions/:id/activate - Activate instruction set
POST /api/tuning/instructions/:id/rollback - Rollback to previous version
POST /api/tuning/instructions/preview  - Preview merged prompt

GET  /api/tuning/summarizer/models     - List available summarizer models
GET  /api/tuning/summarizer/config     - Get current summarizer config
POST /api/tuning/summarizer/config     - Update summarizer config

GET  /api/tuning/models                - List embedding models
POST /api/tuning/models/query          - Switch query model
POST /api/tuning/models/ingestion      - Switch ingestion model

GET  /api/tuning/config                - Get search config
POST /api/tuning/search/config         - Update search config
POST /api/tuning/search/test           - Test search with query

GET  /api/tuning/stats                 - Get system statistics
```

## Troubleshooting

### Password Screen Not Appearing
- Check that `NEXT_PUBLIC_TUNING_PASSWORD` is set in `.env.local`
- Restart frontend: `docker-compose restart frontend`
- Clear browser cache and sessionStorage

### Dashboard Not Loading After Password
- Check backend is running: `docker-compose ps`
- Verify API endpoints are accessible
- Check browser console for errors

### Styling Issues
- Clear Next.js cache: `docker exec drchaffee-frontend rm -rf /app/.next`
- Restart frontend
- Check Tailwind CSS is properly configured

### Session Lost
- Session clears when browser closes
- Use logout button to clear session manually
- Refresh page to re-authenticate

## Development Notes

### File Locations
- Frontend page: `/frontend/src/app/tuning/page.tsx`
- Custom Instructions component: `/frontend/src/components/CustomInstructionsEditor.tsx`
- Backend API: `/backend/api/tuning.py`

### Environment Variables
```bash
# Frontend (.env.local)
NEXT_PUBLIC_TUNING_PASSWORD=chaffee2024
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend (.env)
SUMMARIZER_MODEL=gpt-4-turbo
SUMMARIZER_TEMPERATURE=0.1
SUMMARIZER_MAX_TOKENS=2000
```

### Database Tables
- `custom_instructions` - Stores instruction sets
- `custom_instructions_history` - Tracks versions
- Automatic triggers for versioning

## Performance Tips

1. **Search Testing**: Use smaller `top_k` values for faster results
2. **Model Switching**: Switching models is instant if embeddings exist
3. **Instruction Updates**: Changes take effect on next API call
4. **Batch Operations**: Use API directly for bulk updates

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `docker-compose logs backend`
3. Review frontend logs: `docker-compose logs frontend`
4. Contact Hugo or Dr. Chaffee

---

**Last Updated**: November 17, 2025
**Version**: 1.0
