# OPUS Repository frontend

## Problems

* **FIXED** in "alignment candidate" view: if you press 'refrehs' then it will add copies of the file structure (duplicates)
* **FIXED** importing a tar.gz file: there is '--' in the file view for uploads
* **FIXED** added descrption with HTML code and that did not work well ...
  (need to be more careful with free-text fields! domain, origin, ...)


## Home

* **DONE** add option to remove a corpus (meaning a user-specific branch)
* **DONE** remove group option (**FIXED** add group throws an error for me at the moment)
* **DONE** edit group option (list members, possibility to add/remove members for the owner of a group)
* **DONE** could the list be more compact (less space between list items?)


## Upload file form

* **DONE** remove file format and detect from file extension instead
* **DONE** add `detect` option in language menu (as default)
* **DONE** complete list of iso639-1 language IDs in the language menu (maybe even allow to specify other languages?)
* **DONE** stay in Uploads form instead of moving to corpus view
* **DONE** add link back to corpus view (current corpus)


## Corpus view (file system view)

* make 'view' file the default when clicking on file names (view metadata as option)
* English language names instead of lang-IDs (e.g. using https://pypi.org/project/iso-639/)
* **DONE** refresh button or clickable headers in the table (uploads/monolingual/parallel)
* **DONE** disable 'view' for upload files (does not make sense for tar, pdf, doc, ...)
* **DONE** possibly restrict size in 'view' to avoid loading very big files?
* **DONE** if upload file status = 'importing': change `import` to `stop import` (support for stopping import still needs to be implemented by the backend - need to store job ID in file metadata!)
* **DONE** if upload file status = 'waiting in import queue': change `import` to `cancel import` (cancel import still needs to be implemented by the backend - need to store job ID in file metadata and need to change status when queuing files for import!)


## Corpus settings

* change default for PDF reader to 'combined'
* change options for sentence alignment (internal = AlignPara_method) to: one-to-one,length-based,hunalign,hunalign-cautious,hunalign-bisent,hunalign-bisent-cautious
* add 'language identification (document-level)' (internal = ImportPara_langid) with options: none,textcat,blacklist,cld,cld2,lingua,langid (default = langid)
* add 'language identification (sentence-level)' (internal = ImportPara_langid_sent) with options: none,textcat,blacklist,cld,cld2,lingua,langid (default = langid)
* **DONE** remove option for automatic import
* **DONE** PDF reader options: tika/standard/raw/layout/combined                (default = tika)
* **DONE** document alignment options: identical-names/similar/names	       (default = identical-names)
* **DONE** sentence alignment options: one-to-one/length-based/hunalign/bisent  (default = bisent)
* **DONE** sentence splitter options: europarl/lingua/udpipe/opennlp            (default = udpipe)
* **DONE** add checkbox for `automatic parsing`   (ImportPara_autoparse = on/off, default = on)
* **DONE** add checkbox for `automatic wordalign` (ImportPara_autowordalign = on/off, default = on)

## Create group 

* error message if creating a new group fails (backend problem? does not report that group already exists?)

## General

* add help (hover? help menu?)
* better job handling (need better support from backend)
* admin view? (do we need that for maintenance?)
* how save is the input of arbitrary descriptions and other free edit fields?


## Unstable options

Remove some advanced options from the stable version of the frontend:

* edit metadata
* edit parallel data



## Wish list

* better integration of parallel data edit
* simplified view / download of data?
* conversion of aligned documents to TMX and download
* leader board for regular supporters
* quality rating of public corpora
* user-contributed improvements to the corpus (help with alignment checking)
