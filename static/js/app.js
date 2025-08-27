// 전역 변수
let practiceTimer = null;
let startTime = null;
let timeRemaining = 300; // 5분 = 300초
let isTimerRunning = false;
let currentText = '';
let userTypedText = '';
let lastTypedLength = 0; // 마지막으로 타이핑한 길이 추적

// 전역 상태 변수
let practiceCompleted = false;

// 진행률 기반 점수 누적을 위한 변수들
let accumulatedScore = 0; // 누적된 총 점수
let completedWords = []; // 완료된 단어들의 정보
let lastScoredWordIndex = -1; // 마지막으로 점수를 준 단어 인덱스

// 키보드 상태 변수들
let isCapsLockOn = false; // Caps Lock 상태 추적

// 효과음을 위한 Audio Context
let audioContext = null;

// 효과음 초기화
function initAudio() {
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    } catch (error) {
        console.log('오디오 컨텍스트를 생성할 수 없습니다:', error);
    }
}

// 맞을 때 효과음 (짧은 성공음)
function playCorrectSound() {
    if (!audioContext) return;
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // 밝은 톤의 짧은 음
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(1000, audioContext.currentTime + 0.1);
    
    // 볼륨 설정 (낮게)
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);
}

// 틀릴 때 효과음 (짧은 에러음)
function playIncorrectSound() {
    if (!audioContext) return;
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // 낮은 톤의 짧은 음
    oscillator.frequency.setValueAtTime(200, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(150, audioContext.currentTime + 0.15);
    
    // 볼륨 설정 (낮게)
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.08, audioContext.currentTime + 0.01);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.15);
}

// 연습 완료 효과음 (승리음)
function playCompleteSound() {
    if (!audioContext) return;
    
    // 3단계 상승하는 멜로디 음
    const frequencies = [523, 659, 784]; // C5, E5, G5
    
    frequencies.forEach((freq, index) => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        const startTime = audioContext.currentTime + (index * 0.15);
        
        oscillator.frequency.setValueAtTime(freq, startTime);
        
        // 볼륨 설정
        gainNode.gain.setValueAtTime(0, startTime);
        gainNode.gain.linearRampToValueAtTime(0.15, startTime + 0.05);
        gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 0.2);
        
        oscillator.start(startTime);
        oscillator.stop(startTime + 0.2);
    });
}

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
    initAudio();
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
                // 자리 연습의 경우 줄바꿈 문자 제거
                if (window.currentMode === '자리') {
                    currentText = data.text.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
                } else {
                    currentText = data.text;
                }
                
                // 새로운 텍스트가 로드될 때 점수 변수 초기화
                accumulatedScore = 0;
                completedWords = [];
                lastScoredWordIndex = -1;
                
                // UI 점수 표시도 초기화
                if (elements.score) elements.score.textContent = '0';
                

                
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
    // 자리 연습의 경우 한 줄로 강제 처리
    if (window.currentMode === '자리') {
        // 모든 줄바꿈 제거하고 연속된 공백을 하나로 정리
        currentText = currentText.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

    }
    
    // 텍스트를 스팬으로 분할하여 하이라이트 가능하게 만들기
    elements.practiceText.innerHTML = '';
    for (let i = 0; i < currentText.length; i++) {
        const span = document.createElement('span');
        span.textContent = currentText[i];
        span.setAttribute('data-index', i);
        elements.practiceText.appendChild(span);
    }
    
    // 자리 연습의 경우 추가 스타일 적용
    if (window.currentMode === '자리') {
        elements.practiceText.style.whiteSpace = 'nowrap';
        elements.practiceText.style.display = 'inline-block';
        elements.practiceText.style.width = 'max-content';
    }
    
    // 첫 번째 키 강조
    highlightNextKey();
}

function startPractice() {
    if (isTimerRunning) return;
    
    // 한영 키 확인 메시지 표시
    showLanguageCheckDialog();
}

