:: NOTE:
:: using "http://teencoreclub.com/" as URL did not work for some reason,
:: so in order to use the port, need to edit ./venv/Lib/site-packages/waybackpack/pack.py
:: Replace:	self.parsed_url.netloc,
:: With:	self.parsed_url.hostname,

waybackpack http://teencoreclub.com:80/ --from-date 20090219225754 --to-date 20150116195643 -d home --progress --no-clobber --raw
