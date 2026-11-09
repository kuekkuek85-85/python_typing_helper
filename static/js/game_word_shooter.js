/**
 * 낱말 슈팅 - 타자 게임 (재미용, 클라이언트 전용)
 *
 * 위에서 떨어지는 파이썬 낱말을 타이핑해 맞힌다. 바닥에 닿으면 생명이 줄고,
 * 빠르게 맞힐수록 콤보가 쌓인다. 점수는 서버에 저장하지 않으며(명예의 전당과
 * 무관), 최고 점수만 이 브라우저(localStorage)에 남긴다.
 */
(function () {
    'use strict';

    var WORDS = (window.gameWords && window.gameWords.length) ? window.gameWords
        : ['print', 'def', 'for', 'turtle', 'range'];
    var BEST_KEY = 'wordShooterBest';
    var STUDENT_KEY = 'gameStudentId';
    var GAME_ID = 'word-shooter';

    var el = {};
    var state = null;
    var rafId = null;
    var lastScore = 0;     // 방금 끝난 판의 점수(순위 등록용)

    document.addEventListener('DOMContentLoaded', function () {
        el = {
            area: document.getElementById('gameArea'),
            input: document.getElementById('gameInput'),
            score: document.getElementById('gameScore'),
            combo: document.getElementById('gameCombo'),
            best: document.getElementById('gameBest'),
            lives: document.getElementById('gameLives'),
            overlay: document.getElementById('gameOverlay'),
            overlayTitle: document.getElementById('overlayTitle'),
            overlayText: document.getElementById('overlayText'),
            startBtn: document.getElementById('startBtn'),
            scoreSubmit: document.getElementById('scoreSubmit'),
            studentId: document.getElementById('gameStudentId'),
            submitBtn: document.getElementById('submitScoreBtn'),
            submitStatus: document.getElementById('submitStatus'),
            leaderboardBody: document.getElementById('leaderboardBody'),
            refreshBtn: document.getElementById('refreshLeaderboard')
        };

        el.best.textContent = loadBest();
        el.startBtn.addEventListener('click', startGame);
        el.input.addEventListener('input', handleInput);
        el.submitBtn.addEventListener('click', submitScore);
        el.studentId.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); submitScore(); }
        });
        el.refreshBtn.addEventListener('click', fetchLeaderboard);
        // 한글 입력 모드면 글자가 안 맞으므로, 연습 화면과 같은 영문 힌트를 준다.
        el.input.setAttribute('lang', 'en');

        try {
            var saved = localStorage.getItem(STUDENT_KEY);
            if (saved) el.studentId.value = saved;
        } catch (e) { /* 저장소 접근 불가 시 무시 */ }

        fetchLeaderboard();

        // 탭을 벗어나면 잠시 멈춰 낱말이 쌓이지 않게 한다.
        document.addEventListener('visibilitychange', function () {
            if (document.hidden && state && state.running) pause();
        });
    });

    // --- 최고 점수 (localStorage) ----------------------------------------
    function loadBest() {
        try { return parseInt(localStorage.getItem(BEST_KEY), 10) || 0; }
        catch (e) { return 0; }
    }

    function saveBest(score) {
        try { localStorage.setItem(BEST_KEY, String(score)); }
        catch (e) { /* 사생활 보호 모드 등에서는 그냥 넘어간다 */ }
    }

    // --- 게임 시작/종료 --------------------------------------------------
    function startGame() {
        state = {
            words: [],
            score: 0,
            combo: 0,
            lives: 3,
            running: true,
            lastSpawn: 0,
            lastFrame: 0,
            best: loadBest()
        };

        // 이전 판의 낱말 DOM을 모두 치운다.
        var old = el.area.querySelectorAll('.game-word');
        for (var i = 0; i < old.length; i++) old[i].remove();

        el.overlay.classList.add('d-none');
        el.scoreSubmit.classList.add('d-none');
        el.input.disabled = false;
        el.input.value = '';
        el.input.focus();
        updateHud();
        rafId = window.requestAnimationFrame(loop);
    }

    function pause() {
        if (!state) return;
        state.running = false;
        if (rafId) window.cancelAnimationFrame(rafId);
        showOverlay('⏸ 잠깐 멈춤', '다시 시작하려면 버튼을 누르세요.', '이어서 하기');
    }

    function gameOver() {
        state.running = false;
        if (rafId) window.cancelAnimationFrame(rafId);
        el.input.disabled = true;
        lastScore = state.score;

        // 남아 있던 낱말을 치워 게임오버 화면을 깔끔하게 한다.
        var remaining = el.area.querySelectorAll('.game-word');
        for (var i = 0; i < remaining.length; i++) remaining[i].remove();
        state.words = [];

        var best = loadBest();
        if (state.score > best) { best = state.score; saveBest(best); }
        el.best.textContent = best;

        var newRecord = state.score >= best && state.score > 0;
        showOverlay(
            '게임 끝!',
            '점수 <strong>' + state.score + '</strong>' +
            (newRecord ? ' · 🎉 최고 기록!' : ' · 최고 ' + best),
            '다시 하기'
        );

        // 점수가 있으면 순위 등록 폼을 연다.
        if (state.score > 0) {
            el.submitStatus.textContent = '';
            el.submitStatus.className = 'form-text';
            el.submitBtn.disabled = false;
            el.studentId.disabled = false;
            el.scoreSubmit.classList.remove('d-none');
        } else {
            el.scoreSubmit.classList.add('d-none');
        }
    }

    function showOverlay(title, html, btnLabel) {
        el.overlayTitle.textContent = title;
        el.overlayText.innerHTML = html;
        el.startBtn.innerHTML = '<i class="bi bi-play-fill"></i> ' + btnLabel;
        el.overlay.classList.remove('d-none');
    }

    // --- 메인 루프 -------------------------------------------------------
    function loop(now) {
        if (!state || !state.running) return;
        if (!state.lastFrame) state.lastFrame = now;
        var dt = Math.min((now - state.lastFrame) / 1000, 0.1); // 큰 점프 방지
        state.lastFrame = now;

        maybeSpawn(now);
        moveWords(dt);

        rafId = window.requestAnimationFrame(loop);
    }

    function difficulty() {
        // 점수가 오를수록 더 자주, 더 빠르게 떨어진다.
        var level = state.score / 400;
        return {
            spawnInterval: Math.max(650, 1700 - level * 180),  // ms
            fallSpeed: Math.min(130, 45 + level * 9)           // px/s
        };
    }

    function maybeSpawn(now) {
        var diff = difficulty();
        if (now - state.lastSpawn < diff.spawnInterval) return;
        state.lastSpawn = now;
        spawnWord(diff.fallSpeed);
    }

    function spawnWord(fallSpeed) {
        // 지금 떠 있는 낱말과 '접두사까지' 겹치지 않는 것만 고른다.
        //
        // 같은 글자이거나, 한쪽이 다른 쪽의 앞부분이면(예: "in"⊂"input",
        // "for"⊂"forward") 안 된다. 둘이 같이 떠 있으면 "input"을 치다가
        // "in"이 먼저 완성돼 터져 버리고 남은 "put"이 씹히기 때문이다.
        var activeTexts = state.words.map(function (w) { return w.text; });
        var pool = WORDS.filter(function (w) { return !collidesWithActive(w, activeTexts); });
        if (!pool.length) return;
        var text = pool[Math.floor(Math.random() * pool.length)];

        var node = document.createElement('div');
        node.className = 'game-word';
        node.textContent = text;
        el.area.appendChild(node);

        var areaW = el.area.clientWidth;
        var maxX = Math.max(0, areaW - node.offsetWidth - 8);
        var x = Math.floor(Math.random() * maxX) + 4;
        node.style.left = x + 'px';
        node.style.top = '0px';

        state.words.push({ el: node, text: text, y: 0, speed: fallSpeed });
    }

    /** 후보 낱말이 떠 있는 낱말 중 하나와 접두사 관계(한쪽이 다른 쪽의 앞부분)인가. */
    function collidesWithActive(candidate, activeTexts) {
        for (var i = 0; i < activeTexts.length; i++) {
            var t = activeTexts[i];
            if (candidate.indexOf(t) === 0 || t.indexOf(candidate) === 0) return true;
        }
        return false;
    }

    function moveWords(dt) {
        var bottom = el.area.clientHeight;
        for (var i = state.words.length - 1; i >= 0; i--) {
            var w = state.words[i];
            w.y += w.speed * dt;
            w.el.style.top = w.y + 'px';
            if (w.y + w.el.offsetHeight >= bottom) {
                // 바닥에 닿음 → 생명 감소
                w.el.remove();
                state.words.splice(i, 1);
                loseLife();
            }
        }
    }

    function loseLife() {
        state.lives -= 1;
        state.combo = 0;
        el.input.value = '';
        updateHud();
        flashArea();
        if (state.lives <= 0) gameOver();
    }

    // --- 타이핑 처리 -----------------------------------------------------
    function handleInput() {
        if (!state || !state.running) return;

        // 영문 글자만 남긴다(한글 IME가 켜져 있어도 게임이 멈추지 않게).
        var candidate = (el.input.value || '').replace(/[^A-Za-z]/g, '');

        if (candidate === '') { el.input.value = ''; render(''); return; }

        // 떠 있는 낱말 중 이 입력으로 시작하는 게 있는지 본다.
        var matches = state.words.filter(function (w) {
            return w.text.indexOf(candidate) === 0;
        });

        if (!matches.length) {
            // 어떤 낱말과도 안 맞으면 방금 친 글자는 무시한다(진행 중이던 입력은 지킨다).
            var kept = candidate.slice(0, -1);
            el.input.value = kept;
            flashInput();
            render(kept);
            return;
        }

        el.input.value = candidate;

        // 정확히 완성된 낱말이 있으면 맞힌 것(바닥에 가까운 것부터).
        var done = matches
            .filter(function (w) { return w.text === candidate; })
            .sort(function (a, b) { return b.y - a.y; })[0];

        if (done) {
            destroyWord(done);
            el.input.value = '';
            render('');
        } else {
            render(candidate);
        }
    }

    function destroyWord(word) {
        var idx = state.words.indexOf(word);
        if (idx === -1) return;
        word.el.classList.add('game-word-hit');
        var node = word.el;
        window.setTimeout(function () { node.remove(); }, 150);
        state.words.splice(idx, 1);

        state.combo += 1;
        // 점수 = 글자 수 × (1 + 콤보 보너스). 빨리 연달아 맞힐수록 많이 받는다.
        state.score += word.text.length * (1 + Math.floor(state.combo / 3));
        if (state.score > state.best) state.best = state.score;
        updateHud();
    }

    /** 입력 중인 글자에 맞춰 각 낱말의 맞힌 앞부분을 강조한다. */
    function render(buffer) {
        for (var i = 0; i < state.words.length; i++) {
            var w = state.words[i];
            if (buffer && w.text.indexOf(buffer) === 0) {
                w.el.innerHTML = '<span class="game-word-typed">' +
                    escapeHtml(buffer) + '</span>' + escapeHtml(w.text.slice(buffer.length));
            } else {
                w.el.textContent = w.text;
            }
        }
    }

    // --- 표시 갱신 -------------------------------------------------------
    function updateHud() {
        el.score.textContent = state.score;
        el.combo.textContent = state.combo;
        el.best.textContent = Math.max(state.best, loadBest());
        el.lives.textContent = state.lives > 0 ? '❤️'.repeat(state.lives) : '💀';
    }

    function flashArea() {
        el.area.classList.add('game-area-hurt');
        window.setTimeout(function () { el.area.classList.remove('game-area-hurt'); }, 200);
    }

    function flashInput() {
        el.input.classList.add('is-invalid');
        window.setTimeout(function () { el.input.classList.remove('is-invalid'); }, 150);
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // --- 게임 순위표 (서버 저장) -----------------------------------------
    function submitScore() {
        var studentId = (el.studentId.value || '').trim();
        if (!studentId) {
            setSubmitStatus('학번과 이름을 입력하세요. (예: 10218 홍길동)', true);
            return;
        }

        el.submitBtn.disabled = true;
        setSubmitStatus('등록 중...', false);

        fetch('/api/game/records', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game: GAME_ID, student_id: studentId, score: lastScore })
        })
            .then(function (res) {
                return res.json().then(function (data) { return { ok: res.ok, data: data }; });
            })
            .then(function (r) {
                if (!r.ok) {
                    setSubmitStatus(r.data.error || '등록하지 못했습니다.', true);
                    el.submitBtn.disabled = false;
                    return;
                }
                try { localStorage.setItem(STUDENT_KEY, studentId); } catch (e) { /* 무시 */ }
                setSubmitStatus('✅ 순위에 등록했습니다!', false);
                el.studentId.disabled = true;
                fetchLeaderboard();
            })
            .catch(function () {
                setSubmitStatus('네트워크 오류로 등록하지 못했습니다.', true);
                el.submitBtn.disabled = false;
            });
    }

    function setSubmitStatus(msg, isError) {
        el.submitStatus.textContent = msg;
        el.submitStatus.className = 'form-text ' + (isError ? 'text-danger' : 'text-success');
    }

    function fetchLeaderboard() {
        fetch('/api/game/records?game=' + encodeURIComponent(GAME_ID))
            .then(function (res) { return res.json(); })
            .then(function (data) { renderLeaderboard((data && data.records) || []); })
            .catch(function () {
                el.leaderboardBody.innerHTML =
                    '<tr><td colspan="3" class="text-center text-muted py-3">순위를 불러오지 못했습니다.</td></tr>';
            });
    }

    function renderLeaderboard(records) {
        if (!records.length) {
            el.leaderboardBody.innerHTML =
                '<tr><td colspan="3" class="text-center text-muted py-3">' +
                '아직 기록이 없습니다. 첫 번째 도전자가 되어보세요!</td></tr>';
            return;
        }
        var medals = { 1: '🥇', 2: '🥈', 3: '🥉' };
        var rows = records.map(function (r) {
            var rankCell = medals[r.rank] || r.rank;
            return '<tr>' +
                '<td class="text-center">' + rankCell + '</td>' +
                '<td>' + escapeHtml(r.student_id) + '</td>' +
                '<td class="text-center fw-bold">' + r.score + '</td>' +
                '</tr>';
        });
        el.leaderboardBody.innerHTML = rows.join('');
    }
})();
