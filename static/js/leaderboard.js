/**
 * 홈화면 명예의 전당.
 *
 * 서버가 정렬과 **등수까지** 정해서 보내준다(store.assign_ranks).
 * 여기서 위치로 등수를 계산하면 검색으로 걸러낸 목록에서 "홍길동 1등"처럼
 * 실제와 다른 등수가 나온다. record.rank를 그대로 쓴다.
 */
(function () {
    'use strict';

    var ALL_VIEW_LIMIT = 2000;      // 서버 MAX_PAGE_SIZE와 동일
    var SEARCH_MIN_LENGTH = 2;      // 서버 config.SEARCH_MIN_LENGTH와 동일
    var SEARCH_DEBOUNCE_MS = 300;

    function Leaderboard() {
        this.modes = [];
        document.querySelectorAll('#modeTab button[data-mode]').forEach(function (tab) {
            this.modes.push(tab.getAttribute('data-mode'));
        }, this);

        this.currentMode = this.modes[0] || '자리';
        this.viewMode = 'top10'; // 'top10' | 'all'
        this.search = '';
        this.searchTimer = null;
    }

    Leaderboard.prototype.init = function () {
        this.bindEvents();
        this.updateToggleButton();
        this.loadAllCounts();
        this.loadModeData(this.currentMode);
    };

    Leaderboard.prototype.bindEvents = function () {
        var self = this;

        document.querySelectorAll('#modeTab button[data-bs-toggle="tab"]').forEach(function (tab) {
            tab.addEventListener('shown.bs.tab', function (event) {
                var mode = event.target.getAttribute('data-mode');
                if (!mode) return;
                self.currentMode = mode;
                self.loadModeData(mode);
            });
        });

        var toggleButton = document.getElementById('viewToggleBtn');
        if (toggleButton) {
            toggleButton.addEventListener('click', function () {
                self.viewMode = self.viewMode === 'top10' ? 'all' : 'top10';
                self.updateToggleButton();
                self.loadModeData(self.currentMode);
            });
        }

        var searchInput = document.getElementById('recordSearch');
        if (searchInput) {
            searchInput.addEventListener('input', function () {
                // 한 글자 칠 때마다 요청하면 Firestore를 그만큼 읽는다. 입력이
                // 멎은 뒤에만 보낸다.
                window.clearTimeout(self.searchTimer);
                self.searchTimer = window.setTimeout(function () {
                    self.applySearch(searchInput.value);
                }, SEARCH_DEBOUNCE_MS);
            });
        }

        var clearButton = document.getElementById('searchClearBtn');
        if (clearButton) {
            clearButton.addEventListener('click', function () {
                if (searchInput) searchInput.value = '';
                window.clearTimeout(self.searchTimer);
                self.applySearch('');
                if (searchInput) searchInput.focus();
            });
        }
    };

    /** 검색어를 확정하고 목록을 다시 불러온다. */
    Leaderboard.prototype.applySearch = function (raw) {
        var value = (raw || '').trim();

        // 최소 길이 미만은 검색으로 치지 않는다(서버도 같은 기준으로 거절한다).
        var next = value.length >= SEARCH_MIN_LENGTH ? value : '';
        var changed = next !== this.search;

        this.search = next;
        this.updateSearchUi(value);

        if (changed) this.loadModeData(this.currentMode);
    };

    Leaderboard.prototype.updateSearchUi = function (typed) {
        var clearButton = document.getElementById('searchClearBtn');
        if (clearButton) clearButton.style.display = typed ? '' : 'none';

        var status = document.getElementById('searchStatus');
        if (!status) return;

        if (typed && typed.length < SEARCH_MIN_LENGTH) {
            status.textContent = SEARCH_MIN_LENGTH + '글자 이상 입력하면 검색합니다.';
        } else if (!this.search) {
            status.textContent = '';
        }
        // 검색 결과 건수는 응답을 받은 뒤 loadModeData가 채운다.
    };

    /** 탭 옆 배지에 모드별 전체 기록 수를 채운다. */
    Leaderboard.prototype.loadAllCounts = function () {
        this.modes.forEach(function (mode) {
            fetch('/api/records?mode=' + encodeURIComponent(mode) + '&limit=1&offset=0')
                .then(readJson)
                .then(function (data) {
                    var countEl = document.getElementById(mode + '-count');
                    if (countEl && data.pagination) {
                        countEl.textContent = data.pagination.total;
                    }
                })
                .catch(function () { /* 배지 숫자는 실패해도 무시한다. */ });
        });
    };

    Leaderboard.prototype.loadModeData = function (mode) {
        var view = this.panelElements(mode);
        if (!view) {
            console.error('순위표 영역을 찾을 수 없습니다:', mode);
            return;
        }

        var isSearching = !!this.search;
        // 검색 중에는 Top10만 봐서는 찾는 학생이 안 나오므로 전체에서 찾는다.
        var isAllView = this.viewMode === 'all' || isSearching;
        var url;
        if (isSearching) {
            url = '/api/records?mode=' + encodeURIComponent(mode) +
                  '&limit=' + ALL_VIEW_LIMIT + '&offset=0' +
                  '&search=' + encodeURIComponent(this.search);
        } else if (isAllView) {
            url = '/api/records?mode=' + encodeURIComponent(mode) +
                  '&limit=' + ALL_VIEW_LIMIT + '&offset=0';
        } else {
            url = '/api/records/top?mode=' + encodeURIComponent(mode);
        }

        view.loading.style.display = 'block';
        view.content.style.display = 'none';
        view.empty.style.display = 'none';
        view.tbody.innerHTML = '';

        var self = this;
        fetch(url)
            .then(readJson)
            .then(function (data) {
                var records = Array.isArray(data.records) ? data.records : [];

                // 탭 배지는 그 모드의 **전체** 기록 수다.
                //  - 검색 결과 수로 덮어쓰면 검색을 지운 뒤에도 줄어든 숫자가 남는다.
                //  - Top10 응답에는 pagination이 없다. 목록 길이(최대 10)로 덮어쓰면
                //    기록이 12건이어도 배지가 10으로 굳는다.
                if (view.count && !isSearching && data.pagination) {
                    view.count.textContent = data.pagination.total;
                }
                if (isSearching) {
                    self.showSearchCount(data.pagination ? data.pagination.total : records.length);
                }

                view.loading.style.display = 'none';

                if (records.length === 0) {
                    view.empty.style.display = 'block';
                    self.describeEmptyState(view, isSearching);
                    return;
                }

                self.renderRecords(view.tbody, records);
                view.content.style.display = 'block';

                var tableContainer = view.content.querySelector('.table-responsive');
                if (tableContainer) {
                    tableContainer.style.maxHeight = isAllView ? '600px' : '';
                    tableContainer.style.overflowY = isAllView ? 'auto' : '';
                    tableContainer.classList.toggle('dashboard-scroll', isAllView);
                }
            })
            .catch(function (error) {
                console.error(mode + ' 모드 데이터 로딩 실패:', error);

                view.loading.style.display = 'none';
                view.content.style.display = 'none';
                view.empty.style.display = 'block';

                var title = view.empty.querySelector('h5');
                var description = view.empty.querySelector('p');
                if (title) title.textContent = '데이터를 불러올 수 없습니다';
                if (description) {
                    description.textContent = '네트워크 연결을 확인하고 페이지를 새로고침해주세요. ' +
                        '문제가 계속되면 관리자에게 문의하세요.';
                }
            });
    };

    Leaderboard.prototype.panelElements = function (mode) {
        var loading = document.getElementById(mode + '-loading');
        var contentEl = document.getElementById(mode + '-content');
        var empty = document.getElementById(mode + '-empty');
        var tbody = document.getElementById(mode + '-tbody');

        if (!loading || !contentEl || !empty || !tbody) return null;

        return {
            loading: loading,
            content: contentEl,
            empty: empty,
            tbody: tbody,
            count: document.getElementById(mode + '-count')
        };
    };

    Leaderboard.prototype.renderRecords = function (tbody, records) {
        var fragment = document.createDocumentFragment();

        records.forEach(function (record, index) {
            // 등수는 서버가 정한다. 검색으로 걸러낸 목록에서도 전체 기준 등수가
            // 그대로 와야 하므로 여기서 위치로 다시 계산하지 않는다.
            var rank = typeof record.rank === 'number' ? record.rank : index + 1;
            fragment.appendChild(createRecordRow(record, rank));
        });

        tbody.innerHTML = '';
        tbody.appendChild(fragment);
    };

    /** 검색 결과 건수를 검색창 아래에 적는다. */
    Leaderboard.prototype.showSearchCount = function (total) {
        var status = document.getElementById('searchStatus');
        if (!status) return;
        status.textContent = total > 0
            ? '\'' + this.search + '\' 검색 결과 ' + total + '건 (등수는 전체 기준)'
            : '\'' + this.search + '\'와 일치하는 기록이 없습니다.';
    };

    /** 결과가 없을 때 안내 문구를 상황에 맞게 바꾼다. */
    Leaderboard.prototype.describeEmptyState = function (view, isSearching) {
        var title = view.empty.querySelector('h5');
        var description = view.empty.querySelector('p');
        var startLink = view.empty.querySelector('a');

        if (isSearching) {
            if (title) title.textContent = '검색 결과가 없습니다';
            if (description) {
                description.textContent = '학번 또는 이름의 일부를 입력해보세요. (예: 10218, 홍길동, 102)';
            }
            if (startLink) startLink.style.display = 'none';
        } else {
            if (title) title.textContent = '아직 기록이 없습니다';
            if (startLink) startLink.style.display = '';
        }
    };

    Leaderboard.prototype.updateToggleButton = function () {
        var toggleButton = document.getElementById('viewToggleBtn');
        if (!toggleButton) return;

        if (this.viewMode === 'top10') {
            toggleButton.innerHTML = '<i class="bi bi-list"></i> 전체 보기';
            toggleButton.className = 'btn btn-outline-primary btn-sm';
        } else {
            toggleButton.innerHTML = '<i class="bi bi-trophy"></i> Top10 보기';
            toggleButton.className = 'btn btn-outline-warning btn-sm';
        }
    };

    // --- 렌더링 헬퍼 ------------------------------------------------------
    function createRecordRow(record, rank) {
        var row = document.createElement('tr');

        var rankCell = document.createElement('td');
        rankCell.className = 'text-center';
        if (rank <= 3) {
            var badge = document.createElement('span');
            badge.className = 'badge bg-' + (rank === 1 ? 'warning' : rank === 2 ? 'secondary' : 'dark');
            badge.textContent = rank;
            rankCell.appendChild(badge);
        } else {
            rankCell.textContent = rank;
        }
        row.appendChild(rankCell);

        // textContent를 쓰므로 학생 이름에 특수문자가 있어도 안전하다.
        row.appendChild(cell('td', record.student_id || '', '', 'strong'));
        row.appendChild(cell('td', formatNumber(record.score), 'text-center', 'strong', 'text-warning'));
        row.appendChild(cell('td', formatNumber(record.wpm), 'text-center'));
        row.appendChild(cell('td', formatAccuracy(record.accuracy), 'text-center', 'span', 'text-success'));
        row.appendChild(cell('td', formatDate(record.created_at), 'text-center', 'small', 'text-muted'));

        return row;
    }

    function cell(tagName, text, className, innerTag, innerClassName) {
        var element = document.createElement(tagName);
        if (className) element.className = className;

        if (innerTag) {
            var inner = document.createElement(innerTag);
            if (innerClassName) inner.className = innerClassName;
            inner.textContent = text;
            element.appendChild(inner);
        } else {
            element.textContent = text;
        }
        return element;
    }

    function formatNumber(value) {
        var number = Number(value);
        return Number.isFinite(number) ? String(number) : '-';
    }

    function formatAccuracy(value) {
        var number = Number(value);
        return Number.isFinite(number) ? number.toFixed(1) + '%' : '-';
    }

    function formatDate(value) {
        if (!value) return '-';
        var date = new Date(value);
        if (Number.isNaN(date.getTime())) return '-';

        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        var hours = String(date.getHours()).padStart(2, '0');
        var minutes = String(date.getMinutes()).padStart(2, '0');
        return month + '/' + day + ' ' + hours + ':' + minutes;
    }

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

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.getElementById('modeTab')) return;
        new Leaderboard().init();
    });
})();