// 한영 키 확인 대화상자 표시
function showLanguageCheckDialog() {
    // 기존 대화상자가 있으면 제거
    const existingDialog = document.getElementById('languageCheckDialog');
    if (existingDialog) {
        existingDialog.remove();
    }
    
    // 대화상자 생성
    const dialog = document.createElement('div');
    dialog.id = 'languageCheckDialog';
    dialog.className = 'modal fade show';
    dialog.style.display = 'block';
    dialog.style.backgroundColor = 'rgba(0,0,0,0.5)';
    dialog.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="bi bi-keyboard me-2"></i>
                        한영 키 확인
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <div class="mb-3">
                        <i class="bi bi-exclamation-triangle-fill text-warning" style="font-size: 3rem;"></i>
                    </div>
                    <h6 class="mb-3">연습을 시작하기 전에 입력 모드를 확인해주세요!</h6>
                    <p class="mb-3">파이썬 타자 연습은 <strong>영문 입력 모드</strong>에서 진행됩니다.</p>
                    <div class="alert alert-info mb-3">
                        <strong>한영 키</strong> 또는 <strong>Alt + 한영 키</strong>를 눌러서<br>
                        영문 입력 모드로 변경해주세요.
                    </div>
                    <!-- 한영 키 전환을 위한 숨겨진 입력 필드 -->
                    <input type="text" id="langCheckInput" style="position: absolute; left: -9999px; opacity: 0;" 
                           placeholder="한영키 테스트" autocomplete="off">
                    <div class="mb-3">
                        <small class="text-muted">
                            💡 한영 키를 눌러서 입력 모드를 변경하세요.<br>
                            아래 입력창에 영문으로 타이핑되면 준비 완료입니다.
                        </small>
                    </div>
                    <div class="mb-3">
                        <input type="text" id="testInput" class="form-control" 
                               placeholder="여기에 영문으로 타이핑해보세요 (예: test)" 
                               maxlength="20" autocomplete="off">
                    </div>
                    <p class="text-muted small">영문 입력 모드가 준비되면 '연습 시작' 버튼을 눌러주세요.</p>
                </div>
                <div class="modal-footer justify-content-center">
                    <button type="button" class="btn btn-secondary" onclick="closeLangCheckDialog()">
                        <i class="bi bi-x-lg"></i>
                        취소
                    </button>
                    <button type="button" class="btn btn-success" onclick="confirmLanguageAndStart()">
                        <i class="bi bi-play-fill"></i>
                        연습 시작
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // 대화상자를 페이지에 추가
    document.body.appendChild(dialog);
    
    // 테스트 입력창에 포커스 및 이벤트 리스너 추가
    setTimeout(() => {
        const testInput = document.getElementById('testInput');
        if (testInput) {
            testInput.focus();
            
            // 한글 입력 감지 및 피드백
            testInput.addEventListener('input', function() {
                const koreanRegex = /[ㄱ-ㅎㅏ-ㅣ가-힣]/;
                const hasKorean = koreanRegex.test(this.value);
                
                if (hasKorean) {
                    this.style.borderColor = '#dc3545';
                    this.style.backgroundColor = '#f8d7da';
                    this.placeholder = '한글이 입력되었습니다. 한영키를 눌러주세요!';
                } else if (this.value.length > 0) {
                    this.style.borderColor = '#198754';
                    this.style.backgroundColor = '#d1e7dd';
                    this.placeholder = '영문 입력 모드 준비 완료!';
                } else {
                    this.style.borderColor = '';
                    this.style.backgroundColor = '';
                    this.placeholder = '여기에 영문으로 타이핑해보세요 (예: test)';
                }
            });
            
            // IME 상태 변화 감지
            testInput.addEventListener('compositionstart', function() {
                this.style.borderColor = '#ffc107';
                this.style.backgroundColor = '#fff3cd';
                this.placeholder = '한글 입력 모드입니다. 한영키를 눌러주세요!';
            });
            
            testInput.addEventListener('compositionend', function() {
                // composition 종료 후 다시 검사
                setTimeout(() => {
                    this.dispatchEvent(new Event('input'));
                }, 10);
            });
        }
    }, 100);
}

