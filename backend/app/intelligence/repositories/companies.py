"""Repository for the owned companies collection."""

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Company
from app.intelligence.repositories.base import Document, Repository


class CompaniesRepository(Repository[Company]):
    collection_name = "companies"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Company)

    async def get_for_company(self, company_id: str) -> Company | None:
        return await self.get(company_id)
