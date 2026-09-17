"""연습 기록 저장소.

기본 백엔드는 **Firebase Firestore**(Admin SDK)이며, 자격 증명이 없으면
로컬 JSON 파일로 자동 전환된다. 덕분에 Firebase 설정 없이도 앱을 띄워
수업 전 점검이나 자동 테스트를 할 수 있다.

읽는 문서 수를 줄이는 방법은 세 가지다.
- 개수(탭 배지, 페이지네이션 total): 집계 쿼리 count() - 문서를 읽지 않는다
- 순위표 상위/앞쪽 페이지: order_by + limit 로 필요한 개수만 읽는다.
  복합 색인이 필요하지만, 없으면 모드별 전체 읽기로 자동 대체되므로 색인 설정
  없이도 동작한다.
- 전체 보기: 어차피 전부 필요하므로 모드별 전체 읽기

같은 모드를 반복 조회할 때는 짧은 캐시로 Firestore 읽기 횟수를 더 줄인다.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import config

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

RECORD_FIELDS = ('student_id', 'mode', 'wpm', 'accuracy', 'score', 'duration_sec', 'created_at')

# 상위 문서만 읽는 경로를 쓸 수 있는 최대 개수. 이보다 많이 필요하면(전체 보기)
# 어차피 대부분을 읽어야 하므로 모드별 전체 읽기가 낫다.
HEAD_FETCH_MAX = 200



def now_utc() -> datetime:
    """현재 시각(UTC, timezone-aware)."""
    return datetime.now(timezone.utc)


def to_api_dict(record: dict) -> dict:
    """API 응답용 dict. created_at은 한국 시간 기준 ISO 문자열로 변환한다."""
    created_at = record.get('created_at')
    return {
        'id': record.get('id'),
        'student_id': record.get('student_id'),
        'mode': record.get('mode'),
        'wpm': record.get('wpm'),
        'accuracy': record.get('accuracy'),
        'score': record.get('score'),
        'duration_sec': record.get('duration_sec'),
        'created_at': created_at.astimezone(KST).isoformat() if created_at else None,
    }


# 순위 정렬 기준. Firestore order_by와 파이썬 정렬이 **같은 순서**를 써야 한다.
# 하나만 바꾸면 색인 경로와 전체 읽기 경로의 순위가 달라진다.
SORT_ORDER = (
    ('score', 'DESCENDING'),
    ('accuracy', 'DESCENDING'),
    ('wpm', 'DESCENDING'),
    ('created_at', 'ASCENDING'),
)


def _sort_key(record: dict):
    """정렬 기준: score desc → accuracy desc → wpm desc → created_at asc"""
    created_at = record.get('created_at') or datetime.max.replace(tzinfo=timezone.utc)
    return (-record.get('score', 0), -record.get('accuracy', 0.0),
            -record.get('wpm', 0), created_at)


class RecordStore:
    """저장소 공통 로직(정렬·페이지네이션·캐시)."""

    backend = 'base'
    # 설정이 잘못돼 제 역할을 못 하는 경우 그 이유. /health가 그대로 내보낸다.
    reason: str | None = None

    def __init__(self, cache_ttl_seconds: int | None = None):
        self._cache_ttl = (cache_ttl_seconds if cache_ttl_seconds is not None
                           else config.STORE_CACHE_TTL_SECONDS)
        self._cache_lock = threading.Lock()
        # 키 → (저장 시각, 값). 값은 기록 목록 또는 개수.
        self._cache: dict[str, tuple[float, object]] = {}
        # 무효화 세대. 조회를 시작할 때의 세대와 저장할 때의 세대가 다르면
        # 조회 도중 새 기록이 저장된 것이므로 오래된 값을 캐시하지 않는다.
        self._generations: dict[str, int] = {}
        self._global_generation = 0

    # --- 하위 클래스가 구현 -------------------------------------------------
    def ping(self) -> bool:
        raise NotImplementedError

    def _persist(self, record: dict) -> dict:
        raise NotImplementedError

    def _fetch_mode(self, mode: str) -> list[dict]:
        raise NotImplementedError

    # --- 공통 API ---------------------------------------------------------
    def add(self, *, student_id: str, mode: str, wpm: int, accuracy: float, score: int,
            duration_sec: int, created_at: datetime | None = None) -> dict:
        record = {
            'student_id': student_id,
            'mode': mode,
            'wpm': int(wpm),
            'accuracy': float(accuracy),
            'score': int(score),
            'duration_sec': int(duration_sec),
            'created_at': created_at or now_utc(),
        }
        saved = self._persist(record)
        self.invalidate(mode)
        return saved

    def records_for_mode(self, mode: str) -> list[dict]:
        """모드별 기록을 정렬된 상태로 돌려준다(짧은 캐시 사용)."""
        cached = self._cached(mode)
        if cached is not None:
            return cached

        generation = self._generation(mode)
        records = sorted(self._fetch_mode(mode), key=_sort_key)
        self._store_cache(mode, records, mode=mode, generation=generation)
        return records

    def count_for_mode(self, mode: str) -> int:
        """모드별 기록 수. 하위 클래스는 더 싼 방법으로 대체할 수 있다."""
        return len(self.records_for_mode(mode))

    def top(self, mode: str, limit: int = 10) -> list[dict]:
        return self.records_for_mode(mode)[:limit]

    def page(self, mode: str, limit: int, offset: int) -> tuple[list[dict], int]:
        records = self.records_for_mode(mode)
        return records[offset:offset + limit], len(records)

    def invalidate(self, mode: str | None = None) -> None:
        """캐시를 비운다. 모드별 파생 캐시(head/count)도 함께 지운다."""
        with self._cache_lock:
            if mode is None:
                self._cache.clear()
                self._global_generation += 1
                return
            prefix = f'{mode}:'
            for key in [k for k in self._cache if k == mode or k.startswith(prefix)]:
                del self._cache[key]
            self._generations[mode] = self._generations.get(mode, 0) + 1

    def _generation(self, mode: str) -> tuple[int, int]:
        """조회 시작 시점의 무효화 세대."""
        with self._cache_lock:
            return (self._global_generation, self._generations.get(mode, 0))

    def _cached(self, key: str):
        if self._cache_ttl <= 0:
            return None
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and time.time() - entry[0] < self._cache_ttl:
                return entry[1]
        return None

    def _store_cache(self, key: str, value, mode: str | None = None,
                     generation: tuple[int, int] | None = None) -> None:
        """조회 도중 무효화가 일어나지 않았을 때만 캐시에 저장한다.

        이 확인이 없으면 A 스레드가 옛 데이터를 읽는 동안 B 스레드가 기록을 저장하고
        무효화한 뒤, A가 옛 목록을 다시 캐시해 새 기록이 TTL 동안 안 보이게 된다.
        """
        if self._cache_ttl <= 0:
            return
        with self._cache_lock:
            if generation is not None:
                current = (self._global_generation, self._generations.get(mode, 0))
                if current != generation:
                    return
            self._cache[key] = (time.time(), value)


class FirestoreStore(RecordStore):
    """Firebase Firestore 백엔드(Admin SDK)."""

    backend = 'firestore'

    def __init__(self, collection_name: str | None = None, cache_ttl_seconds: int | None = None):
        super().__init__(cache_ttl_seconds)
        self._collection_name = collection_name or config.FIRESTORE_COLLECTION
        # 복합 색인이 없다는 경고는 한 번만 남긴다.
        self._head_fetch_warned = False
        self._client = create_firestore_client()

    @property
    def _collection(self):
        return self._client.collection(self._collection_name)

    def ping(self) -> bool:
        try:
            # 문서 1개만 읽어 연결을 확인한다.
            next(iter(self._collection.limit(1).stream()), None)
            return True
        except Exception as error:  # noqa: BLE001 - 연결 실패 사유는 로그로만 남긴다
            logger.error("Firestore 연결 실패: %s", error)
            return False

    def _persist(self, record: dict) -> dict:
        doc_ref = self._collection.document()
        doc_ref.set({key: record[key] for key in RECORD_FIELDS})
        return {**record, 'id': doc_ref.id}

    def _fetch_mode(self, mode: str) -> list[dict]:
        query = _apply_mode_filter(self._collection, mode)
        return [self._document_to_record(doc) for doc in query.stream()]

    # --- 서버 측에서 읽는 양을 줄이는 경로 --------------------------------
    def count_for_mode(self, mode: str) -> int:
        """집계 쿼리로 개수만 센다(문서를 전부 읽지 않는다)."""
        cache_key = f'{mode}:count'
        cached = self._cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        generation = self._generation(mode)
        try:
            query = _apply_mode_filter(self._collection, mode)
            result = query.count().get()
            total = int(result[0][0].value)
        except Exception as error:  # noqa: BLE001 - 집계를 못 쓰면 전체 읽기로 대체
            logger.warning("집계 쿼리 실패 → 전체 읽기로 개수를 셉니다: %s", error)
            total = len(self.records_for_mode(mode))

        self._store_cache(cache_key, total, mode=mode, generation=generation)
        return total

    def top(self, mode: str, limit: int = 10) -> list[dict]:
        head = self._fetch_head(mode, limit)
        if head is not None:
            return head[:limit]
        return self.records_for_mode(mode)[:limit]

    def page(self, mode: str, limit: int, offset: int) -> tuple[list[dict], int]:
        total = self.count_for_mode(mode)

        # 앞쪽 일부만 필요하면 상위 문서만 읽는다(순위표 Top10, 탭 배지 등).
        needed = offset + limit
        if needed <= HEAD_FETCH_MAX:
            head = self._fetch_head(mode, needed)
            if head is not None:
                return head[offset:needed], total

        records = self.records_for_mode(mode)
        return records[offset:offset + limit], total

    def _fetch_head(self, mode: str, needed: int) -> list[dict] | None:
        """순위 상위 문서만 읽어 돌려준다.

        **정렬 기준(SORT_ORDER) 전부를 쿼리의 order_by에 넣는다.** score만 정렬하고
        나머지를 읽은 뒤 파이썬에서 처리하면, 같은 점수가 읽어온 개수보다 많을 때
        경계에서 더 높은 정확도·타수의 기록이 잘려 전체 읽기 경로와 순위가 달라진다.

        필요한 복합 색인이 없으면 None을 돌려주고 호출자가 전체 읽기로 대체한다.
        덕분에 색인을 만들지 않아도 앱이 그대로 동작하고, 색인을 만들면 읽는 문서
        수가 전체에서 필요한 개수만큼으로 줄어든다.
        """
        if needed <= 0 or needed > HEAD_FETCH_MAX:
            return None

        cache_key = f'{mode}:head:{needed}'
        cached = self._cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        generation = self._generation(mode)
        try:
            query = _apply_mode_filter(self._collection, mode)
            for field, direction in SORT_ORDER:
                query = query.order_by(field, direction=direction)
            # 쿼리가 이미 최종 순서로 돌려주지만, created_at의 시간대 정규화까지
            # 파이썬 정렬과 완전히 일치시키기 위해 한 번 더 정렬한다.
            records = sorted((self._document_to_record(doc)
                              for doc in query.limit(needed).stream()), key=_sort_key)
        except Exception as error:  # noqa: BLE001 - 색인이 없으면 전체 읽기로 대체
            if not self._head_fetch_warned:
                self._head_fetch_warned = True
                logger.warning(
                    "상위 문서만 읽는 경로를 쓸 수 없어 모드별 전체 읽기로 대체합니다. "
                    "firestore.indexes.json 의 복합 색인을 만들면 읽기 횟수가 크게 줄어듭니다. "
                    "사유: %s", error,
                )
            return None

        self._store_cache(cache_key, records, mode=mode, generation=generation)
        return records

    @staticmethod
    def _document_to_record(doc) -> dict:
        data = doc.to_dict() or {}
        created_at = data.get('created_at')
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elif isinstance(created_at, str):
            created_at = _parse_datetime(created_at)
        return {
            'id': doc.id,
            'student_id': data.get('student_id', ''),
            'mode': data.get('mode', ''),
            'wpm': int(data.get('wpm', 0) or 0),
            'accuracy': float(data.get('accuracy', 0.0) or 0.0),
            'score': int(data.get('score', 0) or 0),
            'duration_sec': int(data.get('duration_sec', 0) or 0),
            'created_at': created_at,
        }


class LocalJsonStore(RecordStore):
    """로컬 JSON 파일 백엔드(개발·테스트·오프라인 수업용)."""

    backend = 'local'

    def __init__(self, path: str | None = None, cache_ttl_seconds: int | None = None):
        # 파일을 매번 읽어도 부담이 없으므로 캐시는 기본적으로 쓰지 않는다.
        super().__init__(0 if cache_ttl_seconds is None else cache_ttl_seconds)
        self._path = path or config.LOCAL_DB_PATH
        self._lock = threading.Lock()
        self._ensure_directory()

    def _ensure_directory(self) -> bool:
        """저장 디렉터리를 준비한다. 만들 수 없으면 경고만 남기고 False.

        **여기서 예외를 올리면 안 된다.** 서버리스(Vercel)의 런타임 파일
        시스템은 `/tmp` 말고는 읽기 전용이라 `makedirs`가 실패하는데, 이 객체는
        `create_app()` 안에서 만들어지므로 예외가 그대로 임포트를 죽인다. 그러면
        앱이 아예 뜨지 않고 배포 실패로만 보인다.

        기록을 남기지 못하는 상태라는 건 `/health`의 `backend`와 `database_connected`가
        이미 드러내 준다. 죽는 것보다 떠서 말해 주는 편이 낫다.
        """
        directory = os.path.dirname(os.path.abspath(self._path))
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except OSError as error:
            logger.error(
                "로컬 저장소 디렉터리를 만들 수 없습니다(%s): %s. "
                "기록이 저장되지 않습니다 — Firebase 자격 증명을 설정하세요.",
                directory, error,
            )
            return False

    @property
    def path(self) -> str:
        return self._path

    def ping(self) -> bool:
        try:
            self._read()
            return True
        except Exception as error:  # noqa: BLE001
            logger.error("로컬 저장소 읽기 실패: %s", error)
            return False

    def _persist(self, record: dict) -> dict:
        with self._lock:
            data = self._read()
            record_id = str(data.get('next_id', 1))
            saved = {**record, 'id': record_id}
            data['records'].append({
                **{key: record[key] for key in RECORD_FIELDS if key != 'created_at'},
                'created_at': record['created_at'].isoformat(),
                'id': record_id,
            })
            data['next_id'] = int(record_id) + 1
            self._write(data)
        return saved

    def _fetch_mode(self, mode: str) -> list[dict]:
        with self._lock:
            data = self._read()
        records = []
        for raw in data.get('records', []):
            if raw.get('mode') != mode:
                continue
            records.append({
                'id': raw.get('id'),
                'student_id': raw.get('student_id', ''),
                'mode': raw.get('mode', ''),
                'wpm': int(raw.get('wpm', 0) or 0),
                'accuracy': float(raw.get('accuracy', 0.0) or 0.0),
                'score': int(raw.get('score', 0) or 0),
                'duration_sec': int(raw.get('duration_sec', 0) or 0),
                'created_at': _parse_datetime(raw.get('created_at')),
            })
        return records

    def _read(self) -> dict:
        if not os.path.exists(self._path):
            return {'next_id': 1, 'records': []}
        try:
            with open(self._path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as error:
            logger.error("로컬 저장소 파일이 손상되었습니다(%s): %s", self._path, error)
            return {'next_id': 1, 'records': []}
        data.setdefault('records', [])
        data.setdefault('next_id', len(data['records']) + 1)
        return data

    def _write(self, data: dict) -> None:
        # 같은 디렉터리에 임시 파일로 쓴 뒤 교체해 쓰기 중단 시 파일이 깨지지 않게 한다.
        temp_path = f"{self._path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, self._path)


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        logger.warning("created_at 값을 해석할 수 없습니다: %r", value)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _apply_mode_filter(collection, mode: str):
    """google-cloud-firestore 버전에 따라 달라지는 where() 호출을 흡수한다."""
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter

        return collection.where(filter=FieldFilter('mode', '==', mode))
    except ImportError:  # 구버전 SDK
        return collection.where('mode', '==', mode)


def _firebase_credential():
    """환경 변수에서 서비스 계정 자격 증명을 만든다. 없으면 None(기본 자격 증명)."""
    from firebase_admin import credentials

    raw_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    if raw_json:
        return credentials.Certificate(json.loads(raw_json))

    key_file = (os.environ.get('FIREBASE_SERVICE_ACCOUNT_FILE')
                or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
    if key_file:
        return credentials.Certificate(key_file)

    return None


def create_firestore_client():
    import firebase_admin
    from firebase_admin import firestore

    if not firebase_admin._apps:  # noqa: SLF001 - 초기화 여부 확인용 공식 관례
        options = {}
        project_id = os.environ.get('FIREBASE_PROJECT_ID') or os.environ.get('GCLOUD_PROJECT')
        if project_id:
            options['projectId'] = project_id
        firebase_admin.initialize_app(_firebase_credential(), options or None)

    return firestore.client()


def firebase_credentials_available() -> bool:
    """Firestore에 쓸 수 있는 자격 증명이 있는지 확인한다.

    명시적 환경 변수뿐 아니라 **기본 자격 증명(ADC)** 도 확인해야 한다.
    Cloud Run처럼 서비스 계정이 런타임에 자동으로 주어지는 환경에서는 환경 변수가
    없는데, 이걸 놓치면 STORE_BACKEND=auto가 로컬 JSON으로 전환되고 컨테이너가
    재시작될 때 학생 기록이 사라진다.
    """
    if any(os.environ.get(name) for name in (
        'FIREBASE_SERVICE_ACCOUNT_JSON',
        'FIREBASE_SERVICE_ACCOUNT_FILE',
        'GOOGLE_APPLICATION_CREDENTIALS',
    )):
        return True

    try:
        import google.auth

        google.auth.default(scopes=['https://www.googleapis.com/auth/datastore'])
        logger.info("Google 기본 자격 증명(ADC)을 찾았습니다. Firestore를 사용합니다.")
        return True
    except Exception as error:  # noqa: BLE001 - 자격 증명이 없는 것은 정상 경로다
        logger.debug("기본 자격 증명을 찾지 못했습니다: %s", error)
        return False


class UnavailableStore(RecordStore):
    """저장소를 만들지 못했을 때 그 자리를 대신한다.

    **설정이 잘못됐다고 앱이 죽으면 안 된다.** 서버리스에서는 임포트 중 예외가
    `500 FUNCTION_INVOCATION_FAILED` 한 줄로만 보여서, 무엇이 잘못됐는지 알 길이
    없다. 대신 떠서 `/health`가 이유를 말하게 한다.

    그렇다고 로컬 JSON으로 조용히 대체하지는 않는다. 명시적으로 Firestore를
    지정했는데 로컬 파일에 쓰면 학생 기록이 사라진다. 저장은 거부하고 이유를
    알린다.
    """

    backend = 'unavailable'

    def __init__(self, reason: str):
        super().__init__(0)
        self.reason = reason

    def ping(self) -> bool:
        return False

    def _fetch_mode(self, mode: str) -> list[dict]:
        raise RuntimeError(self.reason)

    def _persist(self, record: dict) -> dict:
        raise RuntimeError(self.reason)


def create_store() -> RecordStore:
    """config.STORE_BACKEND 설정에 따라 저장소를 만든다.

    **이 함수는 예외를 올리지 않는다.** create_app()이 임포트 중에 호출하므로
    여기서 죽으면 앱이 아예 뜨지 않고 원인도 보이지 않는다.
    """
    backend = config.STORE_BACKEND

    if backend == 'local':
        logger.info("로컬 JSON 저장소를 사용합니다: %s", config.LOCAL_DB_PATH)
        return LocalJsonStore()

    if backend == 'firestore':
        try:
            return FirestoreStore()
        except Exception as error:  # noqa: BLE001
            reason = (
                'STORE_BACKEND=firestore인데 Firestore에 연결할 수 없습니다. '
                'FIREBASE_SERVICE_ACCOUNT_JSON이 줄바꿈 없는 한 줄 JSON인지 '
                f'확인하세요. 원인: {error}'
            )
            logger.error("%s", reason)
            return UnavailableStore(reason)

    if backend != 'auto':
        logger.warning("알 수 없는 STORE_BACKEND=%r → auto로 처리합니다.", backend)

    if firebase_credentials_available():
        try:
            return FirestoreStore()
        except Exception as error:  # noqa: BLE001
            logger.error("Firestore 초기화 실패 → 로컬 JSON 저장소로 대체합니다: %s", error)
            return LocalJsonStore()

    logger.warning(
        "Firebase 자격 증명이 없어 로컬 JSON 저장소를 사용합니다(%s). "
        "실제 수업에 배포할 때는 FIREBASE_SERVICE_ACCOUNT_JSON을 설정하세요.",
        config.LOCAL_DB_PATH,
    )
    return LocalJsonStore()
