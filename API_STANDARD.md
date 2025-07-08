# Kindle Content Server - API Endpoint Standard

## 📋 **Standardized API Endpoints**

All API endpoints follow RESTful conventions and are prefixed with `/api`.

### 🔐 **Authentication**
```
POST   /api/auth/login      - User login
POST   /api/auth/register   - User registration  
POST   /api/auth/logout     - User logout
GET    /api/auth/me         - Get current user info
```

### 📚 **Books Management**
```
GET    /api/books           - List all books
GET    /api/books/{id}      - Get specific book
POST   /api/books/upload    - Upload new book file
DELETE /api/books/{id}      - Delete book
```

### 📰 **News Sources**
```
GET    /api/news-sources              - List news sources
POST   /api/news-sources              - Create news source
PUT    /api/news-sources/{id}         - Update news source
DELETE /api/news-sources/{id}         - Delete news source
POST   /api/news-sources/{id}/sync    - Trigger manual sync
```

### 🔄 **Sync Status**
```
GET    /api/sync-status       - List all sync statuses
GET    /api/sync-status/{id}  - Get specific sync status
```

### 🏥 **Health & Info**
```
GET    /api/health     - API health check (for frontend)
GET    /health         - Basic health check (for load balancers)
GET    /               - Service information
```

## 🔧 **Backend Implementation Status**

### ✅ **IMPLEMENTED** (in `app_local.py`)
- `/api/health` - Health check
- `/api/books` - List books  
- `/api/books/upload` - Upload books
- `/api/books/{id}` - Get/Delete specific book
- `/api/news-sources` - All CRUD operations
- `/api/news-sources/{id}/sync` - Manual sync trigger
- `/api/sync-status` - Get sync statuses
- `/api/auth/*` - All auth endpoints (dev placeholders)

### 📱 **Frontend Compliance**
- All frontend API calls in `/services/api.ts` now match backend endpoints
- Base URL construction: `{server}/api/{endpoint}`
- CORS properly configured for cross-origin requests

## 🎯 **Standards & Conventions**

### **URL Structure**
- **Prefix**: All API endpoints start with `/api/`
- **Resources**: Use kebab-case for multi-word resources (`news-sources`, `sync-status`)
- **IDs**: Use path parameters for resource IDs (`/api/books/{id}`)
- **Actions**: Use path segments for actions (`/api/news-sources/{id}/sync`)

### **HTTP Methods**
- **GET**: Retrieve data (lists or single items)
- **POST**: Create new resources or trigger actions
- **PUT**: Update existing resources (full replacement)
- **DELETE**: Remove resources
- **OPTIONS**: CORS preflight (automatically handled)

### **Response Format**
All responses use consistent JSON structure:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

**List Response:**
```json
{
  "success": true,
  "data": [...],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

### **CORS Configuration**
- **Origins**: `*` for local development, specific domains for production
- **Methods**: `GET, POST, PUT, DELETE, OPTIONS`
- **Headers**: `Content-Type, Authorization`
- **Preflight**: Automatic OPTIONS handling for all endpoints

### **Authentication**
- **Method**: Bearer token in `Authorization` header
- **Format**: `Authorization: Bearer {token}`
- **Dev Mode**: Uses placeholder token `dev-token-123`

## 🔄 **Migration Notes**

### **Fixed Mismatches:**
1. **Health Check**: Added `/api/health` (frontend expected this)
2. **News Sources**: Changed `/api/news/sources` → `/api/news-sources`
3. **Sync Status**: Changed `/api/sync/logs` → `/api/sync-status`
4. **Authentication**: Added missing auth endpoints
5. **CORS**: Configured for cross-origin requests

### **Breaking Changes:**
- If any existing code uses old endpoints, update to new standard
- All frontend API calls now use `/api/` prefix consistently

## 🚀 **Testing Endpoints**

You can test all endpoints with:

```bash
# Health check
curl http://192.168.102.8:8080/api/health

# Books
curl http://192.168.102.8:8080/api/books

# News sources  
curl http://192.168.102.8:8080/api/news-sources

# Auth (POST with JSON)
curl -X POST http://192.168.102.8:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

## 📝 **Development Workflow**

1. **Adding New Endpoints**: Follow the standard URL structure
2. **Frontend Changes**: Update `/services/api.ts` with new endpoints  
3. **Backend Changes**: Add routes in `app_local.py` (dev) and main app (prod)
4. **Testing**: Verify both frontend and backend match before deployment

This standard ensures consistent API design and prevents future endpoint mismatches!