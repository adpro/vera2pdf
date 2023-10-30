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

from io import StringIO
from datetime import datetime

from lxml import etree
from ebooklib import epub
from pikepdf import Pdf, Page   # for rotating pages
from loguru import logger

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
    header.title = remove_spaces(rows[0].text)
    header.no_council_meeting = remove_spaces(rows[1].text)
    header.location_and_time = ' '.join([remove_spaces(rows[2].text), remove_spaces(rows[3].text)])
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


def convert_file_to_supported_type(old_filepath) -> str:
    ext = pathlib.Path(old_filepath).suffix.lower()
    filename = pathlib.Path(old_filepath).stem
    new_filename = '.'.join([filename,'pdf'])
    new_filepath = os.path.join(tmp_dir.name, new_filename)
    new_path = os.path.dirname(new_filepath)
    if ext in ['.docx', '.doc', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.bmp', '.tif']:
        logger.info(f'Converting {os.path.basename(old_filepath)} to {os.path.basename(new_filepath)}...')
        subprocess.call([get_libre_office_path(), '--headless', '--convert-to', 'pdf', old_filepath, '--outdir', new_path])
        return new_filepath, 'pdf'
    return old_filepath, ext[1:]


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
    if len(el) != 4:
        raise WrongProgrammeFormatError
    # id
    item.id = remove_spaces(el[0].text.replace('.',''))    

    # name
    if el[1].text == None:  # with href link to more info
        process_item_w_link(el[1], item)
    else:   # no link to more info
        process_item_wo_link(el[1], item)
    
    # time
    item.time = remove_spaces(el[3].text)
    
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


def get_attachment_new_path(old_path):
    filename = os.path.basename(old_path)
    new_path = os.path.join('attachments', filename)
    return new_path


def generate_html_attachments(attachments):
    # links = []
    # for attachment in attachments:
    #     images = []
    #     for file in attachment.files:
    #         if pathlib.Path(file).suffix.lower() not in ['.png']:
    #             continue
    #         new_path = get_attachment_new_path(file)
    #         image = f'<img src="{new_path}"/>'
    #         images.append(image)
    #     links.append(f'<div class"attachment"><p><em>{attachment.name}</em></p>{"".join(images)}</div>')
    # return "".join(links)
    links = []
    for attachment in attachments:
        links.append(f'<li><a href="references.xhtml#att{attachment.uid}">{attachment.name}</a></li>')
    return '<ul>' + "".join(links) + '</ul>'


def create_chapter(item: ProgrammeItem):
    # create chapter
    c_filename = f'chap_{item.id}.xhtml'
    c_title = f'{item.name}'
    c = epub.EpubHtml(title=c_title, file_name=c_filename, lang='cs-CZ')
    c.add_link(href='style/nav.css', rel='stylesheet', type='text/css')

    if not item.resolution:
        c.content=f'''
                <h1>{item.id}. {item.name}</h1>
                <div class="metadata">
                    <p><span class="title">Předkladatel: </span><span>{item.presenter}</span></p>
                </div>
                '''
    else:
        txt_attach = ''
        if len(item.attachments):
            txt_attach = f'<p><p class="title">Přílohy: </p><div id="ch-att-{item.id}">{generate_html_attachments(item.attachments)}</div></p>'
        c.content=f'''
                <h1>{item.id}. {item.name}</h1>
                <div class="statement"><p class="title">Návrh usnesení:</p><p class="statement">{item.resolution}</p></div>
                <div class="metadata">
                    <p><span class="title">Předkladatel: </span><span>{item.presenter}</span></p>
                    <p><span class="title">Zpracovatel: </span><span>{item.processor}</span></p>
                </div>
                <div>
                    <p><p class="title">Text důvodové zprávy: </p><p class="text">{item.reason_text}</p></p>
                    {txt_attach}
                </div>
                '''
    return c, c_filename, c_title


def get_ebook_name(header) -> str:
    if 'zastupit' in header.no_council_meeting.lower():
        prefix = 'ZM_'
    if 'rad' in header.no_council_meeting.lower():
        prefix = 'RM_'
    date_of_meeting = header.location_and_time.split()[3].split('.')
    month = '0'+date_of_meeting[1] if int(date_of_meeting[1])<10 else date_of_meeting[1]
    day = '0'+date_of_meeting[0] if int(date_of_meeting[0])<10 else date_of_meeting[0]
    return f'{prefix}{date_of_meeting[2]}-{month}-{day}_pb.epub'


def get_notes_name(header) -> str:
    if 'zastupit' in header.no_council_meeting.lower():
        prefix = 'ZM_'
    if 'rad' in header.no_council_meeting.lower():
        prefix = 'RM_'
    date_of_meeting = header.location_and_time.split()[3].split('.')
    month = '0'+date_of_meeting[1] if int(date_of_meeting[1])<10 else date_of_meeting[1]
    day = '0'+date_of_meeting[0] if int(date_of_meeting[0])<10 else date_of_meeting[0]
    return f'{prefix}{date_of_meeting[2]}-{month}-{day}_notes.html'



def generate_references_attachment(attachment: Attachment):
    images = []
    for file in attachment.files:
        new_path = get_attachment_new_path(file)
        if pathlib.Path(file).suffix.lower() in ['.png', '.jpg', '.gif', '.jpeg', '.bmp', '.tiff']:
            image = f'<img src="{new_path}"/>'
        else:
            image = f'<a href="{new_path}">{attachment.name}</a>'
        images.append(image)
    return ''.join(images)        


def generate_references_item(item):
    final_html = []
    for attachment in item.attachments:
        myhtml = f'''
        <div id="att{attachment.uid}">
            <p>{attachment.name}</p>
            <p><a href="chap_{item.id}.xhtml#ch-att-{item.id}">Zpět k bodu {item.id}</a></p>
            {generate_references_attachment(attachment)}
        </div>
        '''
        final_html.append(myhtml)
    return ''.join(final_html)


def generate_references(items):
    final_html = []
    for item in items:
        if len(item.attachments) > 0:
            myhtml = f'''<div id="nav{item.id}">
                {generate_references_item(item)}
                <p><a href="chap_{item.id}.xhtml#ch-att-{item.id}">Zpět k bodu {item.id}</a></p>
            </div>
            '''
            final_html.append(myhtml)
    return ''.join(final_html)


def create_references(items):
    # create chapter
    c_filename = f'references.xhtml'
    c_title = f'Přílohy'
    c = epub.EpubHtml(title=c_title, file_name=c_filename, lang='cs-CZ')
    c.add_link(href='style/nav.css', rel='stylesheet', type='text/css')
    c.content=f'''
            <h1>Přílohy</h1>
            <div>{generate_references(items)}
            </div>
            '''
    return c


def add_metadata(book: epub.EpubBook, meta_author, meta_contributor, meta_source):
    if len(meta_author) > 1:
        book.add_author(meta_author, role='aut')
    else:
        book.add_author('IS VERA', role='aut')
    if len(meta_contributor) > 1:
        book.add_metadata('DC', 'contributor', meta_contributor, {'id': 'contributor'})
        book.add_metadata(None, 'meta', 'edt', {'refines': '#contributor', 'property': 'role', 'scheme': 'marc:relators'})
    if len(input_source) > 2:
        book.add_metadata('DC', 'source', input_source)
    today = datetime.now()
    iso_today = today.isoformat()
    book.add_metadata(None, 'meta', '', {'name': 'ePub generator', 'content': 'vera2epub4pb'})
    book.add_metadata('DC', 'date', iso_today)


def create_ebook(header, items, path, meta_author, meta_contributor, meta_source):
    filepath_ebook = os.path.join(path, get_ebook_name(header))
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(' '.join([header.title, header.no_council_meeting.replace(',','').strip()]))
    book.set_language('cs-CZ')
    add_metadata(book, meta_author, meta_contributor, meta_source)

    chapters = []
    for item in items:
        chapter, chap_filename, chap_title = create_chapter(item)
        book.add_item(chapter)
        chapters.append(chapter)
        logger.trace(f'item {len(item.attachments)}')
        for attach in item.attachments:
            attach_files = attach.files
            if len(attach_files) > 1:
                for filepath in attach.files:
                    file_ext = pathlib.Path(filepath).suffix.lower()
                    filename = os.path.basename(filepath)
                    if file_ext == '.png':
                        image_content = open(filepath, 'rb').read()
                        img_filename = f'attachments/{filename}'
                        # img = epub.EpubImage(uid=str(uuid.uuid4()), file_name=img_filename, media_type='image/png', content=image_content)
                        img = epub.EpubImage()
                        img.file_name = img_filename
                        img.media_type = 'image/png'
                        img.content = image_content
                        book.add_item(img)
            else:
                filepath = attach.files[0]
                file_content = open(filepath, 'rb').read()
                obj = epub.EpubItem(file_name=get_attachment_new_path(filepath),
                                    content=file_content)
                book.add_item(obj)
    chapter = create_references(items)
    chapters.append(chapter)
    book.add_item(chapter)

    # define Table Of Contents
    book.toc = (chapters)                
    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    # define CSS style
    style = '''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h1, h2, h3 {
    margin-bottom: 1.5em;
}
h1 {
    font-size: 165%;
}
h2 {
    font-size: 150%;
}
h3 {
    font-size: 135%;
}
ol {
    list-style-type: none;
}
ol > li:first-child {
    margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
    margin-top: 0.3em;
}
span.title, p.title {
    font-style: italic;
}
p.statement {
    font-weight: bold;
}
p.indented {
    text-indent: 2em;
}
* a {
    text-decoration-style: dotted;
}
hr.emptyline {
    width: 0px;
    margin: 2em;
    border: none;
}
hr.separator {
    width: 1em;
    margin-top: 2em;
    margin-bottom: 2em;
}
img {
    border: none;
}
'''
    # add css file
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)
    # basic spine
    book.spine = ['nav'] + chapters

    epub.write_epub(filepath_ebook, book, {})
    if os.path.exists(filepath_ebook):
        logger.success(f"Ebook written in {filepath_ebook}.")
    else:
        logger.error(f'Something wrong during ebook writing to {filepath_ebook}.')


