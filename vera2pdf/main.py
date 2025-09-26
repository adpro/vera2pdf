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

from loguru import logger
from lxml import etree
from jinja2 import Environment, FileSystemLoader
from unidecode import unidecode
from bs4 import BeautifulSoup as bs

from exceptions import *
from model import *


def get_programme_path():
    global input_path
    if len(input_path) > 0:
        return input_path
    env_var_name = 'VERA_PROGRAMME_PATH'
    if os.environ.get(env_var_name) != None:
        return str(os.environ.get(env_var_name))
    raise NoInputParameterError


def get_html_root(filepath) -> etree:
    parser = etree.HTMLParser()
    text = None
    with open(filepath, encoding = 'utf-8') as f:
        text = html.unescape(f.read())
    tree = etree.parse(StringIO(text), parser)
    root = tree.getroot()
    return root


def remove_spaces(txt:str) -> str:
    if txt is not None:
        return ' '.join(txt.strip().replace('\\t',' ').replace('\\n',' ').split())
    return ""


def parse_programme_header(root) -> ProgrammeHeader:
    header = ProgrammeHeader()
    rows = root.xpath('//table[@class="hlavicka"]/tr/td')
    if rows == None:
        rows = root.xpath('//table[@class="hlavicka"]/tbody/tr/td')
    if len(rows) < 5:
        raise WrongProgrammeFormatError
    # logger.error(f'Header rows: {[x.text for x in rows]}')
    header.title = remove_spaces(rows[3].text)
    header.no_council_meeting = remove_spaces(rows[4].text)
    header.time = remove_spaces(rows[5].text)
    header.location = remove_spaces(rows[6].text)
    return header


def get_element_text_from_html(root, xpath) -> str:
    rows = root.xpath(xpath)
    if len(rows) == 1:
        siblings = list(rows[0].itersiblings())
        if len(siblings) == 1:
            return remove_spaces(siblings[0].text)
    return ""


def get_element_alltext_from_html(root, xpath) -> str:
    rows = root.xpath(xpath)
    if len(rows) == 1:
        siblings = list(rows[0].itersiblings())
        if len(siblings) == 1:
            return remove_spaces('<br/> '.join(siblings[0].itertext()))
    return ""


def get_element_statements_text_from_html(root, xpath) -> str:
    rows = root.xpath(xpath)
    if len(rows) == 1:
        siblings = list(rows[0].itersiblings())
        txt = ''
        for item in siblings:
            if item.tag == 'div':
                txt += ' ' + remove_spaces(' '.join(item.itertext()))
        return txt
    return ""


def get_libre_office_path():
    if platform.system() == 'Darwin':
        path = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    elif platform.system() == 'Windows':
        path = 'C:\Program Files\LibreOffice\program\soffice.exe'
    elif platform.system() == 'Linux':
        path = '/usr/lib/libreoffice/program/'
    if not os.path.exists(path):
        raise LibreOfficeNotFoundError
    return path


def convert_file_to_supported_type(old_filepath, tmp_path) -> str:
    ext = pathlib.Path(old_filepath).suffix.lower()
    filename = pathlib.Path(old_filepath).stem
    new_filename = '.'.join([filename,'pdf'])
    tmp_attachments_path = os.path.join(tmp_path, "attachments")
    if not os.path.exists(tmp_attachments_path):
        os.makedirs(tmp_attachments_path)
    new_filepath = os.path.join(tmp_attachments_path, new_filename)
    new_path = os.path.dirname(new_filepath)
    if ext in ['.docx', '.doc', '.odt', 
               '.xls', '.xlsx', '.ods',
               '.ppt', '.pptx', '.odp',
               '.txt'
               ]:
        logger.info(f'\tConverting {os.path.basename(old_filepath)} to {os.path.basename(new_filepath)} by LibreOffice...')
        if not os.path.exists(old_filepath):
            logger.error(f'File to convert {new_filepath} does not exists.')
        subprocess.call([get_libre_office_path(), '--headless', '--convert-to', 'pdf', old_filepath, '--outdir', new_path]
                        , stdout=subprocess.DEVNULL 
                        , stderr=subprocess.STDOUT)
        if os.path.exists(new_filepath):
            return new_filepath, 'pdf'
        else:
            logger.error(f'Converted file {new_filepath} does not exists.')
            return new_filepath, 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff','.psd']:
        logger.info(f'\tConverting {os.path.basename(old_filepath)} to {os.path.basename(new_filepath)} by PyMuPDF...')
        doc = fitz.open()
        img = fitz.open(old_filepath)  # open pic as document
        rect = img[0].rect  # pic dimension
        pdfbytes = img.convert_to_pdf()  # make a PDF stream
        img.close()  # no longer needed
        imgPDF = fitz.open("pdf", pdfbytes)  # open stream as PDF
        width, height = fitz.paper_size("a4")  # A4 portrait output page format
        page = doc.new_page(width = width, height = height)
        insert_rect = fitz.Rect(18,18,page.rect.br[0]-18,page.rect.br[1]-18)    # 18 points margin around page
        mat = rect.torect(insert_rect)  # create Matrix to scale image to A4 page
        page.show_pdf_page(rect * mat, imgPDF)  # image fills the page with scale (mat)
        doc.save(new_filepath, garbage=4, deflate=True)
        doc.close()
        return new_filepath, 'pdf'
    else:
        new_filename = '.'.join([filename,ext[1:]])
        new_filepath = os.path.join(tmp_attachments_path, new_filename)
        logger.info(f'\tCopying {os.path.basename(old_filepath)} to temp folder...')
        shutil.copyfile(old_filepath, new_filepath)
        return new_filepath, ext[1:]


