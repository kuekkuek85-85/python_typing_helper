// 전역 변수
let practiceTimer = null;
let startTime = null;
let timeRemaining = 300; // 5분 = 300초
let isTimerRunning = false;
let currentText = '';
let userTypedText = '';

// 전역 상태 변수
let practiceCompleted = false;

// DOM 요소들
const elements = {
    timer: document.getElementById('timer'),
    wpm: document.getElementById('wpm'),
    accuracy: document.getElementById('accuracy'),
    score: document.getElementById('score'),
    practiceText: document.getElementById('practiceText'),
    userInput: document.getElementById('userInput'),
    startBtn: document.getElementById('startBtn'),
    resetBtn: document.getElementById('resetBtn'),
    teacherLoginBtn: document.getElementById('teacherLoginBtn'),
    completeModal: document.getElementById('completeModal'),
    finalWpm: document.getElementById('finalWpm'),
    finalAccuracy: document.getElementById('finalAccuracy'),
    finalScore: document.getElementById('finalScore'),
    studentId: document.getElementById('studentId'),
    studentIdError: document.getElementById('studentIdError'),
    saveRecordBtn: document.getElementById('saveRecordBtn'),
    saveSuccessModal: document.getElementById('saveSuccessModal')
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    setupEventListeners();
});

function initializePage() {
    // 홈페이지인 경우
    if (!window.currentMode) {
        setupHomePageEvents();
        return;
    }
    
    // 연습 페이지인 경우
    if (window.currentMode) {
        loadPracticeText();
    }
}

function setupHomePageEvents() {
    // 교사 로그인 버튼 이벤트 (모달 표시)
    if (elements.teacherLoginBtn) {
        elements.teacherLoginBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('teacherLoginModal'));
            modal.show();
        });
    }
    
    // 모드 카드 호버 효과
    const modeCards = document.querySelectorAll('.mode-card');
    modeCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function setupEventListeners() {
    if (!window.currentMode) return;
    
    // 시작 버튼
    if (elements.startBtn) {
        elements.startBtn.addEventListener('click', startPractice);
    }
    
    // 리셋 버튼
    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', resetPractice);
    }
    
    // 입력 이벤트
    if (elements.userInput) {
        elements.userInput.addEventListener('input', handleUserInput);
        elements.userInput.addEventListener('keydown', handleKeyDown);
    }
    
    // 학생 ID 입력 검증
    if (elements.studentId) {
        elements.studentId.addEventListener('input', validateStudentId);
        elements.studentId.addEventListener('keypress', function(event) {
            if (event.key === 'Enter' && elements.saveRecordBtn && !elements.saveRecordBtn.disabled) {
                saveRecord();
            }
        });
    }
    
    // 저장 버튼
    if (elements.saveRecordBtn) {
        elements.saveRecordBtn.addEventListener('click', saveRecord);
    }
    
    // 교사 로그인 버튼
    if (elements.teacherLoginBtn) {
        elements.teacherLoginBtn.addEventListener('click', function() {
            alert('교사 관리자 기능은 향후 버전에서 제공됩니다.');
        });
    }
    
    // 가상 키보드 설정
    setupVirtualKeyboard();
}

