# Palatnik & Vishnik Family Tree

Descendants of David Palatnik and Yankel Meir Vishnik of Teplik, Ukraine, with their spouses.

## Updating the tree

1. Export a new GEDCOM file from Ancestry.
2. Run `python3 tools/build.py "path/to/Lavine-Palat Family Tree.ged"`.
3. Commit and push `index.html`.

The page itself lives in `tools/template.html`. The GEDCOM file is not committed.

## Private additions

Corrections that aren't in Ancestry yet go in `private/additions.json`. The build merges them in, and on the public page living relatives appear as "Living relative". The `private/` folder is never committed, because it holds living relatives' names.

For a full-name copy, run `python3 tools/build.py TREE.ged --full private/full.json`, then `node private/make_doc.js` to build the Word document.
