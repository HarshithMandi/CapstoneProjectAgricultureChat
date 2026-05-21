"""Script to seed initial agriculture data."""
import asyncio
from app.services.ingest_service import IngestService


AGRICULTURE_URLS = [
    "https://www.fao.org/agriculture/crops/thematicspecies/en/",
    "https://www.agric.wa.gov.au/plant-growing-guides",
]


async def main():
    service = IngestService()
    try:
        for url in AGRICULTURE_URLS:
            print(f"Ingesting: {url}")
            result = await service.ingest_url(url, topic="crops")
            print(f"Created {result['chunks_created']} chunks")
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())