def create_html_notes(header, items, programme_path):
    html_items = []

    for item in items:
        html_item = f'''
            <h2>{item.id}. {item.name}</h2>
            <p><br/></p>
            <hr/>
        '''
        html_items.append(html_item)

    html = '''
    <html>
        <head>
            <link rel="preconnect" href="https://fonts.googleapis.com"> 
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin> 
            <link href="https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&display=swap" rel="stylesheet">
            <style>
            body {
                font-family: "Literata", serif;
                font-size: 14px;
            }
            h1 {
                font-weight: bold;   
                font-size: 18px;
            }
            h2 {
                font-weight: bold;
                font-size: 15px;
            }
            </style>
        </head>
    ''' + f'''
        <body>
            <h1>{header.title} {header.no_council_meeting}</h1>
            <p>{header.location_and_time}</p>
            <hr/>
            {"".join(html_items)}
        </body>
    </html>
    '''
    filepath = os.path.join(programme_path, get_notes_name(header))
    with open(filepath, 'w', encoding='utf8') as f:
        f.write(html)
        logger.success(f'Notes written to {filepath}.')


def encode_charset(s, charset='cp852'):
    filename_bytes = s.encode('437')
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
                            zip_filename = encode_charset(file)
                            filename = get_zipped_normalized_filename(zip_filename)
                            filepath_extract = os.path.normpath(os.path.join(tmp_dir.name, filename))
                            with open(filepath_extract, 'wb') as f:
                                f.write(zipobject.read(file))
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


