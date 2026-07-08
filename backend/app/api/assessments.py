from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.database import get_db
from app.models.assessment import AssessmentJob, RequirementResult
from app.schemas.assessment import AssessmentJobRead
from app.ingestion.standards.itsar_adapter import ITSARAdapter
from app.analysis.orchestrator import AssessmentOrchestrator
from app.retrieval.hybrid_retriever import HybridRetriever
from app.ingestion.indexer import QdrantIndexer, BM25Indexer
from app.ingestion.chunker import HierarchicalChunker
from app.ingestion.embedder import BGEEmbedder
from app.models.document import Document as DBDocument
from app.ingestion.standards.itsar_router_config import ITSARRouterConfig
from app.analysis.applicability import ApplicabilityEngine
import os
import uuid
import tempfile
import asyncio
import json
from pathlib import Path

from app.database import get_db, AsyncSessionLocal

router = APIRouter()

INDEX_ROOT = Path(__file__).resolve().parents[2] / ".rag_store"
QDRANT_PATH = INDEX_ROOT / "qdrant"
BM25_STORE_PATH = INDEX_ROOT / "bm25_chunks.json"
INDEX_UPDATE_LOCK = asyncio.Lock()
RESULT_WRITE_LOCK = asyncio.Lock()
ORCHESTRATOR_RUNTIME = None


def get_orchestrator():
    global ORCHESTRATOR_RUNTIME
    if ORCHESTRATOR_RUNTIME is not None:
        return ORCHESTRATOR_RUNTIME
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    dense_idx = QdrantIndexer(location=str(QDRANT_PATH))
    sparse_idx = BM25Indexer(persist_path=str(BM25_STORE_PATH))
    retriever = HybridRetriever(dense_indexer=dense_idx, sparse_indexer=sparse_idx)
    ORCHESTRATOR_RUNTIME = (AssessmentOrchestrator(retriever), dense_idx, sparse_idx)
    return ORCHESTRATOR_RUNTIME


def _bounded_concurrency(env_name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(env_name, str(default))))
    except ValueError:
        return default


async def run_assessment_task(job_id: str, standard_id: str, framework_id: str, file_path: str, file_name: str, config: dict | None = None):
    async with AsyncSessionLocal() as db:
        import logging
        logging.basicConfig(filename="backend_bg_task.log", level=logging.INFO)
        logging.info("STARTING PIPELINE")
        try:
            if file_path.lower().endswith(".pdf"):
                import pymupdf
                pdf_doc = pymupdf.open(file_path)
                text = "\n".join([page.get_text() for page in pdf_doc])
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            doc_id = str(uuid.uuid4())
            db_doc = DBDocument(id=doc_id, filename=file_name, file_path=file_path, mime_type="text/plain", status="processed")
            db.add(db_doc)

            chunker = HierarchicalChunker(chunk_size=350, chunk_overlap=75)
            chunks = chunker.chunk_text(text, doc_id)
            for chunk in chunks:
                chunk.setdefault("metadata", {})["filename"] = file_name.lower()

            from app.retrieval.numeric_extractor import NumericExtractor
            num_extractor = NumericExtractor()
            numeric_chunks = num_extractor.extract(text, doc_id)

            embedder = BGEEmbedder()
            texts = [chunk["text"] for chunk in chunks]
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(None, embedder.embed_documents, texts)

            numeric_texts = [chunk.get("payload", {}).get("text", "") for chunk in numeric_chunks]
            if numeric_texts:
                numeric_embeddings = await loop.run_in_executor(None, embedder.embed_documents, numeric_texts)
                for chunk, emb in zip(numeric_chunks, numeric_embeddings):
                    chunk["vector"] = emb

            async with INDEX_UPDATE_LOCK:
                orchestrator, dense_idx, sparse_idx = get_orchestrator()
                dense_idx.index(chunks, embeddings)
                sparse_idx.index(chunks)

            adapter = ITSARAdapter()
            norm_framework_id = framework_id.upper()
            if not norm_framework_id.startswith(standard_id.upper() + "-"):
                norm_framework_id = standard_id.upper() + "-" + norm_framework_id

            try:
                reqs = adapter.load_framework(standard_id, norm_framework_id)
                if config and standard_id.upper() == "ITSAR":
                    router_config = ITSARRouterConfig.from_dict(config)
                    reqs = ApplicabilityEngine.filter_requirements(reqs, router_config)
                    logging.info("Filtered requirements to %s applicable groups.", len(reqs))
                    
                limit = os.getenv("LIMIT_REQUIREMENTS")
                if limit:
                    allowed_ids = [x.strip() for x in limit.split(",")]
                    limited_reqs = []
                    for g in reqs:
                        if str(g.get("id")) in allowed_ids:
                            limited_reqs.append(g)
                    reqs = limited_reqs
                    logging.info("Limited requirements to %s for testing.", limit)
            except Exception as e:
                logging.error("Failed to load framework: %s", e)
                reqs = []

            job = await db.get(AssessmentJob, job_id)
            if job:
                total_items = sum(1 + len(g.get("children", [])) for g in reqs)
                job.total_requirements = total_items
                job.document_id = doc_id
                db.add(job)
                await db.commit()

            from app.analysis.capability_ledger import CapabilityExtractor
            cap_extractor = CapabilityExtractor(orchestrator.retriever)
            capability_ledger = await cap_extractor.build_ledger(doc_id)

            group_sem = asyncio.Semaphore(_bounded_concurrency("ASSESSMENT_GROUP_CONCURRENCY", 2))

            async def process_group(group):
                async with group_sem:
                    children = group.get("children", [])

                    async def on_result_done(result_schema):
                        details = result_schema.analysis_details or {}
                        scores = details.get("scores", {})
                        async with RESULT_WRITE_LOCK:
                            async with AsyncSessionLocal() as session:
                                db_result = RequirementResult(
                                    job_id=job_id,
                                    requirement_id=result_schema.requirement_id,
                                    classification=result_schema.status,
                                    confidence={
                                        "score": result_schema.confidence_score,
                                        "semantic": scores.get("semantic"),
                                        "capability": scores.get("capability"),
                                        "evidence_quality": scores.get("evidence_quality"),
                                        "grounding": scores.get("grounding"),
                                    },
                                    reasoning=result_schema.justification,
                                    gap_description=details.get("summary"),
                                    expected_capabilities=details.get("expected_capabilities", []),
                                    observed_capabilities=details.get("observed_capabilities", []),
                                    missing_capabilities=details.get("missing_concepts", []),
                                    evidence=result_schema.evidence_references,
                                    evidence_quality=details.get("scores", {}),
                                    is_undertaking_requirement=result_schema.status == "manual_review",
                                    is_prohibition_requirement=details.get("is_prohibition_requirement", False),
                                    prohibition_violations=details.get("prohibition_details", {}).get("violations", []) if details.get("prohibition_details") else [],
                                    is_leaf=not result_schema.requirement_id.startswith("GROUP-"),
                                    child_result_count=len(children) if result_schema.requirement_id.startswith("GROUP-") else 0,
                                    shall_gap_child_count=0,
                                )
                                session.add(db_result)
                                await session.execute(
                                    update(AssessmentJob)
                                    .where(AssessmentJob.id == job_id)
                                    .values(processed_count=AssessmentJob.processed_count + 1)
                                )
                                await session.commit()

                    return await orchestrator.assess_group(group, children, progress_callback=on_result_done, numeric_chunks=numeric_chunks, capability_ledger=capability_ledger)

            tasks = [process_group(group) for group in reqs]
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in all_results:
                if isinstance(res, Exception):
                    logging.error("Exception in group processing: %s", res, exc_info=res)
            for results_schemas in all_results:
                if isinstance(results_schemas, Exception):
                    logging.error("Group processing failed: %s", results_schemas)

            job = await db.get(AssessmentJob, job_id)
            if job:
                job.status = "completed"
                db.add(job)
                await db.commit()

        except Exception as e:
            logging.error("PIPELINE FAILED: %s", e, exc_info=True)
            try:
                job = await db.get(AssessmentJob, job_id)
                if job:
                    job.status = "failed"
                    job.document_id = f"Error: {str(e)[:200]}"
                    db.add(job)
                    await db.commit()
            except Exception:
                pass


