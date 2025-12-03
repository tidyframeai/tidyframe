"""
File processing API routes
"""

import os
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.files.schemas import (
    FileUploadResponse,
    JobList,
    JobStatus,
    ProcessingConfig,
    UsageStats,
)
from app.core.database import get_db
from app.core.dependencies import (
    check_parsing_quota,
    check_user_rate_limit,
    get_anonymous_or_user,
    get_current_user,
    require_auth,
)
from app.models.job import JobStatus as JobStatusEnum
from app.models.job import ProcessingJob
from app.models.user import User
from app.services.file_service import FileService
from app.utils.client_ip import get_client_ip
from app.utils.file_utils import safe_filename, validate_file
from app.workers.file_processor import process_file

logger = structlog.get_logger()

router = APIRouter()

# File service instance
file_service = FileService()


@router.post(
    "/upload", response_model=FileUploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    config: ProcessingConfig = ProcessingConfig(),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(
        get_current_user
    ),  # Allow both authenticated and anonymous users
    _rate_limit: None = Depends(check_user_rate_limit),
):
    """Upload file for name parsing - Admin users bypass billing requirements"""

    # Get client IP - critical for anonymous user tracking
    # In production, this reads X-Forwarded-For header from nginx
    client_ip = get_client_ip(request)

    # Log IP detection for debugging (especially important for anonymous users)
    logger.info(
        "upload_ip_detection",
        detected_ip=client_ip,
        is_anonymous=not bool(current_user),
        x_forwarded_for=request.headers.get("x-forwarded-for"),
        x_real_ip=request.headers.get("x-real-ip"),
        direct_connection=request.client.host if request.client else None,
    )

    # Validate that we can identify anonymous users by IP
    if not current_user and not client_ip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine client IP address for anonymous upload. Please ensure proper network configuration.",
        )

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided"
        )

    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    from app.core.config import settings

    if file_extension not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}",
        )

    # Check file size limits before reading content
    if current_user:
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        max_size_mb = settings.MAX_FILE_SIZE_MB
    else:
        max_size = settings.ANONYMOUS_MAX_FILE_SIZE_MB * 1024 * 1024
        max_size_mb = settings.ANONYMOUS_MAX_FILE_SIZE_MB

    # Read file content with size limit checking
    try:
        # Read file content while checking size
        file_content = bytearray()
        chunk_size = 8192  # 8KB chunks

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break

            file_content.extend(chunk)

            # Check size limit while reading
            if len(file_content) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large (max: {max_size_mb}MB for {'authenticated users' if current_user else 'anonymous users'})",
                )

        file_content = bytes(file_content)
        file_size = len(file_content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty"
            )

    except HTTPException:
        # Re-raise HTTP exceptions (like file too large)
        raise
    except Exception as e:
        logger.error("file_read_failed", filename=file.filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
        )

    # Save file to disk
    try:
        file_path, generated_filename = file_service.save_uploaded_file(
            file_content, safe_filename(file.filename)
        )

        # Validate saved file
        validate_file(file_path)

    except Exception as e:
        logger.error("file_save_failed", filename=file.filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {str(e)}",
        )

    # Get file preview to estimate rows
    try:
        preview = file_service.preview_file(file_path)
        estimated_rows = preview.get("row_count", 0)

        # For full file estimation, we could read more rows or use file size estimation
        if estimated_rows < 1000:  # If preview is small, try to get better estimate
            pass

            try:
                if file_extension == ".csv":
                    # Count lines in CSV
                    with open(file_path, "r", encoding="utf-8") as f:
                        estimated_rows = sum(1 for _ in f) - 1  # Subtract header
                elif file_extension in [".xlsx", ".xls"]:
                    # For Excel, we'll use the preview count as estimation
                    pass
            except BaseException:
                # Fallback to preview count
                pass

    except Exception as e:
        logger.error("file_preview_failed", filename=file.filename, error=str(e))
        estimated_rows = 100  # Fallback estimate

    # Check quota
    try:
        await check_parsing_quota(current_user, client_ip, estimated_rows, db)
    except HTTPException:
        # Clean up file if quota check fails
        file_service.delete_file(file_path)
        raise

    # Note: expires_at is set when job completes (10 minutes after completion)
    # This ensures users get the full 10 minutes regardless of processing time

    # Create processing job
    job = ProcessingJob(
        user_id=current_user.id if current_user else None,
        filename=generated_filename,
        original_filename=safe_filename(file.filename),
        file_size=file_size,
        file_path=file_path,
        content_type=file.content_type,
        status=JobStatusEnum.PENDING,
        row_count=estimated_rows,
        parsing_config=config.dict(),
        anonymous_ip=client_ip if not current_user else None,
        # expires_at is intentionally not set here - it's set when job completes
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start background processing
    try:
        process_file.delay(
            job_id=str(job.id),
            file_path=file_path,
            user_id=str(current_user.id) if current_user else None,
            parsing_config=config.dict(),
        )

        logger.info(
            "file_processing_queued",
            job_id=job.id,
            filename=file.filename,
            user_id=current_user.id if current_user else None,
            estimated_rows=estimated_rows,
        )

    except Exception as e:
        logger.error("file_processing_queue_failed", job_id=job.id, error=str(e))

        # Update job status to failed
        job.status = JobStatusEnum.FAILED
        job.error_message = "Failed to queue processing task"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start file processing",
        )

    # Estimate processing time (rough estimate: 1 second per 100 rows)
    estimated_time = max(30, estimated_rows // 100)

    return FileUploadResponse(
        job_id=str(job.id),
        message="File uploaded successfully. Processing started.",
        estimated_processing_time=estimated_time,
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_and_ip: tuple = Depends(get_anonymous_or_user),
):
    """Get processing job status"""

    current_user, client_ip = user_and_ip

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )

    # Find job
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # Check access permissions
    if current_user:
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    else:
        # Anonymous user - check IP match
        if job.anonymous_ip != client_ip:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    # Prepare response with analytics
    response_data = JobStatus.model_validate(job)

    # Add analytics from error_details if job is completed
    if job.status == JobStatusEnum.COMPLETED:
        # Restructure analytics to match frontend expectations
        analytics_data = job.error_details or {}
        # Handle empty entity_stats properly
        entity_stats = analytics_data.get("entity_stats", {})
        if not entity_stats:  # If empty dict, use defaults
            entity_stats = {
                "person_count": 0,
                "company_count": 0,
                "trust_count": 0,
                "unknown_count": 0,
                "error_count": 0,
            }

        structured_analytics = {
            "entity_stats": entity_stats,
            "confidence_distribution": {
                "high": analytics_data.get("high_confidence_count", 0),
                "medium": analytics_data.get("medium_confidence_count", 0),
                "low": analytics_data.get("low_confidence_count", 0),
            },
            "gender_distribution": analytics_data.get(
                "gender_distribution", {"male": 0, "female": 0, "unknown": 0}
            ),
            "processing_statistics": {
                "avg_confidence": analytics_data.get("avg_confidence", 0.0),
                "success_rate": analytics_data.get("success_rate", 0.0),
                "high_confidence_count": analytics_data.get("high_confidence_count", 0),
                "medium_confidence_count": analytics_data.get(
                    "medium_confidence_count", 0
                ),
                "low_confidence_count": analytics_data.get("low_confidence_count", 0),
            },
        }
        response_data.analytics = structured_analytics

    return response_data


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(
        None, regex="^(pending|processing|completed|failed)$"
    ),
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List user's processing jobs"""

    # Build query
    query = select(ProcessingJob).where(ProcessingJob.user_id == current_user.id)

    if status_filter:
        query = query.where(ProcessingJob.status == status_filter)

    # Add pagination and ordering
    query = query.order_by(desc(ProcessingJob.created_at))

    # Count total
    count_query = select(func.count(ProcessingJob.id)).where(
        ProcessingJob.user_id == current_user.id
    )
    if status_filter:
        count_query = count_query.where(ProcessingJob.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get page results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Prepare job list with analytics
    job_list = []
    for job in jobs:
        job_data = JobStatus.model_validate(job)
        # Add analytics from error_details if job is completed
        if job.status == JobStatusEnum.COMPLETED:
            # Restructure analytics to match frontend expectations
            analytics_data = job.error_details or {}
            # Handle empty entity_stats properly
            entity_stats = analytics_data.get("entity_stats", {})
            if not entity_stats:  # If empty dict, use defaults
                entity_stats = {
                    "person_count": 0,
                    "company_count": 0,
                    "trust_count": 0,
                    "unknown_count": 0,
                    "error_count": 0,
                }

            structured_analytics = {
                "entity_stats": entity_stats,
                "confidence_distribution": {
                    "high": analytics_data.get("high_confidence_count", 0),
                    "medium": analytics_data.get("medium_confidence_count", 0),
                    "low": analytics_data.get("low_confidence_count", 0),
                },
                "gender_distribution": analytics_data.get(
                    "gender_distribution", {"male": 0, "female": 0, "unknown": 0}
                ),
                "processing_statistics": {
                    "avg_confidence": analytics_data.get("avg_confidence", 0.0),
                    "success_rate": analytics_data.get("success_rate", 0.0),
                    "high_confidence_count": analytics_data.get(
                        "high_confidence_count", 0
                    ),
                    "medium_confidence_count": analytics_data.get(
                        "medium_confidence_count", 0
                    ),
                    "low_confidence_count": analytics_data.get(
                        "low_confidence_count", 0
                    ),
                },
                # Add top-level fields that frontend expects directly on analytics
                "low_confidence_count": analytics_data.get("low_confidence_count", 0),
                "high_confidence_count": analytics_data.get("high_confidence_count", 0),
                "avg_confidence": analytics_data.get("avg_confidence", 0.0),
            }
            job_data.analytics = structured_analytics
        job_list.append(job_data)

    return JobList(jobs=job_list, total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of results to return"
    ),
    db: AsyncSession = Depends(get_db),
    user_and_ip: tuple = Depends(get_anonymous_or_user),
):
    """Get processing job results as JSON for display"""

    current_user, client_ip = user_and_ip

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )

    # Find job
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found"
        )

    # Check ownership for authenticated users
    if current_user and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this job"
        )

    # Check if job is completed
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status.value}",
        )

    # Check if results file exists
    if not job.result_file_path:
        logger.error("result_file_path_not_set", job_id=job.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results file path not set in database",
        )

    if not os.path.exists(job.result_file_path):
        logger.error(
            "result_file_missing",
            job_id=job.id,
            expected_path=job.result_file_path,
            file_exists=os.path.exists(job.result_file_path),
        )
        # File may have been auto-deleted after 10 minutes
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results file has expired and been deleted. Please process the file again.",
        )

    try:
        pass

        import pandas as pd
        import numpy as np

        # Read the CSV file
        df = pd.read_csv(job.result_file_path)

        # Limit results
        df_limited = df.head(limit)

        # Replace NaN/Inf with None for JSON compatibility
        # NaN and Inf values are not JSON compliant and will cause serialization errors
        # Step 1: Replace Inf values with None
        df_limited = df_limited.replace([np.inf, -np.inf], None)
        # Step 2: Convert to object dtype to allow mixed types (needed for proper None handling)
        df_limited = df_limited.astype(object)
        # Step 3: Replace NaN with None using where (keeps values where condition is True)
        df_limited = df_limited.where(pd.notnull(df_limited), None)

        # Convert to records format for JSON response
        results = df_limited.to_dict("records")

        return {
            "job_id": str(job.id),
            "filename": job.filename,
            "total_rows": len(df),
            "returned_rows": len(results),
            "results": results,
        }

    except Exception as e:
        logger.error("results_parsing_failed", job_id=job.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse results file",
        )


