// 연습 페이지 JavaScript

// 전역 변수
let currentMode = null;
let currentText = '';
let userInput = '';
let startTime = null;
let endTime = null;
let timerInterval = null;
let remainingTime = 300; // 5분 = 300초
let isRunning = false;
let isCompleted = false;

// 타이핑 통계
let totalCharacters = 0;
let correctCharacters = 0;
let errors = 0;

// 키보드 관련
let isShiftPressed = false;
let isCapsLockOn = false;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializePracticePage();
});

// 연습 페이지 초기화
function initializePracticePage() {
    // URL에서 모드 가져오기
    currentMode = Utils.getUrlParameter('mode') || '자리';
    
    // 모드 정보 설정
    setupModeInfo();
    
    // 연습 텍스트 로드
    loadPracticeText();
    
    // 이벤트 리스너 설정
    setupPracticeEventListeners();
    
    // 초기 상태 설정
    resetPractice();
}

// 모드 정보 설정
function setupModeInfo() {
    const modeInfo = PRACTICE_MODES[currentMode];
    if (!modeInfo) {
        alert('잘못된 연습 모드입니다.');
        window.location.href = 'index.html';
        return;
    }

    // 페이지 제목 업데이트
    document.title = `${modeInfo.title} - 파이썬 타자 도우미`;
    document.getElementById('page-title').textContent = `${modeInfo.title} - 파이썬 타자 도우미`;
    
    // 모드 배지 업데이트
    const modeBadge = document.getElementById('mode-badge');
    if (modeBadge) {
        modeBadge.innerHTML = `${modeInfo.icon} ${modeInfo.title}`;
        modeBadge.className = `badge bg-${modeInfo.color} me-3`;
    }
    
    // 연습 제목 업데이트
    const practiceTitle = document.getElementById('practice-title');
    if (practiceTitle) {
        practiceTitle.innerHTML = `${modeInfo.icon} ${modeInfo.title}`;
    }
    
    // 연습 설명 업데이트
    const practiceDescription = document.getElementById('practice-description');
    if (practiceDescription) {
        practiceDescription.textContent = modeInfo.description;
    }
}

// 연습 텍스트 로드
function loadPracticeText() {
    const texts = PRACTICE_TEXTS[currentMode];
    if (!texts || texts.length === 0) {
        currentText = 'def hello_world():\n    print("Hello, Python!")';
    } else {
        // 랜덤하게 텍스트 선택
        const randomIndex = Math.floor(Math.random() * texts.length);
        currentText = texts[randomIndex];
    }
    
    displayPracticeText();
}

// 연습 텍스트 표시
function displayPracticeText() {
    const textContainer = document.getElementById('practiceText');
    if (!textContainer) return;
    
    // 모드에 따라 다른 스타일 적용
    if (currentMode === '자리') {
        // 자리 연습: 한 줄로 표시
        textContainer.innerHTML = `<div class="practice-line">${escapeHtml(currentText)}</div>`;
    } else {
        // 다른 모드: 여러 줄 가능
        const lines = currentText.split('\n');
        textContainer.innerHTML = lines.map(line => 
            `<div class="practice-line">${escapeHtml(line)}</div>`
        ).join('');
    }
}

