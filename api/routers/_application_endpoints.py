# Application Management Endpoints - Append to hirer.py

@router.get("/{job_id}/applications")
async def get_job_applications(
    job_id: str,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,  # TODO: Get from authenticated user
    status_filter: Optional[str] = None  # pending, accepted, rejected
):
    """
    Get all applications for a specific job.
    Only the job owner can view applications.
    """
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # TODO: Add authorization when auth is implemented
    # if owner_id and job.owner_id != owner_id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get applications
    query = select(Application).where(Application.job_id == job_id)
    if status_filter:
        query = query.where(Application.status == status_filter)
    
    applications = session.exec(query.order_by(Application.applied_at.desc())).all()
    
    # Fetch CV details
    applications_with_cv = []
    for app in applications:
        cv = session.exec(select(CV).where(CV.filename == app.cv_id)).first()
        app_dict = {
            "id": app.id,
            "cv_id": app.cv_id,
            "job_id": app.job_id,
            "prediction_id": app.prediction_id,
            "status": app.status,
            "applied_at": app.applied_at,
            "decision_at": app.decision_at,
            "decided_by": app.decided_by,
            "notes": app.notes,
            "candidate": {
                "name": cv.content.get("basics", {}).get("name", "Unknown") if cv else "Unknown",
                "email": cv.content.get("basics", {}).get("email", "") if cv else "",
                "summary": cv.content.get("basics", {}).get("summary", "") if cv else "",
                "skills": cv.content.get("skills", []) if cv else [],
                "work": cv.content.get("work", [])[:2] if cv else []  # First 2 work experiences
            } if cv else None
        }
        applications_with_cv.append(app_dict)
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "applications": applications_with_cv,
        "count": len(applications_with_cv)
    }


@router.post("/{job_id}/applications/{application_id}/accept")
async def accept_application(
    job_id: str,
    application_id: int,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,  # TODO: Get from authenticated user
):
    """Accept a job application (owner only)."""
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get application
    application = session.exec(
        select(Application).where(
            Application.id == application_id,
            Application.job_id == job_id
        )
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"Application already {application.status}")
    
    # Update application
    application.status = "accepted"
    application.decision_at = datetime.utcnow()
    application.decided_by = owner_id
    session.add(application)
    session.commit()
    
    # Log interaction as 'hired'
    user_id_int = hash(application.cv_id) % (10 ** 8)
    interaction = UserInteraction(
        user_id=user_id_int,
        job_id=job_id,
        action="hired",
        strategy="pgvector",
        metadata={
            "prediction_id": application.prediction_id,
            "cv_id": application.cv_id,
            "application_id": application.id
        }
    )
    session.add(interaction)
    session.commit()
    
    logger.info(f"Application {application_id} accepted for job {job_id}")
    
    return {"status": "success", "message": "Application accepted"}


@router.post("/{job_id}/applications/{application_id}/reject")
async def reject_application(
    job_id: str,
    application_id: int,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,
):
    """Reject a job application (owner only)."""
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get application
    application = session.exec(
        select(Application).where(
            Application.id == application_id,
            Application.job_id == job_id
        )
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"Application already {application.status}")
    
    # Update application
    application.status = "rejected"
    application.decision_at = datetime.utcnow()
    application.decided_by = owner_id
    session.add(application)
    session.commit()
    
    # Log interaction as 'rejected'
    user_id_int = hash(application.cv_id) % (10 ** 8)
    interaction = UserInteraction(
        user_id=user_id_int,
        job_id=job_id,
        action="rejected",
        strategy="pgvector",
        metadata={
            "prediction_id": application.prediction_id,
            "cv_id": application.cv_id,
            "application_id": application.id
        }
    )
    session.add(interaction)
    session.commit()
    
    logger.info(f"Application {application_id} rejected for job {job_id}")
    
    return {"status": "success", "message": "Application rejected"}