def convert_files_to_pdf(items):
    updated_p_items = []
    for p_item in items:
        upd_attachments = []
        for attachment in p_item.attachments:
            if len(attachment.files) == 1:
                full_path = attachment.files[0]
                new_path, ext = convert_file_to_supported_type(full_path)
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


def rotate_landscape_pdf_files(items):
    for item in items:
        for attachment in item.attachments: 
            if len(attachment.files) == 1:
                flag = 0
                filepath = attachment.files[0]
                ext = pathlib.Path(filepath).suffix.lower()
                if ext == '.pdf':
                    pdf = Pdf.open(filepath, allow_overwriting_input=True)
                    for page in pdf.pages:
                        cbox = page.cropbox
                        cbox_x = float(cbox[2]-cbox[0])/72*2.54
                        cbox_y = float(cbox[3]-cbox[1])/72*2.54
                        if cbox_x > cbox_y:
                            if flag == 0:
                                logger.debug(f'\tRotating {filepath}')
                                flag = 1                      
                            page.rotate(270, False)
                    pdf.save(filepath)


def convert_pdf_to_pngs(filepath, attachment: Attachment, tmp_dir) -> Attachment:
    logger.debug(f'Trying to convert {filepath} pages to png images...')
    filedir = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    doc = fitz.open(filepath)  # open document
    pages_filenames = []
    for page in doc:  # iterate through the pages
        uid = uuid.uuid4()
        pix = page.get_pixmap(dpi=150)  # render page to an image
        new_filepath = os.path.join(tmp_dir.name, filename + f'_{uid}_' + str(page.number) + '.png')
        pix.save(new_filepath)  # store image as a PNG
        pages_filenames.append(new_filepath)
    return Attachment(uid,attachment.name, '.png', pages_filenames)


def convert_attachments_to_pngs(items, tmp_dir):
    updated_p_items = []
    for p_item in items:
        upd_attachments = []
        for attachment in p_item.attachments:
            if len(attachment.files) == 1:
                filepath = attachment.files[0]
                ext = pathlib.Path(filepath).suffix.lower()
                if ext == '.pdf':
                    new_attachment = convert_pdf_to_pngs(filepath, attachment, tmp_dir)
                    upd_attachments.append(new_attachment)
                else:
                    logger.debug(f'Skipping {filepath} conversion to png...')
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


def debug_print_items_attachments(items):
    for p_item in items:
        logger.trace(f'DEBUG attachments {p_item.id}')
        for attachment in p_item.attachments:
            logger.trace(f'\t{attachment}')

