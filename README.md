# Metadata Template Transformation

## Introduction

The programs bundled in this repository intend to solve the problem of automatically retrieving metadata records for a given study submitted to NMDC through the [NMDC Submission Portal](https://data.microbiomedata.org/submission/home), and converting the metadata into Excel spreadsheets that are accepted by [DOE user facilities](https://www.energy.gov/science/office-science-user-facilities).

There are three components to keep in mind when trying to use this application.

1. JSON header configuration file
  * The headers that go into the user facility spreadsheet outputs is controlled by JSON files.
  * The keys at the top level are used to indicate the main headers in the output. These values have mappings in the mapping configuration files described in the next point.
  * You can use numbered keys to add more header information to clarify what a particular column contains.
  * The special *header* keyword is reserved in case you want to use some other column names as the main header.
  * Follow the examples that have already been specified in [input-files](input-files/). There are two user facility header customizations that have already been created as examples for the NMDC. They are:
    * EMSL header configuration: [emsl_header.json](input-files/emsl_header.json)
    * JGI header configuration: jgi_header.json

2. Column mapping file
   * A TSV mapping file can be used to specify mappings between columns in the Submission Portal template and columns in the user facility spreadsheet outputs.
   * The column mappings can be specified by following the examples you can see in the [mapping-configs](mapping-configs/) folder. There are two mapping files that have already been created for NMDC. They are:
    * EMSL mapping file: [emsl.tsv](mapping-configs/emsl.tsv)
    * JGI mapping file: [jgi.tsv](mapping-configs/jgi.tsv)

3. [etl.py](etl.py)
   * The command line application that can facilitate the conversion of metadata from the Submission Portal into user facility formats by consuming the above two files as inputs.

## Software Requirements
1. [poetry](https://python-poetry.org/)
2. Python 3.9

## Setup

1. Install dependencies with poetry

```
poetry install
```

2. Run `etl.py` with options as follows:

```bash
➜  metadata-template-transformation git:(main) ✗ poetry run python etl.py --help
Usage: etl.py [OPTIONS]

  Convert submission portal metadata to a DOE user facility specific format.

Options:
  -o, --output TEXT      Path to result output XLSX file.  [required]
  -m, --mapper PATH      Path to user facility specific TSV file.  [required]
  -h, --header TEXT      Path to user facility template headers JSON file.
                         [required]
  -i, --input PATH       Path to submission portal TSV export.
  -s, --submission TEXT  Metadata submission id.  [required]
  --help                 Show this message and exit.
```