// HTML 이스케이프
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 이벤트 리스너 설정
function setupPracticeEventListeners() {
    const userInputElement = document.getElementById('userInput');
    const startBtn = document.getElementById('startBtn');
    const resetBtn = document.getElementById('resetBtn');
    const studentIdInput = document.getElementById('studentId');
    const saveRecordBtn = document.getElementById('saveRecordBtn');

    // 시작 버튼
    if (startBtn) {
        startBtn.addEventListener('click', startPractice);
    }

    // 리셋 버튼
    if (resetBtn) {
        resetBtn.addEventListener('click', resetPractice);
    }

    // 사용자 입력
    if (userInputElement) {
        userInputElement.addEventListener('input', handleUserInput);
        userInputElement.addEventListener('keydown', handleKeyDown);
        userInputElement.addEventListener('paste', handlePaste);
    }

    // 학생 ID 입력 검증
    if (studentIdInput) {
        studentIdInput.addEventListener('input', validateStudentIdInput);
    }

    // 기록 저장 버튼
    if (saveRecordBtn) {
        saveRecordBtn.addEventListener('click', saveRecord);
    }

    // 키보드 이벤트 (전역)
    document.addEventListener('keydown', handleGlobalKeyDown);
    document.addEventListener('keyup', handleGlobalKeyUp);

    // 복사/붙여넣기 방지
    document.addEventListener('copy', preventCopyPaste);
    document.addEventListener('cut', preventCopyPaste);
}

// 연습 시작
function startPractice() {
    if (isRunning) return;
    
    isRunning = true;
    isCompleted = false;
    startTime = new Date();
    
    // UI 업데이트
    document.getElementById('startBtn').disabled = true;
    document.getElementById('userInput').disabled = false;
    document.getElementById('userInput').focus();
    
    // 타이머 시작
    startTimer();
    
    // 통계 초기화
    totalCharacters = 0;
    correctCharacters = 0;
    errors = 0;
    userInput = '';
    
    updateStats();
}

// 연습 리셋
function resetPractice() {
    isRunning = false;
    isCompleted = false;
    
    // 타이머 정지
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    
    remainingTime = 300;
    
    // UI 리셋
    document.getElementById('startBtn').disabled = false;
    document.getElementById('userInput').disabled = true;
    document.getElementById('userInput').value = '';
    document.getElementById('timer').textContent = '5:00';
    
    // 통계 리셋
    totalCharacters = 0;
    correctCharacters = 0;
    errors = 0;
    userInput = '';
    
    updateStats();
    
    // 새로운 텍스트 로드
    loadPracticeText();
    
    // 키보드 하이라이트 제거
    clearKeyboardHighlight();
}

// 타이머 시작
function startTimer() {
    timerInterval = setInterval(() => {
        remainingTime--;
        
        const minutes = Math.floor(remainingTime / 60);
        const seconds = remainingTime % 60;
        document.getElementById('timer').textContent = 
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (remainingTime <= 0) {
            completePractice();
        }
    }, 1000);
}

// 사용자 입력 처리
function handleUserInput(event) {
    if (!isRunning || isCompleted) return;
    
    userInput = event.target.value;
    
    // 텍스트 비교 및 하이라이트
    updateTextHighlight();
    
    // 통계 업데이트
    calculateStats();
    updateStats();
    
    // 다음 키 하이라이트
    highlightNextKey();
    
    // 완료 체크
    if (userInput.length >= currentText.length && userInput === currentText) {
        completePractice();
    }
}

// 키 다운 이벤트
function handleKeyDown(event) {
    // Shift 키 상태 추적
    if (event.key === 'Shift') {
        isShiftPressed = true;
        updateShiftKeyHighlight(true);
    }
    
    // CapsLock 상태 추적
    if (event.key === 'CapsLock') {
        isCapsLockOn = !isCapsLockOn;
        updateCapsLockDisplay();
    }
}

// 전역 키 이벤트
function handleGlobalKeyDown(event) {
    if (event.key === 'Shift') {
        isShiftPressed = true;
        updateShiftKeyHighlight(true);
    }
}

function handleGlobalKeyUp(event) {
    if (event.key === 'Shift') {
        isShiftPressed = false;
        updateShiftKeyHighlight(false);
    }
}

// 붙여넣기 방지
function handlePaste(event) {
    event.preventDefault();
    alert('복사/붙여넣기는 허용되지 않습니다.');
}

function preventCopyPaste(event) {
    event.preventDefault();
}

