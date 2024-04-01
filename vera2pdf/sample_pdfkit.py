import pdfkit


html_paths = ["../sample-data/input/20RM/index.html",
              "../sample-data/input/20RM/navrhy-usneseni/navrh-usneseni_382375.html",
              "../sample-data/input/20RM/navrhy-usneseni/navrh-usneseni_382422.html"]

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
pdfkit.from_file(html_paths, "../sample-data/output/20RM_pdfkit.pdf", 
                 options=options,
                 verbose=True)
