import time
import mlflow
from pydantic import BaseModel
from preprocessing.pdf_extractor import extract_pdf
from preprocessing.pattern_detector import detect_patterns
from preprocessing.layout_analyzer import check_margins
from preprocessing.table_analyzer import analyze_tables
from agents.analyst import run_analyst, CandidateError
from agents.verifier import run_verifier, ConfirmedError
from pipeline.token_tracker import reset, get
from security.guardrails_validator import validate_and_log_input, validate_and_log_output

# Token counter reset at the start of each pipeline run
reset()

class PageResult(BaseModel):
    page_number: int
    candidate_errors: list[CandidateError]
    confirmed_errors: list[ConfirmedError]
    processing_time: float


class PipelineResult(BaseModel):
    pdf_path: str
    total_pages: int
    total_errors: int
    pages: list[PageResult]
    total_processing_time: float


def process_pdf(pdf_path: str) -> PipelineResult:
    pipeline_start = time.time()

    with mlflow.start_run(run_name=f"pipeline_{pdf_path.split('/')[-1]}"):

        pages = extract_pdf(pdf_path)
        layout_errors = check_margins(pdf_path)
        layout_by_page = {}
        for error in layout_errors:
            layout_by_page.setdefault(error.page_number, []).append(error)

        page_results = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for page in pages:
            page_start = time.time()

            # Validar y sanitizar el input antes de procesarlo
            sanitized_text = validate_and_log_input(page.text, page.page_number)
            #if page.page_number == 1:
                #print(f"SANITIZED: {sanitized_text}")
                #print(f"ORIGINAL == SANITIZED: {page.text == sanitized_text}")
                # if page.page_number == 1:
                #     for i, (a, b) in enumerate(zip(page.text, sanitized_text)):
                #         if a != b:
                #             print(f"Diferencia en posición {i}: original='{repr(a)}' sanitized='{repr(b)}'")
                #             break
                #     print(f"Largo original: {len(page.text)}, largo sanitized: {len(sanitized_text)}")

            # Loguear resultado de validación en MLflow
            mlflow.log_metrics({
                f"page_{page.page_number}_input_sanitized": int(sanitized_text != page.text),
            })

            patterns = detect_patterns(sanitized_text, page.page_number)
            table_errors = analyze_tables(page.image_path, page.page_number) if page.image_path else []
            layout = layout_by_page.get(page.page_number, [])

            candidates = run_analyst(
                page_number=page.page_number,
                text=sanitized_text,
                patterns=patterns,
                layout_errors=layout,
                table_errors=table_errors
            )

            # Validar output del analista contra el texto de la página
            # sources = [sanitized_text]
            # for candidate in candidates:
            #     candidate.description = validate_and_log_output(
            #         output=candidate.description,
            #         sources=sources,
            #         agent_name="analyst",
            #         page_number=page.page_number
            #     )

            confirmed = run_verifier(candidates)
            page_time = time.time() - page_start

            page_results.append(PageResult(
                page_number=page.page_number,
                candidate_errors=candidates,
                confirmed_errors=confirmed,
                processing_time=round(page_time, 2)
            ))

        total_errors = sum(
            len([e for e in p.confirmed_errors if e.confirmed])
            for p in page_results
        )

        total_time = round(time.time() - pipeline_start, 2)

        pages_with_no_errors = len([
            p for p in page_results 
            if not any(e.confirmed == True for e in p.confirmed_errors)
        ])
        total_pages = len(page_results)
        correct_abstention_rate = round(pages_with_no_errors / total_pages, 3) if total_pages > 0 else 0
        print(f"pages_with_no_errors: {pages_with_no_errors}, correct_abstention_rate: {correct_abstention_rate}")
        mlflow.log_metrics({
            "total_pages": len(pages),
            "total_errors": total_errors,
            "total_processing_time": total_time,
            "pages_with_no_errors": pages_with_no_errors,
            "correct_abstention_rate": correct_abstention_rate
        })

        mlflow.log_param("pdf_path", pdf_path)
        
        # Log the token counts for the entire pipeline run
        mlflow.log_metrics(get())

    return PipelineResult(
        pdf_path=pdf_path,
        total_pages=len(pages),
        total_errors=total_errors,
        pages=page_results,
        total_processing_time=total_time
    )