def get_attachments_from_html(root, xpath, path) -> str:
    rows = root.xpath(xpath)
    attachments = []
    if len(rows) == 1:
        siblings = list(rows[0].itersiblings())
        if len(siblings) == 1:
            el = siblings[0]
            a_tags =  list(filter(lambda x: (x.tag == 'a'), el))
            for tag in a_tags:
                full_path = os.path.normpath(os.path.join(os.path.dirname(path), tag.attrib["href"]))
                ext = pathlib.Path(full_path).suffix.lower()
                attachments.append(Attachment(uuid.uuid4(),tag.text, ext, [full_path], [full_path]))
            return attachments
    return ""


def parse_item_page(item):
    root = get_html_root(item.link)
    item.presenter = get_element_text_from_html(root, '//td[@class="predkladatelLabel"]')
    item.processor = get_element_text_from_html(root, '//td[text()="Zpracovatel:"]')
    item.reason_text = get_element_alltext_from_html(root, '//td[text()="Text důvodové zprávy:"]')
    item.resolution = get_element_statements_text_from_html(root, '//div[@class="prohlaseni"]')
    item.attachments = get_attachments_from_html(root, '//td[text()="Materiál obsahuje:"]', item.link)


def process_item_w_link(el, item):
    for x in el:
        if x.tag == 'a':
            item.name = remove_spaces(x.text)
            item.link = os.path.normpath(os.path.join(get_programme_path(),x.attrib['href']))
    parse_item_page(item)


def process_item_wo_link(el, item):
    item.name = remove_spaces(el.text)
    if len(list(el.itertext())) < 5:
        raise WrongProgrammeFormatError
    item.presenter = remove_spaces(list(el.itertext())[3]).replace(": ","")


def parse_programme_item(el) -> ProgrammeItem:
    item = ProgrammeItem()
    if len(el) != 2: # old 3: # older 4:
        logger.error(f'Wrong programme Format. el: {el}')
        raise WrongProgrammeFormatError
    # id
    item.id = remove_spaces(el[0].text.replace('.',''))    

    # name
    if el[1].text == None:  # with href link to more info
        process_item_w_link(el[1], item)
    else:   # no link to more info
        process_item_wo_link(el[1], item)
    
    # time
    item.time = '' # remove_spaces(el[2].text)
    
    return item


def parse_programme_items(root) -> list:
    p_list = []
    rows = root.xpath('//table[@class="program"]/tr')
    for row in rows:
        if len(rows) > 0 and row == rows[0]:
            continue
        item = parse_programme_item(row)
        p_list.append(item)
    return p_list


def parse_programme(filepath:str):
    root = get_html_root(filepath)
    p_header = parse_programme_header(root)
    p_list_items = parse_programme_items(root)
    return p_header, p_list_items


def encode_charset(s, charset='cp852'):
    filename_bytes = unidecode(s).encode('437')
    guessed_encoding = charset # chardet.detect(filename_bytes)['encoding'] or 'cp1252'
    filename = filename_bytes.decode(guessed_encoding, 'replace')
    return filename


def get_zipped_normalized_filename(filename):
    path = filename.split(os.sep)
    new_paths = []
    for name in path:
        new_name = '-'.join(name.split())
        new_paths.append(new_name)
    return '_'.join(new_paths)


def extract_zip_files(items, tmp_dir):
    updated_p_items = []
    for p_item in items:
        upd_attachments = []
        for attachment in p_item.attachments:
            if len(attachment.files) == 1:
                filepath = attachment.files[0]
                ext = pathlib.Path(filepath).suffix.lower()
                if ext == '.zip':
                    with zipfile.ZipFile(filepath, 'r') as zipobject:
                        extract_list = zipobject.namelist()
                        for file in extract_list:
                            logger.trace(f'Extracting {file} from {filepath}..')
                            zip_filename = encode_charset(file)
                            filename = get_zipped_normalized_filename(zip_filename)
                            filepath_extract = os.path.normpath(os.path.join(tmp_dir.name, filename))
                            with open(filepath_extract, 'wb') as f:
                                f.write(zipobject.read(file))
                            if os.path.isdir(filepath_extract):
                                continue
                            if os.stat(filepath_extract).st_size == 0:
                                continue
                            # zipobject.extract(file, filepath_extract)
                            ext_extract = pathlib.Path(filepath_extract).suffix.lower()
                            upd_attachments.append(Attachment(
                                        uuid.uuid4(),
                                        attachment.name + file,
                                        ext_extract,
                                        [filepath_extract]))
                else:
                    upd_attachments.append(attachment)
        upd_p_item = ProgrammeItem(p_item.id,
                                    p_item.name,
                                    p_item.time,
                                    p_item.resolution,
                                    p_item.presenter,
                                    p_item.processor,
                                    p_item.reason_text,
                                    upd_attachments,
                                    p_item.link)
        updated_p_items.append(upd_p_item)
    return updated_p_items