# ====================== single PDF output file ======================

def get_pdf_ebook_name(header) -> str:
    if 'zastupit' in header.no_council_meeting.lower():
        prefix = 'ZM_'
    if 'rad' in header.no_council_meeting.lower():
        prefix = 'RM_'
    date_of_meeting = header.location_and_time.split()[3].split('.')
    month = '0'+date_of_meeting[1] if int(date_of_meeting[1])<10 else date_of_meeting[1]
    day = '0'+date_of_meeting[0] if int(date_of_meeting[0])<10 else date_of_meeting[0]
    return f'{prefix}{date_of_meeting[2]}-{month}-{day}_A4.pdf'


def create_basic_pdf(header, items, index_filepath, input_path, output_path):
    filepath_ebook = os.path.join(output_path, get_pdf_ebook_name(header))

    html_paths = [item.link for item in items if len(item.link) > 1]
    logger.trace(f'html paths of files: {html_paths}')
    html_paths.insert(0, index_filepath)

    # change css in input for our custom file
    css_filepath = os.path.join(input_path, "css/style.css")
    new_css_filepath = os.path.join(input_path, "css/style_orig.css")
    shutil.copyfile(css_filepath, new_css_filepath)
    shutil.copyfile("../files/css/style.css",css_filepath)

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
        'header-font-name': 'Times New Roman',
        'header-font-size': 12,    
    }
    pdfkit.from_file(html_paths, filepath_ebook, 
                    options=options,
                    verbose=True)


    if os.path.exists(filepath_ebook):
        logger.success(f"Ebook written in {filepath_ebook}.")
    else:
        logger.error(f'Something wrong during ebook writing to {filepath_ebook}.')

    # return css file from orig back
    shutil.move(new_css_filepath, css_filepath)

    return filepath_ebook


def update_attachment_file(att_doc, orig_filename, item, attachment):
    # att_doc
    page_count = att_doc.page_count
    for i in range(page_count):
        page = att_doc[i]
        r = fitz.Rect(36,36,136,72)  # rectangle
        shape = page.new_shape()  # create Shape
        shape.draw_rect(r)  # draw rectangles
        shape.finish(width = 0.3, color = (0,0,0), fill = (1,1,1))
        t = f'{item.id} {item.name} | {attachment.name}'
        rc = shape.insert_textbox(r, t, color = (0,0,0))
        # rc = shape.insert_textbox(r, t, color = (0,0,0), encoding=fitz.TEXT_ENCODING_LATIN)
        # rc = shape.insert_textbox(r, t, color = (0,0,0), encoding=fitz.TEXT_ENCODING_LATIN, fontname='TiRo')
        shape.commit()  # write all stuff to page /Contents
        att_doc.save(orig_filename, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)


def add_items_to_pdf(orig_file, items, input_path):
    doc = fitz.open(orig_file)
    logger.trace(f'Doc info: {doc.get_toc()}')
    for item in items:
        for attachment in item.attachments:
            for file in attachment.files:
                att = fitz.open(file)
                update_attachment_file(att, file, item, attachment)
                logger.trace(f'Attachment info: {item.id} {attachment.name} {file} {att.get_toc()}')
                doc.insert_pdf(att)
                att.close()
    doc.save(orig_file, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()


def create_programme_item_pdfs(header, items, index_filepath, input_path, output_path, tmp_dir):
    pass


def create_pdf_ebook(header, items, index_filepath, input_path, output_path, meta_author, meta_contributor, meta_source):
    # create PDF from HTML with wkhtmltopdf and PDFkit from programme and programme items only, without attachments
    pdf = create_basic_pdf(header, items, index_filepath, input_path, output_path)
    add_items_to_pdf(pdf, items, input_path)


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
    items = convert_files_to_pdf(items)
    debug_print_items_attachments(items)

    # logger.info(f'Rotating landscape pdf files...')
    # rotate_landscape_pdf_files(items)

    # logger.info(f'Converting PDF files to multiple PNG images...')
    # items = convert_attachments_to_pngs(items, tmp_dir)
    # debug_print_items_attachments(items)

    # logger.info(f'Creating ePub3 ebook...')
    # epub = create_ebook(header, items, output_path, input_author, input_contributor, input_source)

    logger.info(f'Creating PDFs for programme items...')
    pitem_pdfs = create_programme_item_pdfs(header, items, index_filepath, input_path, output_path, tmp_dir)

    logger.info(f'Creating PDF ebook...')
    pdf = create_pdf_ebook(header, items, index_filepath, input_path, output_path, input_author, input_contributor, input_source)

    # logger.info(f'Creating html notes...')
    # create_html_notes(header, items, output_path)
    tmp_dir.cleanup()
    tmp_dir = None

    logger.success(f'All is done.')
