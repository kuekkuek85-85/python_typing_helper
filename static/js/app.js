/**
 * 파이썬 타자 도우미 - 연습 화면 로직
 *
 * 화면에 보이는 점수는 서버가 저장하는 점수와 같은 공식을 쓴다.
 *   점수 = round(분당 타수 * (정확도/100)^2 * 100)
 * '적립 포인트'는 단어를 정확히 완성할 때마다 쌓이는 재미 요소로, 순위와는 무관하다.
 */
(function () {
    'use strict';

    // --- 상태 -------------------------------------------------------------
    var practiceSeconds = 300;
    var practiceTimer = null;
    var startTime = null;
    var timeRemaining = 0;
    var isTimerRunning = false;
    var practiceCompleted = false;

    var currentText = '';
    var userTypedText = '';
    var lastTypedLength = 0;

    // 지금까지 지나온 텍스트들의 누적 입력/정타 수 (현재 텍스트는 제외)
    var committedTypedChars = 0;
    var committedCorrectChars = 0;

    // 단어 완성 보너스(적립 포인트)
    var accumulatedPoints = 0;
    var lastScoredWordIndex = -1;

    var isCapsLockOn = false;
    var audioContext = null;

    // 키 입력 보고 버퍼 (매 글자마다 요청하지 않고 묶어서 보낸다)
    var KEYSTROKE_FLUSH_MS = 2000;
    var pendingKeystrokes = 0;
    var keystrokeFlushTimer = null;

    var elements = {};

    // --- 효과음 -----------------------------------------------------------
    function initAudio() {
        try {
            var AudioCtor = window.AudioContext || window.webkitAudioContext;
            if (AudioCtor) {
                audioContext = new AudioCtor();
            }
        } catch (error) {
            console.log('오디오 컨텍스트를 생성할 수 없습니다:', error);
        }
    }

    function playTone(startFrequency, endFrequency, peakGain, duration, offset) {
        if (!audioContext) return;

        var oscillator = audioContext.createOscillator();
        var gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        var begin = audioContext.currentTime + (offset || 0);
        oscillator.frequency.setValueAtTime(startFrequency, begin);
        if (endFrequency && endFrequency !== startFrequency) {
            oscillator.frequency.exponentialRampToValueAtTime(endFrequency, begin + duration);
        }

        gainNode.gain.setValueAtTime(0, begin);
        gainNode.gain.linearRampToValueAtTime(peakGain, begin + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.01, begin + duration);

        oscillator.start(begin);
        oscillator.stop(begin + duration);
    }

    function playCorrectSound() {
        playTone(800, 1000, 0.1, 0.1, 0);
    }

    function playIncorrectSound() {
        playTone(200, 150, 0.08, 0.15, 0);
    }

    function playCompleteSound() {
        [523, 659, 784].forEach(function (frequency, index) {
            playTone(frequency, frequency, 0.15, 0.2, index * 0.15);
        });
    }

    // --- 키 입력 보고 ------------------------------------------------------
    function countKeystroke() {
        if (!isTimerRunning) return;

        pendingKeystrokes += 1;
        if (!keystrokeFlushTimer) {
            keystrokeFlushTimer = window.setTimeout(flushKeystrokes, KEYSTROKE_FLUSH_MS);
        }
    }

    function flushKeystrokes() {
        if (keystrokeFlushTimer) {
            window.clearTimeout(keystrokeFlushTimer);
            keystrokeFlushTimer = null;
        }
        if (pendingKeystrokes <= 0) return;

        var count = pendingKeystrokes;
        pendingKeystrokes = 0;

        fetch('/api/keystroke', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count, practice_token: window.practiceToken })
        }).catch(function (error) {
            // 사용자 경험을 방해하지 않도록 조용히 넘어간다.
            console.log('키 입력 기록 실패:', error);
        });
    }

    // --- 초기화 -----------------------------------------------------------
    document.addEventListener('DOMContentLoaded', function () {
        if (!window.currentMode) {
            // 홈페이지에서는 순위표(leaderboard.js)만 동작한다.
            return;
        }

        elements = {
            timer: document.getElementById('timer'),
            wpm: document.getElementById('wpm'),
            accuracy: document.getElementById('accuracy'),
            score: document.getElementById('score'),
            points: document.getElementById('points'),
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

        practiceSeconds = parseInt(window.practiceSeconds, 10) || 300;
        timeRemaining = practiceSeconds;
        elements.timer.textContent = formatTime(practiceSeconds);

        setupEventListeners();
        guardAgainstKoreanInput();
        initAudio();
        loadPracticeText(true);
    });

    function setupEventListeners() {
        elements.startBtn.addEventListener('click', startPractice);
        elements.resetBtn.addEventListener('click', resetPractice);

        elements.userInput.addEventListener('input', handleUserInput);
        elements.userInput.addEventListener('keydown', handleKeyDown);

        elements.userInput.addEventListener('paste', function (event) {
            event.preventDefault();
            showInputWarning('붙여넣기 기능이 비활성화되었습니다!', '타자 연습에서는 직접 타이핑해야 합니다.');
        });

        elements.userInput.addEventListener('contextmenu', function (event) {
            event.preventDefault();
            showInputWarning('우클릭 메뉴가 비활성화되었습니다!', '타자 연습에서는 직접 타이핑해야 합니다.');
        });

        if (elements.studentId) {
            elements.studentId.addEventListener('input', validateStudentId);
            elements.studentId.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' && !elements.saveRecordBtn.disabled) {
                    event.preventDefault();
                    saveRecord();
                }
            });
        }

        if (elements.saveRecordBtn) {
            elements.saveRecordBtn.addEventListener('click', saveRecord);
        }

        if (elements.teacherLoginBtn) {
            elements.teacherLoginBtn.addEventListener('click', function () {
                alert('교사 관리자 기능은 향후 버전에서 제공됩니다.');
            });
        }

        setupVirtualKeyboard();

        document.addEventListener('keydown', handleGlobalKeyDown);

        // 연습 중 페이지를 떠날 때 남은 키 입력을 보고한다.
        window.addEventListener('pagehide', flushKeystrokes);
    }

    // --- 연습 텍스트 ------------------------------------------------------
    function loadPracticeText(isFirstLoad) {
        if (!isFirstLoad) {
            elements.practiceText.textContent = '다음 텍스트를 불러오는 중...';
        }

        fetch('/api/practice-text/' + encodeURIComponent(window.currentMode))
            .then(readJson)
            .then(function (data) {
                currentText = normalizeText(data.text);
                // 새 텍스트에서는 단어 점수 진행 상황을 반드시 초기화해야 한다.
                lastScoredWordIndex = -1;
                lastTypedLength = 0;
                renderPracticeText();
            })
            .catch(function (error) {
                elements.practiceText.textContent = '연습 텍스트를 불러올 수 없습니다. 페이지를 새로고침해주세요.';
                console.error('연습 텍스트 로딩 실패:', error);
            });
    }

    function normalizeText(text) {
        var value = String(text || '');
        if (window.currentMode === '자리') {
            // 자리 연습은 한 줄로 표시한다.
            return value.replace(/\s+/g, ' ').trim();
        }
        return value;
    }

    function renderPracticeText() {
        var fragment = document.createDocumentFragment();
        for (var i = 0; i < currentText.length; i++) {
            var span = document.createElement('span');
            span.textContent = currentText[i];
            span.setAttribute('data-index', i);
            fragment.appendChild(span);
        }

        elements.practiceText.innerHTML = '';
        elements.practiceText.appendChild(fragment);

        updateTextHighlight();
        highlightNextKey();
    }

    // --- 연습 시작/종료 ---------------------------------------------------
    function startPractice() {
        if (isTimerRunning) return;
        showLanguageCheckDialog();
    }

    function beginPractice() {
        if (isTimerRunning) return;

        elements.startBtn.disabled = true;
        elements.startBtn.innerHTML = '<i class="bi bi-hourglass"></i> 준비 중...';

        // 서버 측 타이머와 키 입력 집계를 시작한다.
        fetch('/api/practice/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ practice_token: window.practiceToken })
        })
            .then(readJson)
            .then(function (data) {
                practiceSeconds = parseInt(data.practice_seconds, 10) || practiceSeconds;
                runPracticeTimer();
            })
            .catch(function (error) {
                console.error('연습 시작 실패:', error);
                alert('연습을 시작할 수 없습니다: ' + error.message + '\n페이지를 새로고침해주세요.');
                elements.startBtn.disabled = false;
                elements.startBtn.innerHTML = '<i class="bi bi-play-fill"></i> 연습 시작';
            });
    }

    function runPracticeTimer() {
        resetStats();

        elements.userInput.value = '';
        elements.userInput.disabled = false;
        elements.userInput.focus();

        startTime = Date.now();
        isTimerRunning = true;
        practiceCompleted = false;
        timeRemaining = practiceSeconds;

        elements.timer.textContent = formatTime(timeRemaining);
        elements.timer.style.color = '';
        elements.startBtn.innerHTML = '<i class="bi bi-clock"></i> 연습 중...';

        practiceTimer = window.setInterval(updateTimer, 1000);
    }

    function updateTimer() {
        // 브라우저 탭이 비활성화되면 setInterval이 밀리므로 실제 경과 시간으로 계산한다.
        var elapsed = Math.floor((Date.now() - startTime) / 1000);
        timeRemaining = Math.max(0, practiceSeconds - elapsed);

        elements.timer.textContent = formatTime(timeRemaining);
        if (timeRemaining <= 10) {
            elements.timer.style.color = 'var(--bs-danger)';
        }

        if (timeRemaining <= 0) {
            endPractice();
        }
    }

    function endPractice() {
        if (practiceTimer) {
            window.clearInterval(practiceTimer);
            practiceTimer = null;
        }

        isTimerRunning = false;
        practiceCompleted = true;
        elements.userInput.disabled = true;
        elements.timer.textContent = '0:00';
        elements.timer.style.color = 'var(--bs-danger)';

        flushKeystrokes();
        updateStats();
        playCompleteSound();

        elements.startBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i> 연습 완료!';
        elements.startBtn.disabled = true;

        window.setTimeout(showCompleteModal, 200);
    }

    function resetPractice() {
        if (practiceTimer) {
            window.clearInterval(practiceTimer);
            practiceTimer = null;
        }

        flushKeystrokes();

        isTimerRunning = false;
        practiceCompleted = false;
        startTime = null;
        timeRemaining = practiceSeconds;

        resetStats();

        elements.timer.textContent = formatTime(practiceSeconds);
        elements.timer.style.color = '';
        elements.userInput.value = '';
        elements.userInput.disabled = true;
        elements.startBtn.disabled = false;
        elements.startBtn.innerHTML = '<i class="bi bi-play-fill"></i> 연습 시작';

        loadPracticeText(false);
    }

    function resetStats() {
        userTypedText = '';
        lastTypedLength = 0;
        committedTypedChars = 0;
        committedCorrectChars = 0;
        accumulatedPoints = 0;
        lastScoredWordIndex = -1;

        elements.wpm.textContent = '0';
        elements.accuracy.textContent = '100%';
        elements.score.textContent = '0';
        if (elements.points) elements.points.textContent = '0';
    }

    // --- 입력 처리 --------------------------------------------------------
    function handleUserInput() {
        userTypedText = elements.userInput.value;

        updateTextHighlight();
        if (isTimerRunning) {
            awardWordPoints();
            updateStats();
        }
        highlightNextKey();
        advanceTextIfCompleted();
    }

    function handleKeyDown(event) {
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }

        // 복사/붙여넣기 차단
        if ((event.ctrlKey || event.metaKey) && ['c', 'v', 'x'].indexOf(event.key.toLowerCase()) !== -1) {
            event.preventDefault();
            showInputWarning('복사/붙여넣기 기능이 비활성화되었습니다!', '타자 연습에서는 직접 타이핑해야 합니다.');
            return;
        }

        if (event.key === 'CapsLock') {
            event.preventDefault();
            toggleCapsLock();
            return;
        }

        if (isCountableKey(event)) {
            countKeystroke();
        }
    }

    function isCountableKey(event) {
        if (event.ctrlKey || event.altKey || event.metaKey) return false;
        return event.key.length === 1 ||
            event.key === 'Backspace' ||
            event.key === 'Enter' ||
            event.key === 'Tab';
    }

    function handleGlobalKeyDown(event) {
        // 가상 키보드 애니메이션 (연습 중, 입력창에 포커스가 있을 때만)
        if (isTimerRunning && document.activeElement === elements.userInput) {
            var targetKey = findKeyForCharacter(event.key);
            if (targetKey) animateKey(targetKey);
        }

        // 연습 중에만 새로고침을 가로채 '다시 시작'으로 연결한다.
        // (연습 전/후에는 평소처럼 새로고침이 동작해야 한다.)
        if (isTimerRunning && ((event.ctrlKey && event.key.toLowerCase() === 'r') || event.key === 'F5')) {
            event.preventDefault();
            resetPractice();
            return;
        }

        // 열린 모달에서는 ESC가 모달 닫기로 동작해야 한다.
        if (event.key === 'Escape' && !document.querySelector('.modal.show')) {
            if (window.confirm('연습을 중단하고 홈으로 이동하시겠습니까?')) {
                window.location.href = '/';
            }
        }
    }

    function updateTextHighlight() {
        var spans = elements.practiceText.querySelectorAll('span');

        // 새로 입력된 글자에 대한 효과음
        if (userTypedText.length > lastTypedLength) {
            var newCharIndex = userTypedText.length - 1;
            if (newCharIndex >= 0 && newCharIndex < currentText.length) {
                if (userTypedText[newCharIndex] === currentText[newCharIndex]) {
                    playCorrectSound();
                } else {
                    playIncorrectSound();
                }
            }
        }
        lastTypedLength = userTypedText.length;

        for (var i = 0; i < spans.length; i++) {
            var span = spans[i];
            span.className = '';
            if (i < userTypedText.length) {
                span.classList.add(userTypedText[i] === currentText[i] ? 'correct' : 'incorrect');
            } else if (i === userTypedText.length) {
                span.classList.add('current');
            }
        }
    }

    function countCorrectChars(typed, target) {
        var limit = Math.min(typed.length, target.length);
        var correct = 0;
        for (var i = 0; i < limit; i++) {
            if (typed[i] === target[i]) correct++;
        }
        return correct;
    }

    function updateStats() {
        var elapsedMinutes = startTime ? (Date.now() - startTime) / 1000 / 60 : 0;
        var typedChars = committedTypedChars + userTypedText.length;
        var correctChars = committedCorrectChars + countCorrectChars(userTypedText, currentText);

        // 분당 타수 = 정타 수 / 경과 분 (한국식 '타/분' 기준, 보정 없이 실제 값)
        var wpm = elapsedMinutes > 0 ? Math.round(correctChars / elapsedMinutes) : 0;
        var accuracy = typedChars > 0 ? Math.round((correctChars / typedChars) * 100) : 100;

        elements.wpm.textContent = wpm;
        elements.accuracy.textContent = accuracy + '%';
        elements.score.textContent = computeScore(wpm, accuracy);
        if (elements.points) elements.points.textContent = accumulatedPoints;
    }

    /**
     * 서버(scoring.compute_score)와 동일한 공식.
     *
     * Math.round는 0.5를 항상 올린다. 서버도 같은 규칙을 쓰도록
     * scoring.round_half_up()을 사용한다(파이썬 기본 round()는 짝수 쪽으로
     * 반올림해서 34타·정확도 75%처럼 정확히 .5가 되는 값에서 1점 어긋났다).
     * 한쪽 규칙만 바꾸면 화면 점수와 저장 점수가 달라진다.
     */
    function computeScore(wpm, accuracy) {
        var safeWpm = Math.max(0, wpm);
        var safeAccuracy = Math.min(100, Math.max(0, accuracy));
        return Math.round(safeWpm * Math.pow(safeAccuracy / 100, 2) * 100);
    }

    /** 공백으로 나눈 단어의 시작 위치를 순서대로 계산한다. */
    function splitWords(text) {
        var words = [];
        var index = 0;
        while (index < text.length) {
            if (text[index] === ' ') {
                index++;
                continue;
            }
            var end = text.indexOf(' ', index);
            if (end === -1) end = text.length;
            words.push({ value: text.slice(index, end), start: index, end: end });
            index = end;
        }
        return words;
    }

    /** 단어를 정확히 완성했을 때 적립 포인트를 준다. */
    function awardWordPoints() {
        if (!currentText || !userTypedText) return;

        var words = splitWords(currentText);
        for (var i = 0; i < words.length; i++) {
            if (i <= lastScoredWordIndex) continue;

            var word = words[i];
            var typedSlice = userTypedText.slice(word.start, word.end);
            if (typedSlice !== word.value) break;

            // 마지막 단어가 아니면 뒤따르는 공백까지 입력해야 완성으로 본다.
            var isLastWord = i === words.length - 1;
            if (!isLastWord && userTypedText.length <= word.end) break;

            accumulatedPoints += Math.max(1, word.value.length * 3);
            lastScoredWordIndex = i;
        }
    }

    /** 현재 텍스트를 끝까지 입력했으면 통계를 누적하고 다음 텍스트를 불러온다. */
    function advanceTextIfCompleted() {
        if (!currentText || !isTimerRunning) return;
        if (userTypedText.length < currentText.length) return;

        committedTypedChars += userTypedText.length;
        committedCorrectChars += countCorrectChars(userTypedText, currentText);

        elements.userInput.value = '';
        userTypedText = '';
        lastTypedLength = 0;

        loadPracticeText(false);
    }

    // --- 모달 표시 --------------------------------------------------------
    /**
     * Bootstrap JS가 있으면 그것으로, 없으면 직접 모달을 띄운다.
     * (학교 네트워크 문제로 스크립트를 못 불러와도 기록은 저장할 수 있어야 한다.)
     */
    function showModal(element) {
        if (window.bootstrap && window.bootstrap.Modal) {
            bootstrap.Modal.getOrCreateInstance(element).show();
            return;
        }
        element.classList.add('show');
        element.style.display = 'block';
        element.removeAttribute('aria-hidden');
        element.dispatchEvent(new Event('shown.bs.modal'));
    }

    function hideModal(element) {
        if (window.bootstrap && window.bootstrap.Modal) {
            var instance = bootstrap.Modal.getInstance(element);
            if (instance) instance.hide();
            return;
        }
        element.classList.remove('show');
        element.style.display = 'none';
    }

    // --- 완료 모달 / 저장 --------------------------------------------------
    function showCompleteModal() {
        if (!elements.completeModal) return;

        elements.finalWpm.textContent = elements.wpm.textContent;
        elements.finalAccuracy.textContent = elements.accuracy.textContent;
        elements.finalScore.textContent = elements.score.textContent;

        elements.completeModal.addEventListener('shown.bs.modal', function () {
            if (elements.studentId) elements.studentId.focus();
        }, { once: true });

        showModal(elements.completeModal);
    }

    var STUDENT_ID_PATTERN = /^\d{5}\s[가-힣]{2,4}$/;

    function validateStudentId() {
        var value = elements.studentId.value.trim();

        if (value === '') {
            elements.studentIdError.style.display = 'none';
            elements.studentId.classList.remove('is-valid', 'is-invalid');
            elements.saveRecordBtn.disabled = true;
            return;
        }

        if (STUDENT_ID_PATTERN.test(value)) {
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

    function saveRecord() {
        if (!practiceCompleted) return;

        var studentId = elements.studentId.value.trim();
        if (!STUDENT_ID_PATTERN.test(studentId)) {
            alert('학번과 이름을 올바른 형식으로 입력해주세요. (예: 10218 홍길동)');
            return;
        }

        elements.saveRecordBtn.disabled = true;
        elements.saveRecordBtn.innerHTML = '<i class="bi bi-hourglass"></i> 저장 중...';

        // 연습 시간과 점수는 서버가 계산한다. 여기서는 측정값만 보낸다.
        fetch('/api/records', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                wpm: parseInt(elements.wpm.textContent, 10) || 0,
                accuracy: parseFloat(elements.accuracy.textContent) || 0,
                practice_token: window.practiceToken
            })
        })
            .then(readJson)
            .then(function () {
                hideModal(elements.completeModal);

                if (elements.saveSuccessModal) {
                    showModal(elements.saveSuccessModal);
                } else {
                    alert('기록이 성공적으로 저장되었습니다!');
                }
            })
            .catch(function (error) {
                console.error('저장 오류:', error);
                alert('저장 실패: ' + error.message);
                elements.saveRecordBtn.disabled = false;
                elements.saveRecordBtn.innerHTML = '<i class="bi bi-save"></i> 기록 저장';
            });
    }

    /** 응답을 JSON으로 읽고, 실패 응답은 서버 메시지를 담은 Error로 바꾼다. */
    function readJson(response) {
        return response.json()
            .catch(function () {
                throw new Error('HTTP ' + response.status + ' - 서버 응답을 읽을 수 없습니다.');
            })
            .then(function (data) {
                if (!response.ok || data.success === false) {
                    throw new Error(data.error || ('HTTP ' + response.status));
                }
                return data;
            });
    }

    // --- 한/영 입력 안내 ---------------------------------------------------
    function showLanguageCheckDialog() {
        var existing = document.getElementById('languageCheckDialog');
        if (existing) existing.remove();

        var dialog = document.createElement('div');
        dialog.id = 'languageCheckDialog';
        dialog.className = 'modal fade show';
        dialog.style.display = 'block';
        dialog.style.backgroundColor = 'rgba(0,0,0,0.5)';
        dialog.innerHTML =
            '<div class="modal-dialog modal-dialog-centered">' +
            '  <div class="modal-content">' +
            '    <div class="modal-header">' +
            '      <h5 class="modal-title"><i class="bi bi-keyboard me-2"></i>한영 키 확인</h5>' +
            '    </div>' +
            '    <div class="modal-body text-center">' +
            '      <div class="mb-3"><i class="bi bi-exclamation-triangle-fill text-warning" style="font-size: 3rem;"></i></div>' +
            '      <h6 class="mb-3">연습을 시작하기 전에 입력 모드를 확인해주세요!</h6>' +
            '      <p class="mb-3">파이썬 타자 연습은 <strong>영문 입력 모드</strong>에서 진행됩니다.</p>' +
            '      <div class="alert alert-info mb-3"><strong>한영 키</strong> 또는 <strong>Alt + 한영 키</strong>를 눌러서<br>영문 입력 모드로 변경해주세요.</div>' +
            '      <div class="mb-3">' +
            '        <input type="text" id="testInput" class="form-control" placeholder="여기에 영문으로 타이핑해보세요 (예: test)" maxlength="20" autocomplete="off">' +
            '      </div>' +
            '      <p class="text-muted small">영문 입력 모드가 준비되면 \'연습 시작\' 버튼을 눌러주세요.</p>' +
            '    </div>' +
            '    <div class="modal-footer justify-content-center">' +
            '      <button type="button" class="btn btn-secondary" data-action="cancel"><i class="bi bi-x-lg"></i> 취소</button>' +
            '      <button type="button" class="btn btn-success" data-action="start"><i class="bi bi-play-fill"></i> 연습 시작</button>' +
            '    </div>' +
            '  </div>' +
            '</div>';

        document.body.appendChild(dialog);

        dialog.querySelector('[data-action="cancel"]').addEventListener('click', function () {
            dialog.remove();
        });
        dialog.querySelector('[data-action="start"]').addEventListener('click', function () {
            dialog.remove();
            beginPractice();
        });

        var testInput = dialog.querySelector('#testInput');
        testInput.addEventListener('input', function () {
            var hasKorean = /[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(this.value);
            if (hasKorean) {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else if (this.value.length > 0) {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
            } else {
                this.classList.remove('is-valid', 'is-invalid');
            }
        });

        window.setTimeout(function () { testInput.focus(); }, 100);
    }

    /** 입력창에 한글이 들어오면 되돌리고 안내한다. (리스너는 한 번만 등록) */
    function guardAgainstKoreanInput() {
        var input = elements.userInput;
        input.lang = 'en';
        input.setAttribute('inputmode', 'latin');
        input.setAttribute('autocapitalize', 'off');
        input.setAttribute('autocorrect', 'off');
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('spellcheck', 'false');

        input.addEventListener('compositionstart', function () {
            showInputWarning('한영 전환 필요!', '한글 입력 모드를 영문 입력 모드로 변경해주세요. (한영키 또는 Alt+한영키)');
        });

        input.addEventListener('compositionend', function () {
            window.setTimeout(function () {
                if (/[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(input.value)) {
                    input.value = userTypedText;
                    showInputWarning('한영 전환 필요!', '한글이 입력되었습니다. 한영키를 눌러주세요.');
                }
            }, 10);
        });
    }

    /** 입력창 아래에 경고를 띄운다(항상 한 개만 유지). */
    function showInputWarning(title, detail) {
        var existing = document.getElementById('inputWarning');
        if (existing) existing.remove();

        var warning = document.createElement('div');
        warning.id = 'inputWarning';
        warning.className = 'alert alert-warning alert-dismissible fade show mt-2';
        warning.setAttribute('role', 'alert');

        var icon = document.createElement('i');
        icon.className = 'bi bi-exclamation-triangle me-2';

        var strong = document.createElement('strong');
        strong.textContent = title;

        warning.appendChild(icon);
        warning.appendChild(strong);
        warning.appendChild(document.createTextNode(' ' + detail));

        var closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('aria-label', '닫기');
        closeButton.addEventListener('click', function () { warning.remove(); });
        warning.appendChild(closeButton);

        elements.userInput.parentNode.appendChild(warning);

        window.setTimeout(function () {
            if (warning.parentNode) warning.remove();
        }, 3000);
    }

    // --- 가상 키보드 ------------------------------------------------------
    function toggleCapsLock() {
        isCapsLockOn = !isCapsLockOn;

        document.querySelectorAll('.key-letter').forEach(function (span) {
            span.textContent = isCapsLockOn
                ? span.textContent.toUpperCase()
                : span.textContent.toLowerCase();
        });

        var capsLockKey = document.querySelector('.key[data-key="CapsLock"]');
        if (capsLockKey) {
            capsLockKey.classList.toggle('caps-lock-active', isCapsLockOn);
            animateKey(capsLockKey);
        }
    }

    function setupVirtualKeyboard() {
        document.querySelectorAll('.key').forEach(function (key) {
            key.addEventListener('click', function () {
                var keyValue = this.dataset.key;

                if (keyValue === 'CapsLock') {
                    toggleCapsLock();
                    return;
                }

                if (elements.userInput.disabled) return;

                if (keyValue === 'Backspace') {
                    elements.userInput.value = elements.userInput.value.slice(0, -1);
                } else if (keyValue === 'Enter') {
                    elements.userInput.value += '\n';
                } else if (keyValue === 'Tab') {
                    elements.userInput.value += '\t';
                } else if (keyValue && keyValue.length === 1) {
                    var inputChar = /[a-z]/i.test(keyValue) && isCapsLockOn
                        ? keyValue.toUpperCase()
                        : keyValue;
                    elements.userInput.value += inputChar;
                } else {
                    return;
                }

                animateKey(this);
                countKeystroke();
                handleUserInput();
                elements.userInput.focus();
            });
        });
    }

    function animateKey(keyElement) {
        keyElement.classList.add('active');
        window.setTimeout(function () {
            keyElement.classList.remove('active');
        }, 200);
    }

    function highlightNextKey() {
        document.querySelectorAll('.key.next-key').forEach(function (key) {
            key.classList.remove('next-key');
        });

        if (!currentText || userTypedText.length >= currentText.length) return;

        var nextChar = currentText[userTypedText.length];
        var targetKey = findKeyForCharacter(nextChar);
        if (!targetKey) return;

        targetKey.classList.add('next-key');

        if (isShiftRequired(nextChar)) {
            var shiftKey = getAppropriateShift(nextChar);
            if (shiftKey) shiftKey.classList.add('next-key');
        }
    }

    var SHIFT_CHARS = '!@#$%^&*()_+{}|:"<>?~ABCDEFGHIJKLMNOPQRSTUVWXYZ';

    function isShiftRequired(char) {
        return SHIFT_CHARS.indexOf(char) !== -1;
    }

    function getAppropriateShift(char) {
        var shiftKeys = document.querySelectorAll('.key[data-key="Shift"]');
        if (shiftKeys.length < 2) return shiftKeys[0];

        // 왼손으로 누르는 글자는 오른쪽 Shift, 오른손 글자는 왼쪽 Shift를 쓴다.
        var leftHandChars = '~!@#$%QWERTYASDFGZXCVB';
        return leftHandChars.indexOf(char) !== -1 ? shiftKeys[1] : shiftKeys[0];
    }

    var SHIFT_KEY_MAP = {
        '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
        '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
        '~': '`', '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
        ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
    };

    function findKeyForCharacter(char) {
        if (!char) return null;

        if (char === ' ') return document.querySelector('.key[data-key=" "]');
        if (char === '\n' || char === 'Enter') return document.querySelector('.key[data-key="Enter"]');
        if (char === '\t' || char === 'Tab') return document.querySelector('.key[data-key="Tab"]');
        if (char === 'Backspace') return document.querySelector('.key[data-key="Backspace"]');

        var mapped = SHIFT_KEY_MAP[char];
        var wanted = (mapped || char).toLowerCase();

        var keys = document.querySelectorAll('.key');
        for (var i = 0; i < keys.length; i++) {
            var keyValue = keys[i].dataset.key;
            if (keyValue && keyValue.length === 1 && keyValue.toLowerCase() === wanted) {
                return keys[i];
            }
        }
        return null;
    }

    // --- 유틸 -------------------------------------------------------------
    function formatTime(seconds) {
        var minutes = Math.floor(seconds / 60);
        var remaining = seconds % 60;
        return minutes + ':' + String(remaining).padStart(2, '0');
    }
})();