def convert_files_to_pdf(items, tmp_path):
    updated_p_items = []
    for p_item in items:
        upd_attachments = []
        for attachment in p_item.attachments:
            if len(attachment.files) == 1:
                full_path = attachment.files[0]
                new_path, ext = convert_file_to_supported_type(full_path, tmp_path)
                upd_attachments.append(Attachment(
                                        uuid.uuid4(),
                                        attachment.name,
                                        ext,
                                        [new_path],
                                        attachment.orig_files))
        upd_p_item = ProgrammeItem(p_item.id,
                                    p_item.name,
                                    p_item.time,
                                    p_item.resolution,
                                    p_item.presenter,
                                    p_item.processor,
                                    p_item.reason_text,
                                    upd_attachments,
                                    p_item.link)
        updated_p_items.append(upd_p_item)
    return updated_p_items


def debug_print_items_attachments(items):
    for p_item in items:
        logger.trace(f'DEBUG attachments {p_item.id}')
        for attachment in p_item.attachments:
            logger.trace(f'\t{attachment}')

# ====================== single PDF output file ======================

def get_pdf_ebook_name(header) -> str:
    if 'rozpo' in header.no_council_meeting.lower():
        year = header.time.split()[2]
        cur_date = datetime.today().strftime('%Y%m%d')
        return f'Rozpocet_{year}_A4_{cur_date}.pdf'
    else:
        if 'zastupit' in header.no_council_meeting.lower():
            prefix = 'ZM_'
        if 'rad' in header.no_council_meeting.lower():
            prefix = 'RM_'
        # logger.error(f'Time: {header.time}')
        # logger.error(f'Loc: {header.location}')
        date_of_meeting = header.time.split()[3].split('.')
        month = '0'+date_of_meeting[1] if int(date_of_meeting[1])<10 else date_of_meeting[1]
        day = '0'+date_of_meeting[0] if int(date_of_meeting[0])<10 else date_of_meeting[0]
        return f'{prefix}{date_of_meeting[2]}-{month}-{day}_A4.pdf'


def create_html_page(item, filepath, header):
    environment = Environment(loader=FileSystemLoader("../files/"))
    template = environment.get_template("programme_item.html.j2")
    content = template.render(
        id=item.id,
        no_council_meeting=header.no_council_meeting,
        title=header.title,
        time=header.time,
        name=item.name,
        presenter=item.presenter
    )
    with open(filepath, mode="w", encoding="utf-8") as message:
        message.write(content)


def copy_html_to_temp_folder(tmp_path, items, header):
    html_filepath = os.path.join(tmp_path, "html")
    if not os.path.exists(html_filepath):
        os.makedirs(html_filepath)
    css_filepath = os.path.join(tmp_path, "css")
    if not os.path.exists(css_filepath):
        os.makedirs(css_filepath)
    fonts_filepath = os.path.join(tmp_path, 'fonts')
    # if not os.path.exists(fonts_filepath):
    #     os.makedirs(fonts_filepath)
    shutil.copytree('../files/fonts', fonts_filepath)
    css_file_path = os.path.join(css_filepath, "style.css")
    logger.trace(f'CSS sample source: {os.path.exists("../files/css/style.css")}')
    logger.trace(f'CSS sample target: {css_filepath} {os.path.exists(css_filepath)}')
    logger.trace(f'CSS sample file target: {css_file_path}')
    shutil.copyfile("../files/css/style.css", css_file_path)
    for item in items:
        if len(item.link) > 1:
            filename = os.path.basename(item.link)
            filepath = os.path.join(html_filepath, filename)
            shutil.copyfile(item.link, filepath)
        else:
            filename = f"pitem_{item.id}.html"
            filepath = os.path.join(html_filepath, filename)
            create_html_page(item, filepath, header)
        item.temp_link = filepath
        if os.path.exists(filepath):
            logger.trace(f"Html of programme item written to {filepath}.")
        else:
            logger.error(f'Error in copying programme item html to temp dir to {filepath}.')


