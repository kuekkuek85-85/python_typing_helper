# Overview

This project is "파이썬 타자 도우미" (Python Typing Helper) - a static web application designed for middle school students learning Python programming. The application helps students improve their typing skills while becoming familiar with Python syntax, keywords, and common programming patterns. It features four progressive practice modes (keyboard positions, words, sentences, and code blocks) with 5-minute timed sessions, real-time WPM and accuracy tracking, and a leaderboard system.

## Current Implementation Status (v1.0.0 - GitHub Pages)
- ✅ Complete static website deployed on GitHub Pages
- ✅ Four practice modes with dynamic text loading (자리 연습 active)
- ✅ Real-time typing validation with visual feedback
- ✅ 5-minute timer with save restriction until completion
- ✅ Performance metrics calculation (Korean typing speed standard, accuracy, composite score)
- ✅ Student record saving with Supabase database integration
- ✅ Integrated leaderboard with Top10/All view toggle
- ✅ Smart Shift key highlighting based on keyboard layout
- ✅ Fair ranking system with proper tie handling
- ✅ Caps Lock functionality with visual keyboard updates
- ✅ Korean typing speed calculation (characters per minute)
- ✅ Copy/paste prevention and anti-cheating measures
- ✅ Client-side JavaScript architecture with Supabase backend
- ✅ Responsive design for tablets and mobile devices

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 with dark theme
- **UI Framework**: Bootstrap Agent Dark Theme for consistent styling
- **Real-time Features**: Client-side timer, live WPM/accuracy calculation, character-by-character typing validation with visual feedback
- **Responsive Design**: Mobile-first approach with Bootstrap grid system for classroom tablet/laptop usage
- **Static Site Deployment**: GitHub Pages compatible with no server dependencies

## Client-Side Architecture
- **JavaScript Modules**: Config management, database abstraction layer, practice logic, main page controller
- **Authentication**: Simple admin login (admin/admin) stored in localStorage
- **Database Integration**: Supabase JavaScript SDK for real-time database operations
- **Data Validation**: Client-side validation for student ID format (5-digit number + Korean name)
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
- **Connection**: Supabase JavaScript SDK for direct client-side database operations
- **Schema**: Single `records` table with student_id, mode, performance metrics, and timestamps
- **Indexing**: Optimized indexes for leaderboard queries and student record searches

## Third-party Services
- **Hosting Platform**: GitHub Pages for static site hosting
- **CSS Framework**: Bootstrap 5 via CDN with Bootstrap Icons
- **Database Service**: Supabase for PostgreSQL hosting and management
- **Authentication**: Client-side localStorage for session management

## Environment Configuration
- **Required Configuration**: SUPABASE_URL, SUPABASE_ANON_KEY in config.js file
- **Database Setup**: Manual table creation via Supabase SQL Editor
- **Deployment**: GitHub Pages automatic deployment from main branch
- **Development**: Local file:// or localhost testing supported