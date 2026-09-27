/**
 * 교사 대시보드 — 모드 on/off와 자리 연습 예제 목록 전환.
 *
 * 변경은 바로 서버에 저장한다(setter API). 실패하면 체크 상태를 되돌리고
 * 이유를 알린다 — 화면만 바뀌고 저장이 안 되면 교사가 오해하기 때문이다.
 */
(function () {
    'use strict';

    function showStatus(message, ok) {
        var box = document.getElementById('saveStatus');
        if (!box) return;
        box.className = 'alert ' + (ok ? 'alert-success' : 'alert-danger');
        box.textContent = message;
        if (window._statusTimer) window.clearTimeout(window._statusTimer);
        if (ok) {
            window._statusTimer = window.setTimeout(function () {
                box.className = 'alert d-none';
            }, 2000);
        }
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(function (response) {
            return response.json().then(function (data) {
                if (!response.ok) throw new Error(data.error || '저장에 실패했습니다.');
                return data;
            });
        });
    }

    document.querySelectorAll('.mode-toggle').forEach(function (toggle) {
        toggle.addEventListener('change', function () {
            var mode = toggle.getAttribute('data-mode');
            var desired = toggle.checked;
            toggle.disabled = true;

            postJson('/api/teacher/modes', { mode: mode, available: desired })
                .then(function () {
                    showStatus(mode + ' 연습을 ' + (desired ? '열었습니다.' : '닫았습니다.'), true);
                })
                .catch(function (error) {
                    toggle.checked = !desired; // 되돌린다
                    showStatus(error.message, false);
                })
                .then(function () { toggle.disabled = false; });
        });
    });

    var radios = document.querySelectorAll('.example-set-radio');
    radios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            if (!radio.checked) return;
            var previous = document.querySelector('.example-set-radio[data-active="1"]');
            radios.forEach(function (r) { r.disabled = true; });

            postJson('/api/teacher/example-set', { id: radio.value })
                .then(function () {
                    radios.forEach(function (r) { r.removeAttribute('data-active'); });
                    radio.setAttribute('data-active', '1');
                    showStatus('자리 연습 예제 목록을 바꿨습니다.', true);
                })
                .catch(function (error) {
                    if (previous) previous.checked = true;
                    showStatus(error.message, false);
                })
                .then(function () { radios.forEach(function (r) { r.disabled = false; }); });
        });
    });

    // 현재 활성 목록을 표시해 둔다(실패 시 되돌리기용).
    var active = document.querySelector('.example-set-radio:checked');
    if (active) active.setAttribute('data-active', '1');
})();