function loadPracticeText() {
    if (!window.currentMode) {
        elements.practiceText.textContent = '연습 텍스트를 불러올 수 없습니다.';
        return;
    }
    
    // API에서 연습 텍스트 가져오기
    fetch(`/api/practice-text/${window.currentMode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentText = data.text;
                renderPracticeText();
            } else {
                elements.practiceText.textContent = '연습 텍스트를 불러올 수 없습니다.';
                console.error('API 오류:', data.error);
            }
        })
        .catch(error => {
            elements.practiceText.textContent = '연습 텍스트를 불러오는 중 오류가 발생했습니다.';
            console.error('네트워크 오류:', error);
        });
}

function renderPracticeText() {
    // 텍스트를 스팬으로 분할하여 하이라이트 가능하게 만들기
    elements.practiceText.innerHTML = '';
    for (let i = 0; i < currentText.length; i++) {
        const span = document.createElement('span');
        span.textContent = currentText[i];
        span.setAttribute('data-index', i);
        elements.practiceText.appendChild(span);
    }
    
    // 첫 번째 키 강조
    highlightNextKey();
}

function startPractice() {
    if (isTimerRunning) return;
    
    // 입력창 완전 초기화
    elements.userInput.value = '';
    userTypedText = '';
    
    // UI 상태 변경
    elements.startBtn.disabled = true;
    elements.userInput.disabled = false;
    elements.userInput.focus();
    
    // 커서를 맨 앞으로 이동
    elements.userInput.setSelectionRange(0, 0);
    
    // 타이머 시작
    startTime = Date.now();
    isTimerRunning = true;
    timeRemaining = 300; // 5분
    
    practiceTimer = setInterval(updateTimer, 1000);
    
    // 버튼 텍스트 변경
    elements.startBtn.innerHTML = '<i class="bi bi-clock"></i> 연습 중...';
}

function updateTimer() {
    if (timeRemaining <= 0) {
        endPractice();
        return;
    }
    
    timeRemaining--;
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    elements.timer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    // 마지막 10초일 때 타이머 색상 변경
    if (timeRemaining <= 10) {
        elements.timer.style.color = 'var(--bs-danger)';
    }
}

function handleUserInput() {
    userTypedText = elements.userInput.value;
    
    // 실시간 하이라이트 업데이트
    updateTextHighlight();
    
    // 실시간 통계 업데이트
    if (isTimerRunning) {
        updateStats();
    }
    
    // 다음 키 강조 업데이트
    highlightNextKey();
    
    // 텍스트 완료 확인 및 다음 텍스트 로드
    checkTextCompletion();
}

function handleKeyDown(event) {
    // 연습이 시작되지 않았다면 자동 시작
    if (!isTimerRunning && event.key.length === 1) {
        startPractice();
    }
}

function updateTextHighlight() {
    const spans = elements.practiceText.querySelectorAll('span');
    
    for (let i = 0; i < spans.length; i++) {
        const span = spans[i];
        span.className = ''; // 기존 클래스 제거
        
        if (i < userTypedText.length) {
            // 타이핑한 부분
            if (userTypedText[i] === currentText[i]) {
                span.classList.add('correct');
            } else {
                span.classList.add('incorrect');
            }
        } else if (i === userTypedText.length) {
            // 현재 타이핑 위치
            span.classList.add('current');
        }
    }
}

function updateStats() {
    const elapsedTime = (Date.now() - startTime) / 1000 / 60; // 분 단위
    const typedChars = userTypedText.length;
    const correctChars = getCorrectCharCount();
    
    // WPM 계산 (5글자 = 1단어)
    const wpm = Math.round((typedChars / 5) / elapsedTime) || 0;
    
    // 정확도 계산
    const accuracy = typedChars > 0 ? Math.round((correctChars / typedChars) * 100) : 100;
    
    // 점수 계산
    const score = Math.round(Math.max(0, wpm) * Math.pow(accuracy / 100, 2) * 100);
    
    // UI 업데이트
    elements.wpm.textContent = wpm;
    elements.accuracy.textContent = `${accuracy}%`;
    elements.score.textContent = score;
}

function getCorrectCharCount() {
    let correctCount = 0;
    for (let i = 0; i < userTypedText.length && i < currentText.length; i++) {
        if (userTypedText[i] === currentText[i]) {
            correctCount++;
        }
    }
    return correctCount;
}

function endPractice() {
    // 타이머 정리
    if (practiceTimer) {
        clearInterval(practiceTimer);
        practiceTimer = null;
    }
    
    isTimerRunning = false;
    practiceCompleted = true;
    elements.userInput.disabled = true;
    elements.timer.textContent = '0:00';
    elements.timer.style.color = 'var(--bs-danger)';
    
    // 최종 통계 계산
    updateStats();
    
    // 완료 모달 표시
    showCompleteModal();
}

function showCompleteModal() {
    if (!elements.completeModal) return;
    
    // 최종 점수를 모달에 표시
    if (elements.finalWpm) elements.finalWpm.textContent = elements.wpm.textContent;
    if (elements.finalAccuracy) elements.finalAccuracy.textContent = elements.accuracy.textContent;
    if (elements.finalScore) elements.finalScore.textContent = elements.score.textContent;
    
    const modal = new bootstrap.Modal(elements.completeModal);
    modal.show();
}

function resetPractice() {
    // 타이머 정리
    if (practiceTimer) {
        clearInterval(practiceTimer);
        practiceTimer = null;
    }
    
    // 상태 초기화
    isTimerRunning = false;
    timeRemaining = 300;
    userTypedText = '';
    startTime = null;
    
    // UI 초기화
    elements.timer.textContent = '5:00';
    elements.timer.style.color = '';
    elements.wpm.textContent = '0';
    elements.accuracy.textContent = '100%';
    elements.score.textContent = '0';
    
    // 입력창 완전 초기화
    elements.userInput.value = '';
    elements.userInput.disabled = true;
    elements.startBtn.disabled = false;
    elements.startBtn.innerHTML = '<i class="bi bi-play-fill"></i> 연습 시작';
    
    // 새로운 연습 텍스트 로드
    loadPracticeText();
}

// 학생 ID 검증 함수
function validateStudentId() {
    if (!elements.studentId || !elements.studentIdError || !elements.saveRecordBtn) return;
    
    const studentId = elements.studentId.value.trim();
    const pattern = /^\d{5}\s[가-힣]{2,4}$/;
    
    if (studentId === '') {
        elements.studentIdError.style.display = 'none';
        elements.saveRecordBtn.disabled = true;
        return;
    }
    
    if (pattern.test(studentId)) {
        elements.studentIdError.style.display = 'none';
        elements.studentId.classList.remove('is-invalid');
        elements.studentId.classList.add('is-valid');
        elements.saveRecordBtn.disabled = false;
    } else {
        elements.studentIdError.textContent = '형식이 올바르지 않습니다. (예: 10218 홍길동)';
        elements.studentIdError.style.display = 'block';
        elements.studentId.classList.remove('is-valid');
        elements.studentId.classList.add('is-invalid');
        elements.saveRecordBtn.disabled = true;
    }
}

// 기록 저장 함수
function saveRecord() {
    if (!practiceCompleted || !elements.studentId || !elements.saveRecordBtn) return;
    
    const studentId = elements.studentId.value.trim();
    const pattern = /^\d{5}\s[가-힣]{2,4}$/;
    
    if (!pattern.test(studentId)) {
        alert('학번과 이름을 올바른 형식으로 입력해주세요.');
        return;
    }
    
    // 버튼 상태 변경
    elements.saveRecordBtn.disabled = true;
    elements.saveRecordBtn.innerHTML = '<i class="bi bi-hourglass"></i> 저장 중...';
    
    // 저장할 데이터 준비
    const recordData = {
        student_id: studentId,
        mode: window.currentMode,
        wpm: parseInt(elements.wpm.textContent) || 0,
        accuracy: parseFloat(elements.accuracy.textContent.replace('%', '')) || 0,
        score: parseInt(elements.score.textContent) || 0,
        duration_sec: 300 // 5분 완료
    };
    
    // API로 저장 요청
    fetch('/api/records', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(recordData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 성공 모달 표시
            const completeModal = bootstrap.Modal.getInstance(elements.completeModal);
            if (completeModal) {
                completeModal.hide();
            }
            
            if (elements.saveSuccessModal) {
                const successModal = new bootstrap.Modal(elements.saveSuccessModal);
                successModal.show();
            } else {
                alert('기록이 성공적으로 저장되었습니다!');
            }
        } else {
            throw new Error(data.error || '저장에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('저장 오류:', error);
        alert(`저장 실패: ${error.message}`);
        
        // 버튼 상태 복원
        elements.saveRecordBtn.disabled = false;
        elements.saveRecordBtn.innerHTML = '<i class="bi bi-save"></i> 기록 저장';
    });
}

// 유틸리티 함수들
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// 가상 키보드 설정 함수
function setupVirtualKeyboard() {
    const keys = document.querySelectorAll('.key');
    keys.forEach(key => {
        key.addEventListener('click', function() {
            // 가상 키보드 클릭 시 해당 문자를 입력창에 추가
            if (elements.userInput && !elements.userInput.disabled) {
                const keyValue = this.dataset.key;
                if (keyValue === ' ') {
                    elements.userInput.value += ' ';
                } else if (keyValue === 'Backspace') {
                    elements.userInput.value = elements.userInput.value.slice(0, -1);
                } else if (keyValue === 'Enter') {
                    elements.userInput.value += '\n';
                } else if (keyValue === 'Tab') {
                    elements.userInput.value += '\t';
                } else if (keyValue.length === 1) {
                    elements.userInput.value += keyValue;
                }
                
                // 키 애니메이션 효과
                animateKey(this);
                
                // input 이벤트 발생
                elements.userInput.dispatchEvent(new Event('input'));
                elements.userInput.focus();
            }
        });
    });
}

// 키 애니메이션 함수
function animateKey(keyElement) {
    keyElement.classList.add('active');
    setTimeout(() => {
        keyElement.classList.remove('active');
    }, 200);
}

// 다음에 눌러야 할 키 강조
function highlightNextKey() {
    // 모든 키의 강조 효과 제거
    document.querySelectorAll('.key').forEach(key => {
        key.classList.remove('next-key');
    });
    
    if (!currentText || userTypedText.length >= currentText.length) return;
    
    const nextChar = currentText[userTypedText.length];
    const targetKey = findKeyForCharacter(nextChar);
    
    if (targetKey) {
        targetKey.classList.add('next-key');
        
        // 특수문자인 경우 Shift 키도 강조
        if (isShiftRequired(nextChar)) {
            document.querySelectorAll('.key[data-key="Shift"]').forEach(shiftKey => {
                shiftKey.classList.add('next-key');
            });
        }
    }
}

// Shift 키가 필요한 문자인지 확인
function isShiftRequired(char) {
    const shiftChars = '!@#$%^&*()_+{}|:"<>?~ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    return shiftChars.includes(char);
}

// 문자에 해당하는 키 찾기
function findKeyForCharacter(char) {
    const keys = document.querySelectorAll('.key');
    
    // 공백 처리
    if (char === ' ') {
        return document.querySelector('.key[data-key=" "]');
    }
    
    // 엔터 처리
    if (char === '\n') {
        return document.querySelector('.key[data-key="Enter"]');
    }
    
    // 탭 처리
    if (char === '\t') {
        return document.querySelector('.key[data-key="Tab"]');
    }
    
    // 특수문자 처리 (Shift + 숫자 조합)
    const shiftNumberMap = {
        '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
        '^': '6', '&': '7', '*': '8', '(': '9', ')': '0'
    };
    
    if (shiftNumberMap[char]) {
        return document.querySelector(`.key[data-key="${shiftNumberMap[char]}"]`);
    }
    
    // 기타 특수문자 처리 (Shift + 기타 키 조합)
    const shiftSymbolMap = {
        '~': '`', '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
        ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
    };
    
    if (shiftSymbolMap[char]) {
        return document.querySelector(`.key[data-key="${shiftSymbolMap[char]}"]`);
    }
    
    // 일반 문자 처리 (대소문자 구분 없이)
    for (let key of keys) {
        const keyValue = key.dataset.key;
        if (keyValue && keyValue.toLowerCase() === char.toLowerCase()) {
            return key;
        }
    }
    
    return null;
}