@router.get("/jobs/{job_id}/download")
async def download_results(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_and_ip: tuple = Depends(get_anonymous_or_user),
):
    """Download processing results"""

    current_user, client_ip = user_and_ip

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )

    # Find job
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # Check access permissions
    if current_user:
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    else:
        # Anonymous user - check IP match
        if job.anonymous_ip != client_ip:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    # Check if results are available
    if not job.can_download():
        if job.status != JobStatusEnum.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not completed. Current status: {job.status.value}",
            )
        elif not job.result_file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Results file not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Results have expired"
            )

    # Check if file exists
    if not os.path.exists(job.result_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results file not found on disk",
        )

    # Update download count
    job.download_count += 1
    await db.commit()

    # Generate download filename - always CSV
    original_name_without_ext = os.path.splitext(job.original_filename)[0]
    download_filename = f"tidyframe_results_{original_name_without_ext}_{datetime.now().strftime('%Y%m%d')}.csv"

    # Two-tier download: authenticated users get full data, anonymous users get cleaned columns only
    if current_user:
        # Authenticated user: return full results file with all columns
        logger.info(
            "file_downloaded",
            job_id=job.id,
            user_id=current_user.id,
            download_type="full",
            download_count=job.download_count,
        )

        return FileResponse(
            job.result_file_path, filename=download_filename, media_type="text/csv"
        )
    else:
        # Anonymous user: return cleaned columns only (no original data)
        import tempfile

        import pandas as pd

        try:
            # Read full results file
            df = pd.read_csv(job.result_file_path)

            # Define cleaned columns (processed data only, no original input)
            cleaned_columns = [
                "first_name",
                "last_name",
                "entity_type",
                "gender",
                "gender_confidence",
                "parsing_confidence",
                "parsing_method",
            ]

            # Filter to only columns that exist in the file
            available_cols = [col for col in cleaned_columns if col in df.columns]

            if not available_cols:
                # Fallback: if no cleaned columns found, return minimal data
                available_cols = [col for col in df.columns if col in cleaned_columns]

            df_cleaned = df[available_cols]

            # Create temporary file for cleaned results
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".csv", prefix=f"cleaned_{job_id}_"
            )
            os.close(temp_fd)  # Close the file descriptor, we'll write with pandas

            # Write cleaned data to temp file with UTF-8-sig encoding for Excel compatibility
            df_cleaned.to_csv(temp_path, index=False, encoding="utf-8-sig")

            logger.info(
                "file_downloaded",
                job_id=job.id,
                user_id=None,
                anonymous_ip=client_ip,
                download_type="cleaned",
                columns_included=len(available_cols),
                download_count=job.download_count,
            )

            # Return cleaned file and clean up temp file after response
            response = FileResponse(
                temp_path,
                filename=download_filename,
                media_type="text/csv",
                background=None,  # We'll handle cleanup manually
            )

            # Schedule temp file cleanup after response is sent
            import atexit

            atexit.register(lambda: os.path.exists(temp_path) and os.remove(temp_path))

            return response

        except Exception as e:
            logger.error(
                "anonymous_download_filter_failed", job_id=job.id, error=str(e)
            )
            # Fallback: return full file if filtering fails
            logger.warning("anonymous_download_fallback_to_full", job_id=job.id)
            return FileResponse(
                job.result_file_path, filename=download_filename, media_type="text/csv"
            )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_and_ip: tuple = Depends(get_anonymous_or_user),
):
    """Delete processing job and its files"""

    current_user, client_ip = user_and_ip

    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID format"
        )

    # Find job
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # Check access permissions
    if current_user:
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    else:
        # Anonymous user - check IP match
        if job.anonymous_ip != client_ip:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    # Delete files
    if job.file_path:
        file_service.delete_file(job.file_path)

    if job.result_file_path:
        file_service.delete_file(job.result_file_path)

    # Delete job from database
    await db.delete(job)
    await db.commit()

    logger.info("job_deleted", job_id=job.id)

    return {"message": "Job deleted successfully"}


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(current_user: User = Depends(require_auth)):
    """Get user's usage statistics"""

    remaining = max(0, current_user.monthly_limit - current_user.parses_this_month)
    usage_percentage = (
        current_user.parses_this_month / current_user.monthly_limit
    ) * 100

    # Calculate days until reset
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    days_until_reset = (current_user.month_reset_date - now).days

    return UsageStats(
        parses_this_month=current_user.parses_this_month,
        monthly_limit=current_user.monthly_limit,
        remaining_parses=remaining,
        usage_percentage=usage_percentage,
        days_until_reset=max(0, days_until_reset),
    )