def edit_programme_item_html(item):
    html = open(item.temp_link)
    soup = bs(html, 'html.parser')
    logger.trace(f'Editing html in {item.temp_link} in {item.id}')
    # change podpisy to voting
    element = soup.find("table", {"class": "podpisy"})
    new_content = bs('<table class="podpisy"><tr><td>Hlasování:</td><td>Pro ____ </td><td>Proti ____ </td><td>Zdržel se: ____ </td><td>Nehlasoval: ____ </td></tr></table><table class="podpisy"><tr><td width="30%">Usnesení přijato:</td><td width="20%">&#9634; ANO</td><td width="20%">&#9634; NE</td><td width="30%">&#9634; Staženo</td></tr></table><hr class="cela">', 'html.parser')
    if element is None:
        logger.error(f'Table class podpisy not found in item {item.id} in file {os.path.basename(item.temp_link)}.')
    else:
        element.replace_with(new_content)
    # add notes to the end
    # element = soup.find("table", {"class": "akteri"})
    element = soup.find_all("hr", {"class": "cela"})[-1]
    new_content = bs('<table cellspacing="10" class="akteri"><tr><td style="vertical-align:top;color: blue;">Pozn&aacute;mky:</td><td><br><br><br></td></tr></table>', 'html.parser')
    element.insert_after(new_content)
    # add programme item number to tile
    element = soup.find("div", {"class": "nadpis"})
    element.string.replace_with(f'{item.id}. {element.string}')
    # add bookmark to top of page
    element = soup.find("div", {"id": "content"})
    bookmark1 = bs(f'<div id="pitem_{item.id}"></div>', 'html.parser')
    element.insert_before(bookmark1)
    # add bookmark to attachment section
    element = soup.find("table", {"class": "akteri"})
    logger.trace(f'ELEMENT text AKTERI: {element.find_all(string=True)}')
    text = element.find(string="Materiál obsahuje:")
    if text is None:
        logger.error(f'Could not find Přílohy part of page. Skipping adding bookmark.')
    else:
        bookmark2 = bs(f'<div id="pitem_{item.id}_attachments"></div>', 'html.parser')
        text.insert_after(bookmark2)
    # remove style attributes
    remove_attributes = ['style','font','face','size','color']    
    for tag in soup.descendants:
        try:
            # logger.error(f'tag.attrs type {type(tag.attrs), {tag}}')
            tag.attrs = dict((key,value) for key,value in tag.attrs.items()
                        if key not in remove_attributes)
        except AttributeError: 
            # 'NavigableString' object has no attribute 'attrs'
            pass    

    # close and save
    html.close()
    content = soup.prettify("utf-8")
    with open(item.temp_link, "wb") as file:
        file.write(content)


def print_programme_item(item, tmp_path):
    filepath_pdf = os.path.join(tmp_path, f"pitem_{item.id}.pdf")
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
    pdfkit.from_file(item.temp_link, 
                     filepath_pdf, 
                     options=options,
                     verbose=False)
    if os.path.exists(filepath_pdf):
        logger.info(f"\tProgramme item written in {os.path.basename(filepath_pdf)}.")
    else:
        logger.error(f'Something wrong during programme item writing to {filepath_pdf}.')
    return filepath_pdf


