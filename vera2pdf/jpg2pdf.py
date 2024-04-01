import os
import pathlib
import fitz

img_filepath = '/Users/ales/Documents/_dev/vera2epub4pb/sample-data/input/9ZM/attachments/20231010_125023.jpg'
pdf_filepath = '/Users/ales/Documents/_dev/vera2epub4pb/sample-data/output/'

doc = fitz.open()
img = fitz.open(img_filepath)  # open pic as document
rect = img[0].rect  # pic dimension
pdfbytes = img.convert_to_pdf()  # make a PDF stream
img.close()  # no longer needed
imgPDF = fitz.open("pdf", pdfbytes)  # open stream as PDF
width, height = fitz.paper_size("a4")  # A4 portrait output page format
page = doc.new_page(width = width, height = height)
insert_rect = fitz.Rect(18,18,page.rect.br[0]-18,page.rect.br[1]-18)
mat = rect.torect(insert_rect)
print(f'Img rect={rect},\nPage rect={page.rect}')
print(f'Page points: tl={page.rect.tl}, tr={page.rect.tr}, bl={page.rect.bl}, br={page.rect.br}')
page.show_pdf_page(rect * mat, imgPDF)  # image fills the page
doc.save(os.path.join(pdf_filepath, pathlib.Path(img_filepath).stem +'.pdf'))
doc.close()