// 텍스트 하이라이트 업데이트
function updateTextHighlight() {
    const textContainer = document.getElementById('practiceText');
    if (!textContainer) return;
    
    let highlightedHtml = '';
    
    for (let i = 0; i < currentText.length; i++) {
        const char = currentText[i];
        
        if (i < userInput.length) {
            if (userInput[i] === char) {
                highlightedHtml += `<span class="char-correct">${escapeHtml(char)}</span>`;
            } else {
                highlightedHtml += `<span class="char-error">${escapeHtml(char)}</span>`;
            }
        } else if (i === userInput.length) {
            highlightedHtml += `<span class="char-current">${escapeHtml(char)}</span>`;
        } else {
            highlightedHtml += escapeHtml(char);
        }
    }
    
    if (currentMode === '자리') {
        textContainer.innerHTML = `<div class="practice-line">${highlightedHtml}</div>`;
    } else {
        const lines = highlightedHtml.split('\n');
        textContainer.innerHTML = lines.map(line => 
            `<div class="practice-line">${line}</div>`
        ).join('');
    }
}

// 통계 계산
function calculateStats() {
    totalCharacters = userInput.length;
    correctCharacters = 0;
    errors = 0;
    
    for (let i = 0; i < userInput.length; i++) {
        if (i < currentText.length && userInput[i] === currentText[i]) {
            correctCharacters++;
        } else {
            errors++;
        }
    }
}

// 통계 표시 업데이트
function updateStats() {
    const elapsedMinutes = startTime ? (new Date() - startTime) / 60000 : 0;
    
    // WPM 계산 (한국어 기준: 5글자 = 1단어)
    const wpm = elapsedMinutes > 0 ? Utils.calculateKoreanWPM(correctCharacters, elapsedMinutes) : 0;
    
    // 정확도 계산
    const accuracy = totalCharacters > 0 ? Math.round((correctCharacters / totalCharacters) * 100) : 100;
    
    // 점수 계산 (WPM * (정확도/100)^2 * 100)
    const score = Math.round(Math.max(0, wpm) * Math.pow(accuracy / 100, 2) * 100);
    
    // UI 업데이트
    document.getElementById('wpm').textContent = wpm;
    document.getElementById('accuracy').textContent = `${accuracy}%`;
    document.getElementById('score').textContent = score;
}

// 다음 키 하이라이트
function highlightNextKey() {
    clearKeyboardHighlight();
    
    if (userInput.length < currentText.length) {
        const nextChar = currentText[userInput.length];
        highlightKey(nextChar);
    }
}

// 키 하이라이트
function highlightKey(char) {
    const keyElement = document.querySelector(`[data-key="${char}"]`) || 
                     document.querySelector(`[data-key="${char.toLowerCase()}"]`);
    
    if (keyElement) {
        keyElement.classList.add('key-highlight');
    }
    
    // 대문자의 경우 Shift 키도 하이라이트
    if (char !== char.toLowerCase() && !isCapsLockOn) {
        updateShiftKeyHighlight(true);
    }
}

// 키보드 하이라이트 제거
function clearKeyboardHighlight() {
    document.querySelectorAll('.key-highlight').forEach(key => {
        key.classList.remove('key-highlight');
    });
    updateShiftKeyHighlight(false);
}

// Shift 키 하이라이트 업데이트
function updateShiftKeyHighlight(highlight) {
    document.querySelectorAll('[data-key="Shift"]').forEach(key => {
        if (highlight) {
            key.classList.add('key-highlight');
        } else {
            key.classList.remove('key-highlight');
        }
    });
}

// CapsLock 표시 업데이트
function updateCapsLockDisplay() {
    const capsKey = document.querySelector('[data-key="CapsLock"]');
    if (capsKey) {
        if (isCapsLockOn) {
            capsKey.classList.add('key-active');
        } else {
            capsKey.classList.remove('key-active');
        }
    }
    
    // 키보드 문자 업데이트
    document.querySelectorAll('.key-letter').forEach(letterSpan => {
        const key = letterSpan.parentElement;
        const char = key.dataset.key;
        if (char && char.length === 1 && /[a-z]/.test(char)) {
            letterSpan.textContent = isCapsLockOn ? char.toUpperCase() : char;
        }
    });
}

