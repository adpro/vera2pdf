import pathlib
import fitz


html_paths = ["../sample-data/input/20RM/index.html",
              "../sample-data/input/20RM/navrhy-usneseni/navrh-usneseni_382375.html",
              "../sample-data/input/20RM/navrhy-usneseni/navrh-usneseni_382422.html"]

writer = fitz.DocumentWriter("../sample-data/output/20RM_fitz.pdf")  # create the writer

for x in html_paths:
    htmlpath = pathlib.Path(x)
    csspath = pathlib.Path("../sample-data/input/20RM/css/style.css")

    HTML = htmlpath.read_bytes().decode()
    CSS = csspath.read_bytes().decode()

    story = fitz.Story(html=HTML, user_css=CSS)

    MEDIABOX = fitz.paper_rect("a4")  # output page format: Letter
    WHERE = MEDIABOX + (36, 36, -36, -36)  # leave borders of 0.5 inches

    story = fitz.Story(html=HTML)  # create story from HTML
    body = story.body
    with body.add_paragraph() as para:
        para.set_font("serif").add_text("Hlasování: Pro ____ Proti ____ Zdržel se: ____ Nehlasoval: ____")
    with body.add_paragraph() as para:
        para.set_font("serif").add_text("Usnesení: Přijato | Nepřijato")

    match = body.find("table", "class", "podpisy")
    if match is not None:
        match.remove()

    match = body.find("td","class","typDokumentu")
    header = ""
    if match is not None:
        header += match.text

    more = 1  # will indicate end of input once it is set to 0

    while more:  # loop outputting the story
        device = writer.begin_page(MEDIABOX)  # make new page
        more, _ = story.place(WHERE)  # layout into allowed rectangle
        story.draw(device)  # write on page
        writer.end_page()  # finish page

writer.close()  # close output file

# doc_a = fitz.open("../sample-data/output/RM_2023-10-24_pb.epub")
# doc_a.save("../sample-data/output/RM_2023-10-24_pb.pdf")

doc = fitz.open("../sample-data/output/20RM_fitz.pdf")