// 한영 키 확인 대화상자 닫기
function closeLangCheckDialog() {
    const dialog = document.getElementById('languageCheckDialog');
    if (dialog) {
        dialog.remove();
    }
}

// 언어 확인 후 연습 시작
function confirmLanguageAndStart() {
    closeLangCheckDialog();
    actuallyStartPractice();
}

// 실제 연습 시작 함수
function actuallyStartPractice() {
    if (isTimerRunning) return;
    
    // 입력창 완전 초기화
    elements.userInput.value = '';
    userTypedText = '';
    lastTypedLength = 0;
    
    // 진행률 기반 점수 누적 변수 강제 초기화
    accumulatedScore = 0;
    completedWords = [];
    lastScoredWordIndex = -1;
    

    
    // UI 상태 변경
    elements.startBtn.disabled = true;
    elements.userInput.disabled = false;
    elements.userInput.focus();
    
    // 커서를 맨 앞으로 이동
    elements.userInput.setSelectionRange(0, 0);
    
    // IME를 영어로 설정 (한글 입력 모드를 영문 입력 모드로 전환)
    setInputModeToEnglish();
    
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
    // 첫 번째 키 입력 시 오디오 컨텍스트 활성화
    if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume();
    }
    
    // Caps Lock 키 처리
    if (event.key === 'CapsLock') {
        event.preventDefault(); // 기본 동작 방지
        toggleCapsLock();
        return;
    }
    
    // 연습이 시작되지 않았다면 한영 키 확인 대화상자 표시
    if (!isTimerRunning && event.key.length === 1) {
        showLanguageCheckDialog();
    }
}