@router.post("/assess", response_model=AssessmentJobRead)
async def create_assessment(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    standard_id: str = Form(...),
    framework_id: str = Form(...),
    router_type: str | None = Form(None),
    capability_flags: str | None = Form(None),
    db: AsyncSession = Depends(get_db)
):
    caps = []
    if capability_flags:
        caps = [c.strip() for c in capability_flags.split(",") if c.strip()]

    config_dict = {
        "router_type": router_type or "conventional",
        "capability_flags": caps
    }

    content = await file.read()
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    job = AssessmentJob(
        standard_id=standard_id,
        framework_id=framework_id,
        router_type=config_dict["router_type"],
        capability_flags=config_dict["capability_flags"],
        document_id="processing",
        status="running"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(run_assessment_task, job.id, standard_id, framework_id, file_path, file.filename, config_dict)
    return job


@router.get("/reports/{job_id}")
async def get_report(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(AssessmentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Assessment not found")

    stmt = select(RequirementResult).where(RequirementResult.job_id == job_id)
    result = await db.execute(stmt)
    results = result.scalars().all()

    formatted_results = []
    
    title_map = {}
    from app.ingestion.standards.itsar_adapter import ITSARAdapter
    adapter = ITSARAdapter()
    try:
        norm_framework_id = job.framework_id.upper()
        if not norm_framework_id.startswith(job.standard_id.upper() + "-"):
            norm_framework_id = job.standard_id.upper() + "-" + norm_framework_id
        reqs = adapter.load_framework(job.standard_id, norm_framework_id)
        for g in reqs:
            title_map[str(g.get("id"))] = g.get("title", "")
            title_map[f"GROUP-{g.get('id')}"] = g.get("title", "")
            for c in g.get("children", []):
                title_map[str(c.get("id"))] = c.get("title", "")
    except Exception as e:
        import logging
        logging.error(f"Failed to load framework for titles: {e}")

    for r in results:
        parsed_reasoning = {}
        try:
            parsed_reasoning = json.loads(r.reasoning) if r.reasoning else {}
        except Exception:
            parsed_reasoning = {"summary": r.reasoning}

        summary_text = parsed_reasoning.get("summary") or parsed_reasoning.get("justification") or r.reasoning
        formatted_results.append({
            "id": r.requirement_id,
            "title": title_map.get(str(r.requirement_id), ""),
            "status": r.classification,
            "conf": f"{r.confidence.get('score', 0) * 100:.1f}%",
            "text": summary_text,
            "summary": summary_text,
            "recommendation": parsed_reasoning.get("recommendation"),
            "matched_concepts": parsed_reasoning.get("matched_concepts", []),
            "missing_concepts": parsed_reasoning.get("missing_concepts", []),
            "scores": parsed_reasoning.get("scores", {}),
            "evidence": parsed_reasoning.get("extracted_evidence", []),
            "details": parsed_reasoning,
        })

    return {
        "id": job.id,
        "status": job.status,
        "document_id": job.document_id,
        "total": job.total_requirements,
        "processed": job.processed_count,
        "group_titles": {k.replace("GROUP-", ""): v for k, v in title_map.items() if k.startswith("GROUP-") or not "." in k.replace("GROUP-", "")},
        "results": formatted_results
    }
