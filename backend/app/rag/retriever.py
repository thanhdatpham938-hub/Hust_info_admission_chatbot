"""Retriever: tim chunk trong Qdrant (PLAN - T7 retrieval (v2), muc 2.2).

Khong biet gi ve nganh/Truong o muc ten — chi nhan ma da phan giai (program_code, faculty_code). T7
(tools/rag_tool.py) lo phan giai thuc the va dong ToolResult; scripts/eval_retrieval.py dung lai lop nay.

Cac nhanh gop bang RRF cua Qdrant (Prefetch + FusionQuery):
  A  moi ban        loc cung: nam (neu neu), khoa (neu neu), loai tai lieu (neu co)
  B  ban moi nhat   A + (is_latest hoac versioned=false) — chi khi KHONG neu nam (R2: uu tien, khong loai)
  C  cum tu         A (+ ban moi neu khong neu nam) + MatchText cum tu chuyen nganh / cach goi tuong duong (R3)
  Nganh: moi nganh mot luot tim rieng (R1). Truong/Khoa: RRF (loc Truong) + (loc Truong va gioi_thieu_don_vi).
dense_score = cosine voi cau hoi, lay rieng (khong dung diem RRF) de dat nguong (R6).
"""

from dataclasses import dataclass, field

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings
from app.rag.phrases import Phrase, extract_phrases

F = models.FieldCondition
PREFETCH_LIMIT = 20
LATEST = models.Filter(should=[F(key="is_latest", match=models.MatchValue(value=True)),
                               F(key="versioned", match=models.MatchValue(value=False))])


@dataclass
class SearchSpec:
    query: str
    years: list[int] = field(default_factory=list)
    cohort: str | None = None                 # "K71+" | "<=K70" (da chuan hoa o T7)
    document_types: list[str] = field(default_factory=list)
    program_codes: list[str] = field(default_factory=list)
    faculty_codes: list[str] = field(default_factory=list)
    top_k: int = 5


@dataclass
class Hit:
    payload: dict
    dense_score: float


@dataclass
class SearchResult:
    hits: list[Hit]
    phrases: list[Phrase]
    top_dense_score: float


def base_filter(spec: SearchSpec) -> models.Filter:
    """Loc cung dung chung moi nhanh."""
    must: list = []
    if spec.years:
        # Neu nam: tai lieu nhieu nam chi lay dung nam do; tai lieu mot ban (so tay, quy che) giu nguyen
        must.append(models.Filter(should=[F(key="versioned", match=models.MatchValue(value=False)),
                                          F(key="year", match=models.MatchAny(any=spec.years))]))
    if spec.cohort:
        # Neu khoa: giu chunk khong gan khoa + chunk dung khoa (R5)
        must.append(models.Filter(should=[F(key="cohort", match=models.MatchValue(value="")),
                                          F(key="cohort", match=models.MatchValue(value=spec.cohort))]))
    if spec.document_types:
        must.append(F(key="document_type", match=models.MatchAny(any=spec.document_types)))
    return models.Filter(must=must)


def with_(flt: models.Filter, *extra) -> models.Filter:
    return models.Filter(must=list(flt.must or []) + list(extra))


def general_branches(spec: SearchSpec, phrases: list[Phrase]) -> list[models.Filter]:
    """Nhanh A, B, C cho cau hoi khong gan nganh/Truong."""
    a = base_filter(spec)
    branches = [a]
    if not spec.years:
        branches.append(with_(a, LATEST))
    if phrases:
        text = models.Filter(should=[F(key="text", match=models.MatchText(text=p.match)) for p in phrases])
        branches.append(with_(a, text) if spec.years else with_(a, LATEST, text))
    return branches


def faculty_branches(spec: SearchSpec) -> list[models.Filter]:
    a = base_filter(spec)
    fac = F(key="faculty_code", match=models.MatchAny(any=spec.faculty_codes))
    donvi = F(key="document_type", match=models.MatchValue(value="gioi_thieu_don_vi"))
    return [with_(a, fac), with_(a, fac, donvi)]


class Retriever:
    def __init__(self, qdrant_url: str | None = None, collection: str | None = None, model: str | None = None,
                 api_key: str | None = None) -> None:
        s = get_settings()
        # 127.0.0.1 thay localhost: tren Windows localhost thu IPv6 truoc, Qdrant chi mo 127.0.0.1
        url = (qdrant_url or s.qdrant_url).replace("localhost", "127.0.0.1")
        self.client = AsyncQdrantClient(url=url, timeout=20)
        key = api_key or (s.openai_api_key.get_secret_value() if s.openai_api_key else None)
        self.oa = AsyncOpenAI(api_key=key)
        self.collection = collection or s.qdrant_collection
        self.model = model or s.embedding_model

    async def close(self) -> None:
        await self.client.close()
        await self.oa.close()

    async def embed(self, text: str) -> list[float]:
        return (await self.oa.embeddings.create(model=self.model, input=text)).data[0].embedding

    async def _fuse(self, vec: list[float], branches: list[models.Filter], k: int) -> list[models.ScoredPoint]:
        if len(branches) == 1:
            return (await self.client.query_points(self.collection, query=vec, using="dense",
                                                   query_filter=branches[0], limit=k)).points
        return (await self.client.query_points(
            self.collection,
            prefetch=[models.Prefetch(query=vec, using="dense", filter=f, limit=PREFETCH_LIMIT) for f in branches],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=k)).points

    async def _cosine(self, vec: list[float], ids: list) -> dict:
        """Diem cosine that cua cac diem da chon (diem RRF chi la thu hang)."""
        if not ids:
            return {}
        pts = (await self.client.query_points(self.collection, query=vec, using="dense",
                                              query_filter=models.Filter(must=[models.HasIdCondition(has_id=ids)]),
                                              limit=len(ids))).points
        return {p.id: p.score for p in pts}

    async def search(self, spec: SearchSpec, vec: list[float] | None = None) -> SearchResult:
        """`vec` truyen san khi da co vector cau hoi (script do dung chung cho cach tim cu va moi)."""
        vec = vec or await self.embed(spec.query)
        phrases = extract_phrases(spec.query)
        if spec.program_codes:
            # R1: moi nganh mot luot tim rieng, xen ke de nganh nao cung co mat
            per = max(2, -(-spec.top_k // len(spec.program_codes)))
            lists = [await self._fuse(vec, [with_(base_filter(spec), F(key="program_code",
                                                                       match=models.MatchValue(value=c)))], per)
                     for c in spec.program_codes]
            points = [p for group in zip(*[lst + [None] * (per - len(lst)) for lst in lists]) for p in group if p]
        elif spec.faculty_codes:
            points = await self._fuse(vec, faculty_branches(spec), spec.top_k)
        else:
            points = await self._fuse(vec, general_branches(spec, phrases), spec.top_k)
        cos = await self._cosine(vec, [p.id for p in points])
        hits = [Hit(payload=p.payload, dense_score=cos.get(p.id, 0.0)) for p in points]
        return SearchResult(hits=hits, phrases=phrases if not (spec.program_codes or spec.faculty_codes) else [],
                            top_dense_score=max((h.dense_score for h in hits), default=0.0))
