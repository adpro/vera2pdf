# vera2pdf
![GitHub Release Date](https://img.shields.io/github/release-date/adpro/vera2pdf)
![License](https://img.shields.io/github/license/adpro/vera2pdf)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/adpro/vera2pdf)

aka converter of the programme for members of the Council and the Council from IS VERA in its format eJednání to PDF A4 file, primarily for the Fujitsu Quaderno e-ink reader.

## Prerequisites

### Operating system
If you want to use this tool in **developer way** like `python main.py`, you can use MacOS, Windows or Linux. Tool is tested only on MacOS 14.x Sonoma.

### Software installed
For PDF conversion tool needs LibreOffice installed. Tested with LibreOffice 7.3 and LibreOffice 24.2.x.

## Getting started

Firstly, check requirements. You need [git 2.0](https://git-scm.com) or better, Python 3.9 or better and [poetry](https://python-poetry.org) as package manager to be installed.

Clone repository:
```
$ git clone https://github.com/adpro/vera2pdf.git
```
Go to project repository and its source code:
```
$ cd vera2pdf
```
Create poetry virtual environment:
```
$ poetry shell
```
Install all required packages from pyproject.toml:
```
$ poetry install
```
Go to code subfolder:
```
$ cd vera2pdf
```

Run `main.py` script for help:
```
$ python main.py -h
usage: main.py [-h] [-p PROGRAMME] [-o OUTPUT] [--author AUTHOR] [--contributor CONTRIBUTOR] [--source SOURCE]

optional arguments:
  -h, --help            show this help message and exit
  -p PROGRAMME, --programme PROGRAMME
                        path to VERA ejednani directory
  -o OUTPUT, --output OUTPUT
                        PDF output folder path
  --author AUTHOR       the name of the city that generated eJednani export
  --contributor CONTRIBUTOR
                        your name
  --source SOURCE       original resource URL
```
For conversion run with arguments:
```
$ python main.py --author "Your City of published program" --contributor "Your Name" --source "https://www.your-city.cz" -p /path/to/program -o /path/for/pdf/output/
```
with output:
```
2024-04-01T18:27:08.900928+0200 Creating temp directory /var/folders/5z/x2sg6_b17kxbc0g55nvjtglr0000gn/T/tmpn554xs88...
2024-04-01T18:27:08.901762+0200 Parsing programme...
2024-04-01T18:27:08.929605+0200 Extracting *.ZIP attachments original files...
2024-04-01T18:27:09.000127+0200 Converting attachments to PDF files...
2024-04-01T18:27:09.000762+0200 	Copying Zapis-o-jednani-spolecenske-komise_-24.-3.-2024.pdf to temp folder...
2024-04-01T18:27:09.034382+0200 	Copying Divadelni-sdruzeni-CK--akce.pdf to temp folder...
2024-04-01T18:27:09.035885+0200 	Converting VPS--Divadelni-sdruzeni-CK-z.s..docx to VPS--Divadelni-sdruzeni-CK-z.s..pdf by LibreOffice...
2024-04-01T18:27:11.860943+0200 	Copying VPS--Divadelni-sdruzeni-CK-.pdf to temp folder...
2024-04-01T18:27:43.792998+0200 	Copying snimek-1.pdf to temp folder...
2024-04-01T18:27:43.794734+0200 	Copying snimek-2.pdf to temp folder...
2024-04-01T18:27:43.797484+0200 	Converting UP-.png to UP-.pdf by PyMuPDF...
2024-04-01T18:27:43.827977+0200 	Copying zadosti.pdf to temp folder...
2024-04-01T18:27:43.836736+0200 	Converting IMG_7600.jpg to IMG_7600.pdf by PyMuPDF...
2024-04-01T18:27:43.846007+0200 	Converting IMG_7601.jpg to IMG_7601.pdf by PyMuPDF...
2024-04-01T18:27:43.854860+0200 	Converting IMG_7602.jpg to IMG_7602.pdf by PyMuPDF...
2024-04-01T18:27:43.868712+0200 	Copying podminky.pdf to temp folder...
2024-04-01T18:27:46.921664+0200 Creating PDFs for programme items...
2024-04-01T18:27:48.117942+0200 	Programme item written in pitem_1.pdf.
2024-04-01T18:27:49.298058+0200 	Programme item written in pitem_2.pdf.
2024-04-01T18:27:50.674674+0200 	Programme item written in pitem_3.pdf.
2024-04-01T18:27:51.855643+0200 	Programme item written in pitem_4.pdf.
2024-04-01T18:27:52.961141+0200 	Programme item written in pitem_5.pdf.
2024-04-01T18:28:17.654962+0200 Creating PDF for index programme...
2024-04-01T18:28:17.655501+0200 	Updating HTML programme in index.html, inserting links to programme items...
2024-04-01T18:28:17.668470+0200 	Printing programme to PDF...
2024-04-01T18:28:19.225217+0200 	Programme written in index.pdf.
2024-04-01T18:28:19.226284+0200 	Joining programme with programme items in PDF...
2024-04-01T18:28:19.460068+0200 	Updating link in joined PDF..
2024-04-01T18:28:21.425692+0200 Inserting title page...
2024-04-01T18:28:21.426080+0200 	Copying custom css for frontpage to temp dir...
2024-04-01T18:28:21.427565+0200 	Creating HTML cover page...
2024-04-01T18:28:21.430248+0200 	Printing HTML cover page to PDF...
2024-04-01T18:28:23.389721+0200 	Cover page written in cover.pdf.
2024-04-01T18:28:23.390643+0200 	Joining PDF cover with programme PDF...
2024-04-01T18:28:23.784957+0200 Complete PDF file was written to /path/for/pdf/output/RM_2024-04-03_A4.pdf.
2024-04-01T18:28:23.809788+0200 Script ended. All is done.
```

## Contributing
Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on code of conduct, and the process for submitting pull requests.


## License

vera2epub4pb is licensed under the Apache 2.0 license - see the [LICENSE](./LICENSE) file
for details.

## Credits
adpro - author
