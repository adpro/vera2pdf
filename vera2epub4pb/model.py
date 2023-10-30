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


@dataclass
class Attachment():
    uid: uuid4
    name: str
    extension: str
    files: list = field(default_factory=list)
    orig_files: list = field(default_factory=list)