from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class ProgrammeHeader():
    title: str = ""
    no_council_meeting: str = ""
    location_and_time: str = ""


@dataclass
class ProgrammeItem():
    id: int = 0                 # cislo
    name: str = ""              # nazev
    time: str = ""              # cas
    resolution: str = ""        # navrh usneseni
    presenter: str = ""         # predkladatel
    processor: str = ""         # zpracovatel
    reason_text: str = ""       # text duvodove zpravy
    attachments: list = field(default_factory=list)      # prilohy s nazvy
    link: str = ""              # odkaz na usneseni
    temp_link: str = ""         # cesta k docasnemu html souboru s upravami
    pdf_temp_file: str = ""     # cesta k docasnemu pdf souboru s upravami
    pdf_start_page: int = 0     # cislo stranky se zacatkem bodu v pdf dokumentu


@dataclass
class Attachment():
    uid: uuid4
    name: str
    extension: str
    files: list = field(default_factory=list)
    orig_files: list = field(default_factory=list)