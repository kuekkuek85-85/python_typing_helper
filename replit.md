# Overview

This project is "파이썬 타자 도우미" (Python Typing Helper) - a Python typing practice web application designed for middle school students learning Python programming. The application helps students improve their English typing skills while becoming familiar with Python syntax, keywords, and common programming patterns. It features four progressive practice modes (keyboard positions, words, sentences, and code blocks) with 5-minute timed sessions, real-time WPM and accuracy tracking, and a leaderboard system.

## Current Implementation Status (v0.7.2)
- ✅ Complete Flask web application with Supabase database
- ✅ Four practice modes with dynamic text loading
- ✅ Real-time typing validation with visual feedback
- ✅ 5-minute timer with save restriction until completion
- ✅ Performance metrics calculation (WPM, accuracy, composite score)
- ✅ Word-based progressive scoring system with real-time accumulation
- ✅ Single-line text display for character practice mode
- ✅ Student record saving with validation
- ✅ API endpoints for data operations
- ✅ Integrated leaderboard with Top10/All view toggle
- ✅ Smart Shift key highlighting based on keyboard layout
- ✅ Fair ranking system with proper tie handling
- ✅ Caps Lock functionality with visual keyboard updates
- ✅ Korean-English input mode detection and guidance

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: HTML5, CSS3, JavaScript (vanilla), Bootstrap 5 with dark theme
- **UI Framework**: Bootstrap Agent Dark Theme for consistent styling across Replit environment
- **Real-time Features**: Client-side timer, live WPM/accuracy calculation, character-by-character typing validation with visual feedback
- **Responsive Design**: Mobile-first approach with Bootstrap grid system for classroom tablet/laptop usage

## Backend Architecture
- **Web Framework**: Flask (Python) with session management
- **Authentication**: Simple admin login (admin/admin) for teacher dashboard functionality
- **API Design**: RESTful endpoints for practice data, record saving, and admin operations
- **Data Validation**: Dual client/server-side validation for student ID format (5-digit number + Korean name)
- **Business Logic**: WPM calculation (5 characters = 1 word), accuracy percentage, composite scoring algorithm

## Practice Content Management
- **Content Structure**: Four progressive difficulty modes with curated Python syntax examples
- **Text Generation**: Predefined arrays of practice texts focusing on Python keywords, built-ins, and common patterns
- **Difficulty Progression**: From basic keyboard positions to complete code blocks with proper indentation
- **Validation Rules**: 300-second minimum session duration to prevent premature submissions

## Scoring and Analytics
- **Metrics Calculation**: Real-time WPM (words per minute), accuracy percentage, composite score formula
- **Score Formula**: `score = round(max(0, WPM) * (accuracy/100)^2 * 100)` to balance speed and accuracy
- **Session Tracking**: Duration validation, typing statistics, progress monitoring

# External Dependencies

## Database Integration
- **Primary Database**: Supabase (managed PostgreSQL)
- **Connection**: Supabase Python client library for database operations
- **Schema**: Single `records` table with student_id, mode, performance metrics, and timestamps
- **Indexing**: Optimized indexes for leaderboard queries and student record searches using pg_trgm extension

## Third-party Services
- **Hosting Platform**: Replit with environment variable configuration
- **CSS Framework**: Bootstrap 5 via CDN with Bootstrap Icons
- **Database Service**: Supabase for PostgreSQL hosting and management
- **Authentication**: Environment-based admin credentials for teacher access

## Environment Configuration
- **Required Secrets**: SUPABASE_URL, SUPABASE_ANON_KEY, ADMIN_USER, ADMIN_PASS, SESSION_SECRET
- **Database Setup**: Automated table creation with proper indexing for performance
- **Deployment**: Single-click Replit deployment with automatic dependency installation