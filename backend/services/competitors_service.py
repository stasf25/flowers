"""
Хранилище результатов по конкурентам: data/competitors.json (вложенный latest).
history.json остается журналом последних 10 запросов, сюда пишется
привязка сущности (текст/картинка/букет/сайт/отзывы) к конкуренту.
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.models.schemas import CompetitorProfile

logger = logging.getLogger("competitor_monitor.competitors")

_EMPTY_SLOTS = {"text": None, "site": None, "bouquets": [], "images": [], "reviews": []}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9а-яё]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60] or "shop"


class CompetitorsService:
    """Вложенный latest: последний результат каждого типа на конкурента"""

    def __init__(self):
        self.store_file = Path(settings.store_file)
        if not self.store_file.exists():
            # Чистый лист: пример для старта — examples/competitors.example.json
            # (скопировать в data/competitors.json вручную)
            self._save({"shops": {}})
            logger.info("competitors.json создан пустым (чистый лист)")
        else:
            self._merge_domain_duplicates()
        logger.info(f"Competitors store: {self.store_file}")

    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.store_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"competitors.json битый/пустой: {e}")
            return {"shops": {}}

    def _save(self, data: Dict[str, Any]):
        self.store_file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def list_profiles(self) -> List[CompetitorProfile]:
        data = self._load()
        return [CompetitorProfile(
            id=sid,
            name=s.get("name", sid),
            url=s.get("url", ""),
            price_min=s.get("price_min"),
            price_max=s.get("price_max"),
        ) for sid, s in data.get("shops", {}).items()]

    @staticmethod
    def _normalize_shop(name: str) -> str:
        """vesnaflowers.ru / https://vesnaflowers.ru/catalog -> vesnaflowers.
        Иначе — исходное имя как есть."""
        s = name.strip().lower()
        s = re.sub(r"^https?://", "", s)
        s = s.split("/")[0].split(":")[0].split("?")[0].strip().rstrip(".")
        if s.startswith("www."):
            s = s[4:]
        parts = s.split(".")
        # похоже на домен: последняя часть — TLD (2-10 букв), предпоследняя — имя
        if len(parts) >= 2 and re.fullmatch(r"[a-zа-яё]{2,10}", parts[-1]) \
                and re.fullmatch(r"[a-z0-9а-яё-]+", parts[-2]):
            return parts[-2]
        return name.strip()

    @staticmethod
    def _base_key(name: str) -> str:
        """Имя без хвостового '.tld': 'Флорист.ру' и 'Флорист' -> один ключ."""
        return re.sub(r"\.[a-zа-яё]{2,10}$", "", name.strip().lower())

    @staticmethod
    def _move_analyses(shops: dict, alias: str, target: str):
        src, dst = shops[alias], shops[target]
        da, sa = dst.setdefault("analyses", {}), src.get("analyses", {})
        for k in ("text", "site"):
            if sa.get(k) and not da.get(k):
                da[k] = sa[k]
        for k in ("bouquets", "images", "reviews"):
            da.setdefault(k, []).extend(sa.get(k, []))
            del da[k][:-10]
        if not dst.get("url") and src.get("url"):
            dst["url"] = src["url"]

    def _merge_domain_duplicates(self):
        """Одноразовое слияние фантомов, созданных из доменов до фикса нормализации.
        Правило общее (без перечня магазинов): совпал базовый ключ
        (имя без хвостового '.tld') или нормализованный домен — сливаем.
        Направление фиксировано: поздняя запись вливается в более раннюю
        (сиды пишутся первыми, фантомы дописываются в конец)."""
        data = self._load()
        shops = data.get("shops", {})
        changed = False
        order = list(shops.keys())
        for sid in list(shops.keys()):
            norm = self._normalize_shop(shops[sid].get("name", sid)).lower()
            base = self._base_key(shops[sid].get("name", sid))
            target = None
            for tsid in order:
                if tsid == sid or tsid not in shops:
                    continue
                # только назад по порядку: фантом (позже) -> оригинал (раньше)
                if order.index(tsid) > order.index(sid):
                    continue
                tname = shops[tsid].get("name", "")
                if tsid == norm or tname.lower() == norm or _slugify(tname) == _slugify(norm) \
                        or self._base_key(tname) == base:
                    target = tsid
                    break
            if target and target in shops:
                self._move_analyses(shops, sid, target)
                del shops[sid]
                changed = True
                logger.info(f"Слит фантом {sid} -> {target}")
        if changed:
            self._save(data)

    def add_profile(self, name: str, shop_id: str = "", url: str = "",
                    price_min: Optional[int] = None, price_max: Optional[int] = None) -> CompetitorProfile:
        """Явное добавление конкурента (вкладка Конкуренты). Пустой id -> slug из имени."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Название обязательно")
        sid = (shop_id or "").strip() or _slugify(name)
        data = self._load()
        shops = data.setdefault("shops", {})
        if sid in shops:
            raise KeyError(f"Конкурент {sid} уже существует")
        shops[sid] = {"id": sid, "name": name, "url": url or "",
                      "price_min": price_min, "price_max": price_max,
                      "analyses": {"text": None, "site": None, "bouquets": [], "images": [], "reviews": []}}
        self._save(data)
        logger.info(f"Добавлен конкурент: {name} -> {sid}")
        return CompetitorProfile(id=sid, name=name, url=url or "", price_min=price_min, price_max=price_max)

    def update_profile(self, shop_id: str, name: Optional[str] = None, url: Optional[str] = None,
                       price_min: Optional[int] = None, price_max: Optional[int] = None) -> CompetitorProfile:
        """Редактирование профиля (id неизменен). Пустые строки игнорируются, цены None = не менять."""
        data = self._load()
        shops = data.setdefault("shops", {})
        if shop_id not in shops:
            raise KeyError(f"Конкурент {shop_id} не найден")
        s = shops[shop_id]
        if name is not None and name.strip():
            s["name"] = name.strip()
        if url is not None:
            s["url"] = url
        if price_min is not None:
            s["price_min"] = price_min
        if price_max is not None:
            s["price_max"] = price_max
        self._save(data)
        logger.info(f"Обновлен конкурент: {shop_id}")
        return CompetitorProfile(id=shop_id, name=s.get("name", shop_id), url=s.get("url", ""),
                                 price_min=s.get("price_min"), price_max=s.get("price_max"))

    def delete_profile(self, shop_id: str):
        """Удаление конкурента вместе с анализами"""
        data = self._load()
        shops = data.setdefault("shops", {})
        if shop_id not in shops:
            raise KeyError(f"Конкурент {shop_id} не найден")
        del shops[shop_id]
        self._save(data)
        logger.info(f"Удален конкурент: {shop_id}")

    def resolve_shop(self, shop: str, url: str = "") -> Optional[str]:
        """Пустое имя -> None (без привязки).
        Порядок: 1) точное совпадение сырого ввода с id/именем (важно для имен
        вида 'Флорист.ру' — иначе нормализация срежет '.ру' как TLD);
        2) нормализация домен/URL -> имя -> совпадение; 3) создать профиль."""
        name = (shop or "").strip()
        if not name:
            return None
        data = self._load()
        shops = data.setdefault("shops", {})

        def _find(key: str) -> Optional[str]:
            for sid, s in shops.items():
                if sid == key or s.get("name", "").lower() == key.lower():
                    return sid
            return None

        sid = _find(name)
        if sid is None:
            norm = self._normalize_shop(name)
            if norm != name:
                sid = _find(norm)
        if sid is not None:
            if url and not shops[sid].get("url"):
                shops[sid]["url"] = url
                self._save(data)
            return sid
        sid = _slugify(name)
        i = 2
        while sid in shops:
            sid = f"{_slugify(name)}_{i}"
            i += 1
        shops[sid] = {"id": sid, "name": name, "url": url,
                      "price_min": None, "price_max": None,
                      "analyses": {"text": None, "site": None, "bouquets": [], "images": [], "reviews": []}}
        self._save(data)
        logger.info(f"Новый конкурент: {name} -> {sid}")
        return sid

    def save_analysis(self, shop_id: str, entity_type: str, result: Dict[str, Any], meta: Optional[Dict[str, Any]] = None):
        """entity_type: text | site | bouquet | reviews. bouquet/reviews — append (макс. 10), text/site — перезапись."""
        data = self._load()
        shop = data.get("shops", {}).get(shop_id)
        if not shop:
            return
        entry = {"ts": datetime.now().isoformat(), "result": result, "meta": meta or {}}
        analyses = shop.setdefault("analyses", {"text": None, "site": None, "bouquets": [], "images": [], "reviews": []})
        if entity_type in ("bouquet", "image"):
            key = "bouquets" if entity_type == "bouquet" else "images"
            items = analyses.setdefault(key, [])
            items.append(entry)
            del items[:-10]
        elif entity_type == "reviews":
            items = analyses.setdefault("reviews", [])
            items.append(entry)
            del items[:-10]
        elif entity_type in ("text", "site"):
            analyses[entity_type] = entry
        else:
            return
        self._save(data)
        logger.info(f"Сохранен анализ {entity_type} для {shop_id}")

    def get_for_compare(self, shop_ids: List[str]) -> Dict[str, Any]:
        data = self._load()
        return {sid: data.get("shops", {}).get(sid) for sid in shop_ids if sid in data.get("shops", {})}


logger.info("Создание глобального экземпляра Competitors сервиса...")
competitors_service = CompetitorsService()
