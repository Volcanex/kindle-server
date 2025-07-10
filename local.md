# Kindle Content Server - Local Development Setup

Quick start guide for running the entire Kindle Content Server stack locally for development and testing.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **npm or yarn** (package manager)
- **Expo CLI** (`npm install -g @expo/cli`)

### 1. Backend Setup (Flask API)

```bash
# Navigate to backend
cd project/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install LOCAL dependencies (lighter, no Google Cloud deps)
pip install -r requirements-local.txt

# Run LOCAL backend server (simplified for testing)
python app_local.py
```

**Backend will be available at: `http://localhost:8080`**

### 2. Frontend Setup (React Native/Expo)

```bash
# Navigate to frontend (in a new terminal)
cd project/frontend

# Install dependencies
npm install

# Start Expo development server
npm start
```

**Frontend options:**
- **Web**: Press `w` or run `npm run web` → `http://localhost:8081`
- **iOS**: Press `i` or run `npm run ios` (requires Xcode/iOS Simulator)
- **Android**: Press `a` or run `npm run android` (requires Android Studio/Emulator)

## 📱 Testing the App

### Backend API Testing
The backend includes these endpoints for testing:

```bash
# Health check
curl http://localhost:8080/health

# API info
curl http://localhost:8080/

# Books API (examples)
curl http://localhost:8080/api/books
curl -X POST http://localhost:8080/api/books/upload -F "file=@/path/to/book.epub"

# News API
curl http://localhost:8080/api/news/sources
curl -X POST http://localhost:8080/api/news/aggregate

# Sync API
curl http://localhost:8080/api/sync/logs
```

### Frontend Features to Test
1. **📚 Book Upload** - Upload EPUB/PDF files
2. **📰 News Management** - Add RSS feeds and news sources
3. **🔄 Sync Status** - Monitor sync operations
4. **⚙️ Settings** - Configure app preferences

### 🔓 Authentication (LOCAL DEVELOPMENT ONLY)
**Authentication is DISABLED for local testing:**
- No real login/password required
- Auto-logged in as "Local Dev User"
- All auth endpoints return success automatically
- Focus on testing core functionality (books, news, sync)

## 🐳 Alternative: Docker Setup

If you prefer containerized development:

```bash
# Backend with Docker
cd project/backend
docker build -t kindle-backend .
docker run -p 8080:8080 kindle-backend

# Or use Docker Compose for full stack
cd project/infrastructure/docker
docker-compose up --build
```

## 🔧 Configuration

### Backend Configuration
For local development, no `.env` file needed! The `app_local.py` uses SQLite by default.

**Optional** - Create `project/backend/.env` for advanced features:
```env
SECRET_KEY=your-secret-key-here
DEV_DATABASE_URL=sqlite:///kindle_local.db
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Frontend Configuration
Create `project/frontend/.env`:
```env
EXPO_PUBLIC_API_URL=http://localhost:8080/api
```

## 🧪 Running Tests

### Backend Tests
```bash
cd project/backend
source venv/bin/activate
python -m pytest tests/ -v
```

**Test Results:**
- ✅ `test_health_endpoint` - Health check functionality
- ✅ `test_root_endpoint` - API info endpoint
- ✅ `test_404_handling` - Error handling

### Frontend Tests
```bash
cd project/frontend
npm test  # (No test script configured yet)
```

## 📂 Project Structure

```
kindle/
├── project/
│   ├── backend/           # Flask API server
│   │   ├── app.py        # Main application
│   │   ├── models/       # Database models
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── tests/        # Test suite
│   │   └── venv/         # Python virtual environment
│   ├── frontend/         # React Native/Expo app
│   │   ├── App.tsx       # Main app component
│   │   ├── screens/      # App screens
│   │   ├── components/   # Reusable components
│   │   ├── services/     # API integration
│   │   └── node_modules/ # Node dependencies
│   └── infrastructure/   # Docker & deployment configs
└── run.md               # This file
```

## 🔍 Development Workflow

### 1. Start Both Services
```bash
# Terminal 1: Backend (LOCAL MODE)
cd project/backend && source venv/bin/activate && python app_local.py

# Terminal 2: Frontend
cd project/frontend && npm start
```

### 2. Access the Apps
- **Backend API**: http://localhost:8080
- **Frontend Web**: http://localhost:8081 (press `w` in Expo)
- **Mobile**: Use Expo Go app or simulators

### 3. Test Basic Functionality
1. Visit backend health endpoint: http://localhost:8080/health
2. Open frontend and check if it loads
3. Try uploading a book file (use any EPUB/PDF)
4. Add a news source (any RSS feed URL)

## 🚨 Troubleshooting

### Backend Issues
```bash
# Port already in use
lsof -ti:8080 | xargs kill -9

# Dependencies missing
cd project/backend && pip install -r requirements.txt

# Database issues
rm kindle.db  # Reset SQLite database
python app.py  # Recreate tables
```

### Frontend Issues
```bash
# Clear Expo cache
cd project/frontend && npx expo start --clear

# Clear npm cache
npm cache clean --force && rm -rf node_modules && npm install

# Metro bundler issues
npx expo start --tunnel  # Use tunnel connection
```

### Common Issues
1. **Backend not starting**: Check if port 8080 is free
2. **Frontend can't connect**: Verify API_URL in frontend `.env`
3. **File uploads failing**: Check file permissions and size limits
4. **CORS errors**: Backend includes CORS headers for local development

## 📝 Next Steps

### For Development
1. **Add authentication**: Implement login/register screens
2. **Database setup**: Switch from SQLite to PostgreSQL
3. **File storage**: Configure Google Cloud Storage
4. **Email setup**: Configure SMTP for Kindle sync

### For Production
1. **Deploy backend**: Use Google Cloud Run
2. **Build mobile apps**: Generate APK/IPA files
3. **Environment configs**: Set up staging/production environments
4. **Monitoring**: Add logging and error tracking

## 🤝 Getting Help

- **Backend logs**: Check terminal output where `python app.py` is running
- **Frontend logs**: Check browser console or Expo CLI output
- **API testing**: Use curl, Postman, or browser developer tools
- **File issues**: Check file permissions and supported formats

---

**Ready to start?** Run both terminals and visit http://localhost:8081 to see your Kindle Content Server in action! 🎉