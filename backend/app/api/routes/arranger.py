from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.auth.dependencies import require_role
from app.core.config import settings
from app.models.user import UserRole
from app.schemas.arranger import ArrangerPreview, ArrangerTableInfo
from app.services import data_arranger
from app.services.data_arranger import ArrangeOptions, ArrangeResult, ArrangerError


router = APIRouter()

ARRANGER_ROLES = [UserRole.ADMIN, UserRole.MIS]
MAX_FILES = 10


@dataclass
class ArrangerRequest:
    files: list[tuple[str, bytes]]
    options: ArrangeOptions
    key: str | None
    how: str
    sort_by: str | None


def read_arranger_request(
    files: list[UploadFile] = File(...),
    key: str | None = Form(None),
    how: str = Form("outer"),
    sort_by: str | None = Form(None),
    trim: bool = Form(True),
    tidy_headers: bool = Form(True),
    drop_empty: bool = Form(True),
    drop_duplicates: bool = Form(True),
    title_case: bool = Form(False),
) -> ArrangerRequest:
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload at least one file.")
    if len(files) > MAX_FILES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Upload at most {MAX_FILES} files at a time.")

    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    loaded: list[tuple[str, bytes]] = []
    for upload in files:
        data = upload.file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"{upload.filename}: larger than {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        loaded.append((upload.filename or "file", data))

    return ArrangerRequest(
        files=loaded,
        options=ArrangeOptions(
            trim=trim,
            tidy_headers=tidy_headers,
            drop_empty=drop_empty,
            drop_duplicates=drop_duplicates,
            title_case=title_case,
        ),
        key=key or None,
        how=how,
        sort_by=sort_by or None,
    )


def run_arranger(request: ArrangerRequest) -> ArrangeResult:
    try:
        return data_arranger.process(
            request.files,
            request.options,
            key=request.key,
            how=request.how,
            sort_by=request.sort_by,
        )
    except ArrangerError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post(
    "/preview",
    response_model=ArrangerPreview,
    dependencies=[Depends(require_role(ARRANGER_ROLES))],
)
def preview_arranged_data(
    request: ArrangerRequest = Depends(read_arranger_request),
) -> ArrangerPreview:
    """Tidy the uploaded files, join them on a common column, and return the first rows."""
    result = run_arranger(request)
    frame = result.frame
    return ArrangerPreview(
        columns=[str(column) for column in frame.columns],
        rows=frame.head(data_arranger.PREVIEW_ROWS).values.tolist(),
        total_rows=len(frame),
        preview_limit=data_arranger.PREVIEW_ROWS,
        key=result.key,
        common_columns=result.common_columns,
        tables=[ArrangerTableInfo(name=n, rows=r, columns=c) for n, r, c in result.tables],
        notes=result.notes,
    )


@router.post(
    "/export",
    dependencies=[Depends(require_role(ARRANGER_ROLES))],
)
def export_arranged_data(
    file_format: str = Form("xlsx"),
    request: ArrangerRequest = Depends(read_arranger_request),
) -> Response:
    """The same result as /preview, with every row, as an Excel or CSV download."""
    if file_format not in data_arranger.EXPORT_FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file_format must be xlsx or csv.")
    result = run_arranger(request)
    if result.frame.empty:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "There is no data to export.")

    content = data_arranger.render(result.frame, file_format)
    filename = f"arranged_data_{date.today().isoformat()}.{file_format}"
    return Response(
        content=content,
        media_type=data_arranger.CONTENT_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
