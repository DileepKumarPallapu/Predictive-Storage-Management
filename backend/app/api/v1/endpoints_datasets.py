from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import DatasetSource
from app.schemas.payloads import DatasetItem

router = APIRouter()

@router.get("/datasets", response_model=List[DatasetItem])
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(DatasetSource).all()
    return [
        DatasetItem(
            id=ds.id,
            name=ds.name,
            dataset_type=ds.dataset_type,
            records_count=ds.records_count,
            missing_rate=ds.missing_rate,
            sampling_interval_s=ds.sampling_interval_s,
            license=ds.license,
            description=ds.description,
            created_at=ds.created_at
        )
        for ds in datasets
    ]