// 실제 키보드 입력 시 애니메이션
function handleKeyPress(event) {
    const pressedChar = event.key;
    const targetKey = findKeyForCharacter(pressedChar);
    
    if (targetKey) {
        animateKey(targetKey);
    }
}

// 텍스트 완료 확인 및 다음 텍스트 로드
function checkTextCompletion() {
    if (!currentText || !isTimerRunning) return;
    
    // 입력한 텍스트 길이가 현재 텍스트 길이와 같거나 크면 다음 텍스트로 넘어감
    if (userTypedText.length >= currentText.length) {
        // 입력창 완전 클리어 및 커서 위치 초기화
        elements.userInput.value = '';
        userTypedText = '';
        elements.userInput.setSelectionRange(0, 0);
        
        // 새로운 텍스트 로드
        loadNextPracticeText();
    }
}

// 다음 연습 텍스트 로드
function loadNextPracticeText() {
    if (!window.currentMode) return;
    
    // 로딩 표시
    elements.practiceText.textContent = '다음 텍스트를 불러오는 중...';
    
    // API에서 새로운 연습 텍스트 가져오기
    fetch(`/api/practice-text/${window.currentMode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentText = data.text;
                renderPracticeText();
            } else {
                elements.practiceText.textContent = '다음 텍스트를 불러올 수 없습니다.';
                console.error('API 오류:', data.error);
            }
        })
        .catch(error => {
            elements.practiceText.textContent = '텍스트를 불러오는 중 오류가 발생했습니다.';
            console.error('네트워크 오류:', error);
        });
}

// 키보드 단축키 지원
document.addEventListener('keydown', function(event) {
    // 키보드 애니메이션 (연습 중일 때만)
    if (isTimerRunning && elements.userInput && elements.userInput === document.activeElement) {
        handleKeyPress(event);
    }
    
    // Ctrl+R 또는 F5로 리셋 (기본 새로고침 방지)
    if ((event.ctrlKey && event.key === 'r') || event.key === 'F5') {
        if (window.currentMode) {
            event.preventDefault();
            resetPractice();
        }
    }
    
    // ESC로 홈으로 이동
    if (event.key === 'Escape' && window.currentMode) {
        if (confirm('연습을 중단하고 홈으로 이동하시겠습니까?')) {
            window.location.href = '/';
        }
    }
});
