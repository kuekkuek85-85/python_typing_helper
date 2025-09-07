// Supabase 클라이언트 설정
// 환경변수는 여기서 직접 설정해야 합니다 (GitHub Pages에서는 runtime 환경변수를 사용할 수 없음)
const SUPABASE_CONFIG = {
    url: 'YOUR_SUPABASE_URL', // Supabase 프로젝트 URL
    key: 'YOUR_SUPABASE_ANON_KEY' // Supabase anon key
};

// 개발 모드 확인 (localhost 또는 file://)
const isDevelopment = location.hostname === 'localhost' || location.protocol === 'file:';

// 연습 모드 설정
const PRACTICE_MODES = {
    '자리': {
        title: '자리 연습',
        description: '파이썬 키워드와 키보드를 연습하세요',
        icon: '⌨️',
        color: 'primary',
        available: true
    },
    '낱말': {
        title: '낱말 연습',
        description: '파이썬 변수명과 함수명을 연습하세요',
        icon: '🔤',
        color: 'success',
        available: false
    },
    '문장': {
        title: '문장 연습',
        description: '파이썬 문장과 표현식을 연습하세요',
        icon: '📝',
        color: 'info',
        available: false
    },
    '문단': {
        title: '문단 연습',
        description: '파이썬 함수와 클래스를 연습하세요',
        icon: '📄',
        color: 'warning',
        available: false
    }
};

// 연습 텍스트 데이터
const PRACTICE_TEXTS = {
    '자리': [
        'print input if else for while',
        'def class return True False None',
        'import from as and or not in is',
        'try except finally pass break continue',
        'lambda with yield global nonlocal',
        'assert del exec eval repr str int float',
        'list tuple dict set range len sum max min',
        'open read write close file path join',
        'append extend insert remove pop index count',
        'split strip replace upper lower title',
        'format join sort reverse copy clear',
        'self init main args kwargs super',
        'request response json data api url',
        'error exception debug info warning',
        'config settings database model view',
        'test unit mock patch fixture setup',
        'async await future task thread process',
        'map filter reduce lambda x y z i j k',
        'start end step begin finish result',
        'name age email address phone number'
    ]
};

// 관리자 설정
const ADMIN_CONFIG = {
    username: 'admin',
    password: 'admin'
};

// 세션 키
const SESSION_KEY = 'typing_admin_session';

// 유틸리티 함수
const Utils = {
    // URL 파라미터 가져오기
    getUrlParameter: function(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    },

    // 로컬 스토리지 관리
    setSession: function(key, value) {
        localStorage.setItem(key, JSON.stringify(value));
    },

    getSession: function(key) {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
    },

    removeSession: function(key) {
        localStorage.removeItem(key);
    },

    // 시간 포맷팅
    formatTime: function(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    // 한국어 타자 속도 계산 (글자 기준)
    calculateKoreanWPM: function(characters, timeInMinutes) {
        // 한국어는 글자당 1타로 계산
        // 5글자 = 1단어 (영어 기준)로 환산
        const words = characters / 5;
        return Math.round(words / timeInMinutes);
    },

    // 학생 ID 유효성 검사
    validateStudentId: function(studentId) {
        const pattern = /^\d{5}\s[가-힣]{2,4}$/;
        return pattern.test(studentId);
    },

    // 날짜 포맷팅
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};