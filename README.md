# vera2epub4pb
![GitHub Release Date](https://img.shields.io/github/release-date/adpro/vera2epub4pb)
![License](https://img.shields.io/github/license/adpro/vera2epub4pb)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/adpro/vera2epub4pb)

aka converter of the program for members of the Council and the Council from IS VERA in its format eJednání to Epub file, primarily for the PocketBook reader. The Epub output file fully meets the Epub version 3.2 specification (according to [EpubCheck](https://github.com/w3c/epubcheck)).

## Prerequisites

### Operating system
If you want to use this tool in **developer way** like `python main.py`, you can use MacOS, Windows or Linux. Tool is tested only on MacOS 12.6.

### Software installed
For PDF conversion tool needs LibreOffice installed. Tested with LibreOffice 7.3.

## Getting started

Firstly, check requirements. You need [git 2.0](https://git-scm.com) or better, Python 3.9 and [poetry](https://python-poetry.org) as package manager to be installed.

Clone repository:
```
$ git clone https://github.com/adpro/vera2epub4pb.git
```
Go to project repository and its source code:
```
$ cd vera2epub4pb
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
$ cd vera2epub4pb
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
                        ePub output folder path
  --author AUTHOR       the name of the city that generated eJednani export
  --contributor CONTRIBUTOR
                        your name
  --source SOURCE       original resource URL
```
For conversion run with arguments:
```
$ python main.py --author "Your City of published program" --contributor "Your Name" --source "https://www.your-city.cz" -p /path/to/program -o /path/for/epub/output/
```
with output:
```
2022-11-09T13:04:52.192521+0100 Creating temp directory /var/folders/5z/x2sg6_b17kxbc0g55nvjtglr0000gn/T/tmp2dzq3gcz...
2022-11-09T13:04:52.195835+0100 Parsing programme...
2022-11-09T13:04:52.237802+0100 Extracting *.ZIP attachments original files...
2022-11-09T13:04:52.251173+0100 Converting attachments to PDF files...
2022-11-09T13:04:52.252339+0100 Converting KS-c.-26-2022.doc to KS-c.-26-2022.pdf...
2022-11-09T13:04:56.745139+0100 Converting KS-c.-36-2022.doc to KS-c.-36-2022.pdf...
2022-11-09T13:04:58.885390+0100 Converting Znalecky-posudek.doc to Znalecky-posudek.pdf...
2022-11-09T13:05:08.095936+0100 Converting DAROVACI_SMLOUVA__184_2022.docx to DAROVACI_SMLOUVA__184_2022.pdf...
...
2022-11-09T13:05:25.083942+0100 Rotating landscape pdf files...
2022-11-09T13:05:26.178703+0100 Converting PDF files to multiple PNG images...
2022-11-09T13:05:58.994590+0100 Creating ePub3 ebook...
2022-11-09T13:06:02.287547+0100 Ebook written in /path/for/epub/output/ZM_2022-11-09_pb.epub.
2022-11-09T13:06:02.287901+0100 Creating html notes...
2022-11-09T13:06:02.288521+0100 Notes written to /path/for/epub/output/ZM_2022-11-09_notes.html.
2022-11-09T13:06:02.313265+0100 All is done.
```

## Contributing
Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on code of conduct, and the process for submitting pull requests.


## License

vera2epub4pb is licensed under the Apache 2.0 license - see the [LICENSE](./LICENSE) file
for details.

## Credits
adpro - author