// 연습 완료
function completePractice() {
    if (isCompleted) return;
    
    isCompleted = true;
    isRunning = false;
    endTime = new Date();
    
    // 타이머 정지
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    
    // UI 업데이트
    document.getElementById('userInput').disabled = true;
    clearKeyboardHighlight();
    
    // 최종 통계 계산
    const duration = (endTime - startTime) / 1000; // 초
    const elapsedMinutes = duration / 60;
    const wpm = Utils.calculateKoreanWPM(correctCharacters, elapsedMinutes);
    const accuracy = totalCharacters > 0 ? Math.round((correctCharacters / totalCharacters) * 100) : 100;
    const score = Math.round(Math.max(0, wpm) * Math.pow(accuracy / 100, 2) * 100);
    
    // 완료 모달 표시
    showCompletionModal(wpm, accuracy, score, Math.round(duration));
}

// 완료 모달 표시
function showCompletionModal(wpm, accuracy, score, duration) {
    document.getElementById('finalWpm').textContent = wpm;
    document.getElementById('finalAccuracy').textContent = `${accuracy}%`;
    document.getElementById('finalScore').textContent = score;
    
    // 결과를 전역 변수에 저장 (저장 시 사용)
    window.practiceResult = {
        mode: currentMode,
        wpm: wpm,
        accuracy: accuracy,
        score: score,
        duration_sec: duration
    };
    
    const modal = new bootstrap.Modal(document.getElementById('completeModal'));
    modal.show();
}

// 학생 ID 입력 검증
function validateStudentIdInput() {
    const input = document.getElementById('studentId');
    const error = document.getElementById('studentIdError');
    const saveBtn = document.getElementById('saveRecordBtn');
    
    const isValid = Utils.validateStudentId(input.value);
    
    if (input.value.length > 0) {
        if (isValid) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            error.style.display = 'none';
            saveBtn.disabled = false;
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            error.textContent = '올바른 형식이 아닙니다. (예: 10218 홍길동)';
            error.style.display = 'block';
            saveBtn.disabled = true;
        }
    } else {
        input.classList.remove('is-valid', 'is-invalid');
        error.style.display = 'none';
        saveBtn.disabled = true;
    }
}

// 기록 저장
async function saveRecord() {
    const studentId = document.getElementById('studentId').value;
    
    if (!Utils.validateStudentId(studentId)) {
        alert('올바른 학번과 이름을 입력해주세요.');
        return;
    }
    
    if (!window.practiceResult) {
        alert('저장할 결과가 없습니다.');
        return;
    }
    
    try {
        const recordData = {
            ...window.practiceResult,
            student_id: studentId
        };
        
        document.getElementById('saveRecordBtn').disabled = true;
        document.getElementById('saveRecordBtn').innerHTML = '<i class="bi bi-spinner-border spinner-border-sm"></i> 저장 중...';
        
        await db.saveRecord(recordData);
        
        // 완료 모달 닫기
        const completeModal = bootstrap.Modal.getInstance(document.getElementById('completeModal'));
        completeModal.hide();
        
        // 성공 모달 표시
        const successModal = new bootstrap.Modal(document.getElementById('saveSuccessModal'));
        successModal.show();
        
    } catch (error) {
        console.error('기록 저장 실패:', error);
        alert('기록 저장에 실패했습니다. 네트워크 연결을 확인해주세요.');
        
        // 버튼 복원
        document.getElementById('saveRecordBtn').disabled = false;
        document.getElementById('saveRecordBtn').innerHTML = '<i class="bi bi-save"></i> 기록 저장';
    }
}