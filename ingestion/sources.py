from dataclasses import dataclass
from pathlib import Path

from schema import GoverningBody


@dataclass
class SourceConfig:
    path: Path
    governing_body: GoverningBody
    year: int

    @property
    def source_doc(self) -> str:
        return self.path.stem


SOURCES: list[SourceConfig] = [
    SourceConfig(Path("/app/pdfs/2026-DYB-Official-Playing-Rules.pdf"), GoverningBody.DYB, 2026),
    SourceConfig(Path("/app/pdfs/2026-DYS-Official-Playing-Rules.pdf"), GoverningBody.DYS, 2026),
    SourceConfig(Path("/app/pdfs/2026-official-baseball-rules.pdf"), GoverningBody.OBR, 2026),
    SourceConfig(Path("/app/pdfs/2026-NFHS-softball-rules.md"), GoverningBody.NFHS_SOFTBALL, 2026),
]