def rotate_landscape_pdf_file(attachment):
    if len(attachment.files) == 1:
        flag = 0
        filepath = attachment.files[0]
        ext = pathlib.Path(filepath).suffix.lower()
        if ext == '.pdf':
            doc = fitz.open(filepath)
            for page in doc:
                logger.trace(f'File {os.path.basename(filepath)}, page {page.number}, rotation {page.rotation} deg, mediabox: {page.mediabox_size}, cropbox: {page.cropbox} WxH {page.cropbox.width}x{page.cropbox.height}, rect: {page.rect}, width={page.rect.width}, height={page.rect.height}, top-left corner at {fitz.Point(0,0) * page.rotation_matrix}')
                if page.rect.width > page.rect.height:    # landscape
                    if flag == 0:
                        logger.debug(f'\tRotating {filepath}')
                        flag = 1                      
                    logger.trace(f'Rotating {os.path.basename(filepath)}, page {page.number}, rect: {page.rect}, width={page.rect.width}, height={page.rect.height}, top-left corner at {fitz.Point(0,0) * page.rotation_matrix}')                    
                    if page.rotation in (90,270):
                        page.set_rotation(0)
                    else:
                        page.set_rotation(270)
                    logger.trace(f'After rotation of {os.path.basename(filepath)}, page {page.number}, rect: {page.rect}, width={page.rect.width}, height={page.rect.height}, top-left corner at {fitz.Point(0,0) * page.rotation_matrix}')
            doc.save(filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            doc.close()


def repair_pdf_if_needed(attachment, tmp_path):
    filepath = os.path.join(tmp_path, "attachments")
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    for i in range(len(attachment.files)):
        logger.trace(f'Attachment {attachment}')
        logger.trace(f'Attachment files list, list item {attachment.files[i]}')
        att_doc = fitz.open(attachment.files[i])
        if not att_doc.can_save_incrementally():
            # logger.trace(f'Attachment {attachment.files[i]} had been repaired by PyMuPDF. Warnings: {fitz.Tools.mupdf_warnings()}')
            logger.trace(f'Attachment {attachment.files[i]} had been repaired by PyMuPDF.')
            c = att_doc.tobytes(garbage=3, deflate=True)
            del att_doc
            filename = pathlib.Path(attachment.files[i]).stem
            new_filename = f'{filename}_{i}.pdf'
            att_doc_new = fitz.Document(stream=BytesIO(c))
            new_filepath = os.path.join(filepath, new_filename)
            att_doc_new.save(new_filepath)
            attachment.files[i] = new_filepath


def join_attachment_pdf_files(attachment, tmp_path):
    if len(attachment.files) > 1:
        doc = fitz.open(attachment.files[0])
        for i in range(1, len(attachment.files)):
            att_doc = fitz.open(attachment.files[i])
            doc.insert_pdf(att_doc)
            att_doc.close()
        doc.save(attachment.files[0], incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        pages_no = len(doc)
        doc.close()
        attachment.files = [attachment.files[0]]
        return pages_no
    elif len(attachment.files) == 1:
        doc = fitz.open(attachment.files[0])
        pages_no = len(doc)
        doc.close()
        return pages_no
    else:
        return 0


def add_header_to_attachment(item, attachment):
    for f in attachment.files:
        logger.info(f"\t\tAdding header to attachment {os.path.basename(f)}.")
        doc = fitz.open(f)
        page_count = doc.page_count
        for i in range(page_count):
            page = doc[i]
            if not page.is_wrapped:
                page.wrap_contents()
            # r = fitz.Rect(36,18,536,36)  # rectangle
            page = doc[i]
            # get scale to A4
            a4_height = fitz.paper_size('a4')[1]    # get height from (width, height) tuple
            page_height = page.rect.height
            scale = page_height/a4_height
            # positioning and drawing
            r = fitz.Rect(0, page.rect.height-(18*scale), page.rect.width, page.rect.height)  # rectangle shape
            r2 = fitz.Rect((36*scale), page.rect.height-(18*scale), page.rect.width-(36*scale), page.rect.height)  # rectangle text
            r_rot = r * page.derotation_matrix
            r_rot2 = r2 * page.derotation_matrix
            shape = page.new_shape()  # create Shape
            shape.draw_rect(r_rot)  # draw rectangles
            shape.finish(width = 0.0, color = (0,0,0), fill = (1,1,1))
            logger.trace(f'Header placement: file {os.path.basename(f)}, page {page.number}, rotation={page.rotation}, page.rect={page.rect}, r={r}, r_rot={r_rot}')
            rotate_text = 0
            if r2 != r_rot2:
                rotate_text = page.rotation
            fontsize = 11*scale
            text = f'{item.name} # {attachment.name}'
            if len(text) > 105:
                text = f'{item.name[:25]} # {attachment.name[:80]}'
            t = unidecode(f'Strana {page.number+1} z {len(doc)} # Bod {item.id} - {text}')
            rc = shape.insert_textbox(r_rot2, t, color = (0,0,0), encoding=fitz.TEXT_ENCODING_LATIN, fontname='TiRo', fontsize=fontsize, rotate=rotate_text)
            shape.commit()  # write all stuff to page /Contents

            doc.save(f, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        doc.close()


def join_with_programme_item(attachment, pitem_pdf, pdf_file):
    if len(attachment.files) > 0:
        doc = fitz.open(attachment.files[0])
        pitem_pdf.insert_pdf(doc)
        doc.close()
        pitem_pdf.save(pdf_file, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)

        # main_doc = fitz.open(pdf_file)
        # doc = attachment.files[0]
        # main_doc.insert_pdf(doc)
        # doc.close()
        # main_doc.save(pdf_file, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        # main_doc.close()


def update_programme_item_links_to_local(pitem_pages_no, doc, pdf_file, item, attachments_pages_no):
    used = 0
    logger.trace(f'Linking programme item file {item.id} with inserted attachments. Doc pages: {len(doc)}')
    for p_index in range(pitem_pages_no):
        links = doc[p_index].get_links()
        logger.trace(f'LINKS in programme item {item.id}, page {doc[p_index]} {p_index}: {doc[p_index].get_links()}')
        for i in range(len(links)):
            link_dict = links[i]
            link_dict['kind'] = fitz.LINK_GOTO
            link_dict['page'] = min(pitem_pages_no + sum(attachments_pages_no[:used]), len(doc)-1)
            logger.trace(f'Update link dict: {link_dict}, doc pages: {len(doc)}')
            used += 1
            doc[p_index].update_link(link_dict)
    for p_index in range(pitem_pages_no, min(pitem_pages_no + sum(attachments_pages_no), len(doc))):
        logger.trace(f'Adding "Zpet" link.. p_index: {p_index}, pitem_pages_no: {pitem_pages_no}, whole pages: {pitem_pages_no + sum(attachments_pages_no)}, doc pages: {len(doc)}')
        page = doc[p_index]
        # get scale to A4
        a4_height = fitz.paper_size('a4')[1]    # get height from (width, height) tuple
        page_height = page.rect.height
        scale = page_height/a4_height
        # drawing back link
        rect = page.bound() # get page dimensions
        r = fitz.Rect(page.rect.width-(200*scale), page.rect.height-(118*scale), page.rect.width, page.rect.height)  # rectangle
        r_rot = r * page.derotation_matrix
        # shape = page.new_shape()  # create Shape
        # shape.draw_rect(r_rot)  # draw rectangles
        # shape.finish(width = 0.6, color = (0,1,0))
        # shape.commit()  # write all stuff to page /Contents
        link_dict = {'kind': fitz.LINK_GOTO, 'from': r_rot, 'page': 0}
        page.insert_link(link_dict)
        
        link_rect = fitz.Rect(page.rect.bl[0],page.rect.bl[1]-118,page.rect.bl[0]+200,page.rect.bl[1]) * page.rotation_matrix
        logger.trace(f'2nd link rect: {link_rect}')
        link_dict = {'kind': fitz.LINK_GOTO, 'from': link_rect, 'page': 0}
        page.insert_link(link_dict)

    doc.save(pdf_file, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)


def create_programme_item_pdfs(header, items, tmp_dir):
    # zkopírovat html s navrhy usneseni a upravit cesty v seznamu
    # pres polozky
    #   upravit obsah pro hlasovani a poznamky
    #   vytisknout jako PDF a ulozit do TMP, aktualizovat odkaz na dokument
    #   zjistit pocet stranek PDF souboru s programovym bodem
    #   pres pocet priloh
    #       zjistit inkrementalni ulozeni souboru
    #       pokud ne, preulozit a nahradit odkaz
    #       zjistit pocet stran
    #       doplnit do prilohy hlavicku
    #       sloucit s pdf program. bodu
    #       na strany priloh doplnit odkaz na stranu 1 programoveho bodu
    #       na stranu seznamu priloh doplnit odkaz na prilohu
    #       aktualizovat stranku na pdf_start_page
    copy_html_to_temp_folder(tmp_dir, items, header)
    for item in items:  # over programme items
        if len(item.link) > 1:
            edit_programme_item_html(item)
        pdf_file = print_programme_item(item, tmp_dir)
        item.pdf_temp_file = pdf_file
        doc = fitz.open(pdf_file)
        pdf_pitem_pages_no = doc.page_count
        attachments_pages_no = []
        for attachment in item.attachments:
            repair_pdf_if_needed(attachment, tmp_dir)
            pdf_att_pages_no = join_attachment_pdf_files(attachment, item)
            attachments_pages_no.append(pdf_att_pages_no)
            rotate_landscape_pdf_file(attachment)            
            add_header_to_attachment(item, attachment)
            join_with_programme_item(attachment, doc, pdf_file)
        # update links in joined programme item with attachments
        update_programme_item_links_to_local(pdf_pitem_pages_no, doc, pdf_file, item, attachments_pages_no)
        doc.close()
    logger.trace(f'Programme items pdfs: {[item.pdf_temp_file for item in items]}')


def update_index_html(index_filepath, tmp_path, header, items):
    tmp_index_filepath = os.path.join(tmp_path, os.path.basename(index_filepath))
    shutil.copyfile(index_filepath, tmp_index_filepath)
    html = open(tmp_index_filepath)
    soup = bs(html, 'html.parser')
    elmnts = soup.find("tr", {"class": "popisek"}).find_all_next("td", {"class": "left"})
    for i in range(len(elmnts)):
        if i == 0:
            continue
        if elmnts[i].a == None:
            tag = soup.new_tag('a')
            tag.string = elmnts[i].contents[0]
            tag.attrs['href'] = f"html/pitem_{i}.html"
            elmnts[i].contents[0].replace_with(tag)
    # remove style attributes
    remove_attributes = ['style','font','face','size','color']    
    for tag in soup.descendants:
        try:
            # logger.error(f'tag.attrs type {type(tag.attrs), {tag}}')
            tag.attrs = dict((key,value) for key,value in tag.attrs.items()
                        if key not in remove_attributes)
        except AttributeError: 
            # 'NavigableString' object has no attribute 'attrs'
            pass    
    html.close()
    content = soup.prettify("utf-8")
    with open(tmp_index_filepath, "wb") as file:
        file.write(content)
    # logger.trace(f'Index - elements: {[e.contents[0] for e in elmnts]}')
    # logger.trace(f'Index - elements.a: {[e.a for e in elmnts]}')
    return tmp_index_filepath


def print_programme(header, tmp_path, tmp_index_filepath):
    filepath_pdf = os.path.join(tmp_path, "index.pdf")
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
    pdfkit.from_file(tmp_index_filepath, 
                     filepath_pdf,
                     options=options,
                     verbose=False)
    if os.path.exists(filepath_pdf):
        logger.info(f"\tProgramme written in {os.path.basename(filepath_pdf)}.")
    else:
        logger.error(f'Something wrong during programme writing to {filepath_pdf}.')
    return filepath_pdf


def join_pdf_programme_with_items(index_pdf, header, items, tmp_path):
    joined_pdf = os.path.join(tmp_path, get_pdf_ebook_name(header))
    index_pdf = fitz.open(index_pdf)
    pages = []
    pages.append(len(index_pdf))
    for item in items:
        doc = fitz.open(item.pdf_temp_file)
        pages.append(len(doc))
        index_pdf.insert_pdf(doc)
        doc.close()
    index_pdf.save(joined_pdf, encryption=fitz.PDF_ENCRYPT_KEEP)
    index_pdf.close()
    logger.trace(f'Pages counts: {pages}')
    return joined_pdf, pages


def create_pdf_shape_link(page, width, pos_y, text):
    rect = page.bound() # get page dimensions
    margin_left = 32
    size = 20
    # r = fitz.Rect(rect.width-width-margin_left,
    #               pos_y,
    #               rect.width-margin_left,
    #               pos_y+size)  # rectangle
    r = fitz.Rect(rect.width-(width+margin_left),pos_y,rect.width-8,pos_y+size)  # rectangle
    # r = fitz.Rect(margin_left,
    #               pos_y,
    #               width+margin_left,
    #               pos_y+size)  # rectangle
    logger.trace(f'Inserting shape for link {text} on page {page.number} with rectangle {page.rect}. Page bounds: ({rect.width}, {rect.height}). Result rect({r.x0},{r.y0},{r.x1},{r.y1}).')
    shape = page.new_shape()  # create Shape
    shape.draw_rect(r)  # draw rectangles
    shape.finish(width = 0.3, color = (0,0,0), fill = (0.8,0.8,0.8))
    t = unidecode(text)
    rc = shape.insert_textbox(r, t, color = (0,0,0), encoding=fitz.TEXT_ENCODING_LATIN, fontname='TiRo')
    shape.commit()  # write all stuff to page /Contents
    return r


def update_links_in_joined_pdf(joined_pdf, pages):
    link_height = 128
    doc = fitz.open(joined_pdf)
    logger.trace(f'Linking programme to programme items pages. Pages: {pages}, sums: {[sum(pages[:i]) for i in range(len(pages))]}')
    idx = 0
    for p_index in range(pages[0]):
        links = doc[p_index].get_links()
        logger.trace(f'LINKS in index page {p_index}: {doc[p_index].get_links()}')
        for i in range(len(links)):
            link_dict = links[i]
            link_dict['kind'] = fitz.LINK_GOTO
            link_dict['page'] = sum(pages[:idx+i+1])
            logger.trace(f'Update link dict: {link_dict}')
            doc[p_index].update_link(link_dict)
            # insert backlink
            page = doc[sum(pages[:idx+i+1])]
            p = fitz.Point(0, 0)
            logger.trace(f'Program link. Page bounds: {page.rect}. Top-left (0,0): {p * page.rotation_matrix}')
            # link to programme page from top-center
            link_dict2 = {'kind': fitz.LINK_GOTO, 'from': fitz.Rect(200,0,400,link_height), 'page': p_index}
            page.insert_link(link_dict2)
        idx += len(links)
    doc.save(joined_pdf, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    logger.trace(f'Linking programme items to other programme items (prev/next).')
    for i in range(len(pages)-1):
        # if i == len(pages) - 2:
        #     page = doc[sum(pages[:i+1])-1]
        # else:
        page = doc[sum(pages[:i+1])]
        if i == 0:
            # Next
            link_dict = {'kind': fitz.LINK_GOTO, 'from': fitz.Rect(420,0,page.rect.width,link_height), 'page': sum(pages[:i+2])}
            page.insert_link(link_dict)
        else:
            if len(doc)-1 > page.number:
                # Next
                page_number = sum(pages[:i+2])
                if page_number > len(doc)-1:
                    page_number = len(doc)-1
                link_dict = {'kind': fitz.LINK_GOTO, 'from': fitz.Rect(420,0,page.rect.width,link_height), 'page': page_number}
                logger.trace(f'Programme item Next link dict: {link_dict} from page {page.number}')
                page.insert_link(link_dict)
            # Previous
            link_dict2 = {'kind': fitz.LINK_GOTO, 'from': fitz.Rect(0,0,180,link_height), 'page': sum(pages[:i])}
            page.insert_link(link_dict2)
    doc.save(joined_pdf, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()


def create_programme_index_pdf(index_filepath, tmp_path, header, items):
    logger.info(f'\tUpdating HTML programme in index.html, inserting links to programme items...')
    tmp_index_filepath = update_index_html(index_filepath, tmp_path, header, items)
    logger.info(f'\tPrinting programme to PDF...')
    index_pdf = print_programme(header, tmp_path, tmp_index_filepath)
    logger.info(f'\tJoining programme with programme items in PDF...')
    joined_pdf, pages = join_pdf_programme_with_items(index_pdf, header, items, tmp_path)
    logger.info('\tUpdating link in joined PDF..')
    update_links_in_joined_pdf(joined_pdf, pages)
    return joined_pdf


def insert_title_pdf_page(joined_pdf, output_path, tmp_path, header):
    logger.info(f'\tCopying custom css for frontpage to temp dir...')
    css_filepath = os.path.join(tmp_path, "css")
    if not os.path.exists(css_filepath):
        os.makedirs(css_filepath)
    css_file_path = os.path.join(css_filepath, "style_fp.css")
    shutil.copyfile("../files/css/style_fp.css", css_file_path)
    logger.info(f'\tCreating HTML cover page...')
    environment = Environment(loader=FileSystemLoader("../files/"))
    template = environment.get_template("front_page.html.j2")
    content = template.render(
        no_council_meeting=header.no_council_meeting,
        title=header.title,
        time=header.time,
        location=header.location
    )
    filepath = os.path.join(tmp_path, "cover.html")
    with open(filepath, mode="w", encoding="utf-8") as message:
        message.write(content)
    logger.info(f'\tPrinting HTML cover page to PDF...')
    filepath_pdf = os.path.join(tmp_path, "cover.pdf")
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
    if os.path.exists(filepath_pdf):
        logger.info(f"\tCover page written in {os.path.basename(filepath_pdf)}.")
    else:
        logger.error(f'Something wrong during cover page writing to {filepath_pdf}.')
    logger.info(f'\tJoining PDF cover with programme PDF...')
    output_filepath = os.path.join(output_path, os.path.basename(joined_pdf))
    doc = fitz.open(joined_pdf)
    cover = fitz.open(filepath_pdf)
    doc.insert_pdf(cover, start_at=0)
    doc.save(output_filepath, garbage=4, deflate=True, linear=True) # save the document    
    doc.close()
    cover.close()
    return output_filepath


if __name__ == "__main__":

    logger.remove()
    logger.add(sys.stderr, format="{time} {level} {message}", level="WARNING")
    logger.add(sys.stdout, colorize=True, format="<green>{time}</green> <level>{message}</level>", level="INFO")
    logger.add("trace.log", backtrace=True, diagnose=True, rotation="10 minutes", retention="10 minutes", level="TRACE")  # Caution, may leak sensitive data
    logger.add("last.log", rotation="10 minutes", retention="10 minutes", enqueue=True, level="DEBUG")

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--programme", help = "path to VERA ejednani directory", type=str)
    parser.add_argument("-o", "--output", help = "ePub output folder path", type=str)
    parser.add_argument("--author", help = "the name of the city that generated eJednani export", type=str)
    parser.add_argument("--contributor", help = "your name", type=str)
    parser.add_argument("--source", help = "original resource URL", type=str)
    args = parser.parse_args()

    global input_path
    input_path = ''
    if args.programme:
        input_path = args.programme
        if not (os.path.exists(input_path) and os.path.isdir(input_path)):
            logger.error(f"Input parameter '--programme' doesn't contain valid folder path. Value: {input_path}. Exiting...")
            exit(1)
    global output_path
    output_path = ''
    if args.output:
        output_path = args.output
        if not os.path.exists(os.path.normpath(os.path.dirname(output_path))):
            logger.error(f"Input parameter '--output' doesn't contain valid output path (must exists). Value: {os.path.normpath(os.path.dirname(output_path))}. Exiting...")
            exit(1)
    input_author = ''
    if args.author:
        input_author = args.author
    input_contributor = ''
    if args.contributor:
        input_contributor = args.contributor
    input_source = ''
    if args.source:
        input_source = args.source

    tmp_dir = tempfile.TemporaryDirectory()

    logger.info(f'Creating temp directory {tmp_dir.name}...')
    programme_path = get_programme_path()
    index_filepath = os.path.join(programme_path, "index.html")

    logger.info(f'Parsing programme...')
    header, items = parse_programme(index_filepath)
    logger.trace([item.resolution for item in items])
    debug_print_items_attachments(items)

    logger.info(f'Extracting *.ZIP attachments original files...')
    items = extract_zip_files(items, tmp_dir)
    debug_print_items_attachments(items)

    logger.info(f'Converting attachments to PDF files...')
    items = convert_files_to_pdf(items, tmp_dir.name)
    debug_print_items_attachments(items)

    logger.info(f'Creating PDFs for programme items...')
    create_programme_item_pdfs(header, items, tmp_dir.name)
    logger.info(f'Creating PDF for index programme...')
    index_pdf = create_programme_index_pdf(index_filepath, tmp_dir.name, header, items)
    logger.info(f'Inserting title page...')
    pdf_output_filepath = insert_title_pdf_page(index_pdf, output_path, tmp_dir.name, header)
    if os.path.exists(pdf_output_filepath):
        logger.success(f"Complete PDF file was written to {pdf_output_filepath}.")
    else:
        logger.error(f'Something wrong during writing complete PDF to {pdf_output_filepath}.')

    # input("Press ENTER for cleanup temp dir")
    tmp_dir.cleanup()
    tmp_dir = None

    logger.success(f'Script ended. All is done.')
