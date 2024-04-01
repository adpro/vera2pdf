import os
import html
import pathlib
import tempfile
import uuid
import tempfile
import platform
import subprocess
import zipfile
import sys
import argparse
import shutil

import pdfkit
import fitz

from io import StringIO, BytesIO
from datetime import datetime

from lxml import etree
from ebooklib import epub
from pikepdf import Pdf, Page   # for rotating pages
from loguru import logger
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup as bs
from unidecode import unidecode

from exceptions import *
from model import *


environment = Environment(loader=FileSystemLoader("../files/"))
template = environment.get_template("front_page.html.j2")
content = template.render(
    no_council_meeting='20. Rady města ,',
    title='TITLE',
    location_and_time='od 16:00 hodin v v zasedací místnosti městského úřadu',
)
shutil.copyfile("../files/css/style_fp.css", "../sample-data/output/tmp/css/style_fp.css")
filepath = os.path.join("../sample-data/output/tmp", "cover.html")
with open(filepath, mode="w", encoding="utf-8") as message:
    message.write(content)
filepath_pdf = os.path.join("../sample-data/output/tmp", "cover.pdf")
options = {
    'page-size': 'A4',
    'margin-top': '0.5in',
    'margin-right': '0.5in',
    'margin-bottom': '0.5in',
    'margin-left': '0.5in',
    'encoding': "UTF-8",
    'enable-local-file-access': None,
    'no-outline': None,
    'orientation': 'Portrait',
    'header-font-name': 'Literata, Times New Roman',
    'header-font-size': 13,    
}
pdfkit.from_file(filepath, 
                    filepath_pdf,
                    options=options,
                    verbose=False)