function updateTextHighlight() {
    const spans = elements.practiceText.querySelectorAll('span');
    
    // 새로 타이핑된 문자가 있는 경우 효과음 재생
    if (userTypedText.length > lastTypedLength) {
        const newCharIndex = userTypedText.length - 1;
        if (newCharIndex >= 0 && newCharIndex < currentText.length) {
            if (userTypedText[newCharIndex] === currentText[newCharIndex]) {
                playCorrectSound();
            } else {
                playIncorrectSound();
            }
        }
    }
    
    // 마지막 타이핑 길이 업데이트
    lastTypedLength = userTypedText.length;
    
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
    
    // 분당 타자 수 계산 (정확한 글자 수 기준)
    // elapsedTime이 0보다 클 때만 계산하고, 최소 0.1분(6초) 이상일 때 의미있는 값
    const wpm = elapsedTime > 0.1 ? Math.round(correctChars / elapsedTime) : 0;
    
    // 정확도 계산
    const accuracy = typedChars > 0 ? Math.round((correctChars / typedChars) * 100) : 100;
    
    // 진행률 기반 점수 계산 (단어 단위로)
    calculateProgressScore();
    
    // UI 업데이트
    elements.wpm.textContent = wpm;
    elements.accuracy.textContent = `${accuracy}%`;
    elements.score.textContent = accumulatedScore;
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

// 완성된 정확한 단어 수 계산
function getCompletedWordsCount() {
    if (!currentText || !userTypedText) return 0;
    
    const words = currentText.split(' ').filter(word => word.trim() !== '');
    let completedWords = 0;
    let charIndex = 0;
    
    for (let wordIndex = 0; wordIndex < words.length; wordIndex++) {
        const word = words[wordIndex];
        let isWordCorrect = true;
        
        // 단어의 각 글자를 확인
        for (let i = 0; i < word.length; i++) {
            if (charIndex >= userTypedText.length || 
                userTypedText[charIndex] !== currentText[charIndex]) {
                isWordCorrect = false;
                break;
            }
            charIndex++;
        }
        
        // 단어가 완전히 정확하게 입력되었으면 카운트
        if (isWordCorrect && charIndex <= userTypedText.length) {
            completedWords++;
        } else {
            break; // 틀린 단어가 나오면 중단
        }
        
        // 단어 뒤 공백 건너뛰기
        if (charIndex < currentText.length && currentText[charIndex] === ' ') {
            if (charIndex >= userTypedText.length || userTypedText[charIndex] !== ' ') {
                break; // 공백도 정확해야 함
            }
            charIndex++;
        }
    }
    
    return completedWords;
}

// 단어 단위 진행률 기반 점수 계산
function calculateProgressScore() {
    if (!currentText || !userTypedText) return;
    
    // 텍스트를 단어 단위로 분할 (공백 기준) 및 빈 문자열 제거
    const words = currentText.split(' ').filter(word => word.trim() !== '');
    

    
    for (let wordIndex = 0; wordIndex < words.length; wordIndex++) {
        const word = words[wordIndex];
        
        // 이미 점수를 받은 단어는 건너뛰기
        if (wordIndex <= lastScoredWordIndex) continue;
        
        // 현재 단어의 위치를 텍스트에서 찾기
        let searchStartIndex = 0;
        for (let i = 0; i < wordIndex; i++) {
            const prevWordIndex = currentText.indexOf(words[i], searchStartIndex);
            if (prevWordIndex !== -1) {
                searchStartIndex = prevWordIndex + words[i].length + 1; // +1 for space
            }
        }
        
        const wordStartIndex = currentText.indexOf(word, searchStartIndex);
        if (wordStartIndex === -1) continue; // 단어를 찾을 수 없으면 건너뛰기
        
        const wordEndIndex = wordStartIndex + word.length;
        const isLastWord = wordIndex === words.length - 1;
        
        // 단어 완료 조건 확인
        let wordComplete = false;
        
        if (isLastWord) {
            // 마지막 단어: 정확히 타이핑되면 완료
            wordComplete = (userTypedText.length >= wordEndIndex && 
                           userTypedText.substring(wordStartIndex, wordEndIndex) === word);
        } else {
            // 마지막 단어가 아님: 단어 + 공백까지 타이핑되면 완료
            wordComplete = (userTypedText.length > wordEndIndex && 
                           userTypedText.substring(wordStartIndex, wordEndIndex) === word &&
                           userTypedText[wordEndIndex] === ' ');
        }
        
        if (wordComplete) {
            // 단어별 점수 계산
            const wordScore = calculateWordScore(word, word);
            accumulatedScore += wordScore;
            
            // 완료된 단어 정보 저장
            completedWords.push({
                wordIndex: wordIndex,
                word: word,
                score: wordScore,
                completedAt: Date.now()
            });
            
            lastScoredWordIndex = wordIndex;
            console.log(`단어 "${word}" 완료! 점수: ${wordScore}, 총 누적: ${accumulatedScore}`);
        }
    }
}

// 개별 단어의 점수 계산 함수
function calculateWordScore(originalWord, typedWord) {
    if (!originalWord || originalWord.trim() === '') return 0;
    
    // 단어 길이에 비례하는 기본 점수
    const baseScore = originalWord.length * 3; // 글자당 3점
    
    // 정확도 계산
    let correctChars = 0;
    for (let i = 0; i < Math.min(originalWord.length, typedWord.length); i++) {
        if (originalWord[i] === typedWord[i]) {
            correctChars++;
        }
    }
    
    const accuracy = originalWord.length > 0 ? correctChars / originalWord.length : 0;
    
    // 정확도에 따른 점수 조정
    const finalScore = Math.round(baseScore * accuracy * accuracy); // 정확도 제곱으로 보너스
    
    return Math.max(1, finalScore); // 최소 1점
}

// 마지막 미완성 단어의 부분 점수 계산
function calculateFinalPartialScore() {
    if (!userTypedText || !currentText) return;
    
    const words = currentText.split(' ');
    let textIndex = 0;
    
    // 마지막으로 타이핑 중인 단어 찾기
    for (let wordIndex = 0; wordIndex < words.length; wordIndex++) {
        const word = words[wordIndex];
        
        // 이미 점수를 받은 단어는 건너뛰기
        if (wordIndex <= lastScoredWordIndex) {
            textIndex += word.length + 1;
            continue;
        }
        
        const wordStartIndex = textIndex;
        const wordEndIndex = textIndex + word.length;
        
        // 현재 타이핑 중인 단어가 있는지 확인
        if (userTypedText.length > wordStartIndex && userTypedText.length <= wordEndIndex) {
            const partialTypedWord = userTypedText.substring(wordStartIndex);
            
            // 부분 점수 계산
            let correctChars = 0;
            for (let i = 0; i < Math.min(word.length, partialTypedWord.length); i++) {
                if (word[i] === partialTypedWord[i]) {
                    correctChars++;
                }
            }
            
            if (correctChars > 0) {
                const partialScore = Math.round(correctChars * 1.5); // 글자당 1.5점 (부분 점수)
                accumulatedScore += partialScore;
                console.log(`미완성 단어 "${word}" 부분 점수: ${partialScore} (${correctChars}글자 정확)`);
            }
            break;
        }
        
        textIndex += word.length + 1;
    }
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
    
    // 마지막 미완성 단어도 점수 계산 (부분 점수)
    calculateFinalPartialScore();
    
    // 최종 통계 계산
    updateStats();
    
    console.log(`연습 완료! 최종 누적 점수: ${accumulatedScore}, 완료된 단어 수: ${completedWords.length}`);
    
    // 연습 완료 효과음 재생
    playCompleteSound();
    
    // 완료 모달 표시 (효과음 재생 후 약간 지연)
    setTimeout(() => {
        showCompleteModal();
    }, 200);
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
    lastTypedLength = 0;
    startTime = null;
    
    // 진행률 기반 점수 누적 변수 초기화
    accumulatedScore = 0;
    completedWords = [];
    lastScoredWordIndex = -1;
    
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

// IME를 영어로 설정하는 함수
function setInputModeToEnglish() {
    try {
        const input = elements.userInput;
        
        // 입력창에 영어 입력 모드 속성 설정
        input.lang = 'en';
        input.setAttribute('inputmode', 'latin');
        input.setAttribute('autocapitalize', 'off');
        input.setAttribute('autocorrect', 'off');
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('spellcheck', 'false');
        
        // compositionstart 이벤트로 한글 입력 감지 및 경고
        input.addEventListener('compositionstart', function(e) {
            // 한글 입력이 시작되면 사용자에게 알림
            showIMEWarning();
        });
        
        // compositionend 이벤트로 한글 입력 종료 처리
        input.addEventListener('compositionend', function(e) {
            // 한글 입력이 완료되면 입력값 제거
            setTimeout(() => {
                const koreanRegex = /[ㄱ-ㅎㅏ-ㅣ가-힣]/;
                if (koreanRegex.test(input.value)) {
                    input.value = userTypedText; // 이전 상태로 복원
                    showIMEWarning();
                }
            }, 10);
        });
        
    } catch (error) {
        console.log('IME 설정 실패:', error);
    }
}

// 한글 입력 모드 경고 표시
function showIMEWarning() {
    // 기존 경고가 있으면 제거
    const existingWarning = document.getElementById('imeWarning');
    if (existingWarning) {
        existingWarning.remove();
    }
    
    // 경고 메시지 생성
    const warning = document.createElement('div');
    warning.id = 'imeWarning';
    warning.className = 'alert alert-warning alert-dismissible fade show mt-2';
    warning.style.position = 'relative';
    warning.innerHTML = `
        <i class="bi bi-exclamation-triangle-fill me-2"></i>
        <strong>한영 전환 필요!</strong> 한글 입력 모드를 영문 입력 모드로 변경해주세요. (한영키 또는 Alt+한영키)
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 입력창 아래에 경고 표시
    const inputContainer = elements.userInput.parentElement;
    inputContainer.appendChild(warning);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (warning.parentElement) {
            warning.remove();
        }
    }, 3000);
}

// Caps Lock 상태 토글 함수
function toggleCapsLock() {
    isCapsLockOn = !isCapsLockOn;
    updateKeyboardDisplay();
    
    // Caps Lock 키에 시각적 효과 추가
    const capsLockKey = document.querySelector('.key[data-key="CapsLock"]');
    if (capsLockKey) {
        if (isCapsLockOn) {
            capsLockKey.classList.add('caps-lock-active');
        } else {
            capsLockKey.classList.remove('caps-lock-active');
        }
        animateKey(capsLockKey);
    }
}

// 키보드 표시 업데이트 (Caps Lock 상태에 따라)
function updateKeyboardDisplay() {
    const letterSpans = document.querySelectorAll('.key-letter');
    
    letterSpans.forEach(span => {
        const letter = span.textContent.toLowerCase();
        if (isCapsLockOn) {
            span.textContent = letter.toUpperCase();
        } else {
            span.textContent = letter.toLowerCase();
        }
    });
}

// 가상 키보드 설정 함수
function setupVirtualKeyboard() {
    const keys = document.querySelectorAll('.key');
    keys.forEach(key => {
        key.addEventListener('click', function() {
            const keyValue = this.dataset.key;
            
            // Caps Lock 키 처리
            if (keyValue === 'CapsLock') {
                toggleCapsLock();
                return;
            }
            
            // 가상 키보드 클릭 시 해당 문자를 입력창에 추가
            if (elements.userInput && !elements.userInput.disabled) {
                if (keyValue === ' ') {
                    elements.userInput.value += ' ';
                } else if (keyValue === 'Backspace') {
                    elements.userInput.value = elements.userInput.value.slice(0, -1);
                } else if (keyValue === 'Enter') {
                    elements.userInput.value += '\n';
                } else if (keyValue === 'Tab') {
                    elements.userInput.value += '\t';
                } else if (keyValue.length === 1) {
                    // 영문자인 경우 Caps Lock 상태에 따라 대소문자 결정
                    let inputChar = keyValue;
                    if (/[a-zA-Z]/.test(keyValue)) {
                        inputChar = isCapsLockOn ? keyValue.toUpperCase() : keyValue.toLowerCase();
                    }
                    elements.userInput.value += inputChar;
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
        
        // 특수문자인 경우 적절한 Shift 키만 강조
        if (isShiftRequired(nextChar)) {
            const appropriateShift = getAppropriateShift(nextChar);
            if (appropriateShift) {
                appropriateShift.classList.add('next-key');
            }
        }
    }
}

// Shift 키가 필요한 문자인지 확인
function isShiftRequired(char) {
    const shiftChars = '!@#$%^&*()_+{}|:"<>?~ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    return shiftChars.includes(char);
}

// 문자에 따라 적절한 Shift 키 선택 (키보드 자판 위치 기반)
function getAppropriateShift(char) {
    // 모든 Shift 키를 찾기
    const shiftKeys = document.querySelectorAll('.key[data-key="Shift"]');
    if (shiftKeys.length < 2) {
        return shiftKeys[0]; // Shift 키가 하나만 있으면 그것 사용
    }
    
    // 왼쪽 Shift를 사용해야 하는 문자들
    const leftShiftChars = '~!@#$%QWERTYASDFGZXCVB';
    
    // 나머지 Shift (오른쪽 Shift)를 사용해야 하는 문자들
    const rightShiftChars = '^&*()_+{}|:"<>?YUIOPHJKLNM';
    
    // 왼쪽 Shift 사용 (배열의 첫 번째)
    if (leftShiftChars.includes(char)) {
        return shiftKeys[0];
    }
    
    // 오른쪽 Shift 사용 (배열의 마지막)
    if (rightShiftChars.includes(char)) {
        return shiftKeys[1];
    }
    
    // 기본값: 왼쪽 Shift
    return shiftKeys[0];
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
        '~': '`', '_': '-', '=': '+', '{': '[', '}': ']', '|': '\\',
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
