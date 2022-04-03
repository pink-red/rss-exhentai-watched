# RSS ExHentai Watched

Generate a personal atom feed for your [watched tags](https://ehwiki.org/wiki/My_Tags#Watched) on ExHentai.


## Requirements

Tested on Python 3.9, would probably work on older versions.


## Usage

1. Clone this repo.
2. Copy the `config.json.example` to `config.json` and specify your cookies from ExHentai.
3. Create and activate a venv, install the dependencies:
   ```bash
   python -m venv venv
   . venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run it!
   ```bash
   gunicorn --bind 127.0.0.1:5000 main:app
   ```
5. You've got an atom feed on http://127.0.0.1:5000.


## See also

RSSHub's E-Hentai/ExHentai feeds: https://docs.rsshub.app/picture.html#e-hentai. For example, https://rsshub.app/ehentai/search/
